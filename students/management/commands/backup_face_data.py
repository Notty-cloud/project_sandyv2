"""
Export students, classes and face embeddings to a portable JSON file.

Railway's own backups protect against corruption and bad migrations, but they
live inside Railway — a lapsed account or a deleted project takes them too.
Face embeddings are the one thing here that cannot be regenerated: recovering
them means physically re-enrolling every student, one at a time. This produces
a copy you can keep somewhere else.

    python manage.py backup_face_data --output backup.json
    python manage.py backup_face_data --tenant <uuid> --output school-a.json

Embeddings are written as plain lists of floats, so the file restores onto
either database backend regardless of which produced it (PostgreSQL stores a
vector column, SQLite a JSON array).

Admin accounts are deliberately excluded — they contain password hashes, and
this file is meant to be copied around. Recreate them with create_admin.py.

Restore with: python manage.py restore_face_data <file>
"""
import json
from datetime import datetime, timezone

from django.core.management.base import BaseCommand, CommandError

from classes.models import Class
from enrollments.models import Enrollment
from students.models import Student, StudentEmbedding

FORMAT_VERSION = 1


class Command(BaseCommand):
    help = 'Export students, classes and face embeddings to a portable JSON file.'

    def add_arguments(self, parser):
        parser.add_argument('--output', '-o', required=True, help='path to write')
        parser.add_argument('--tenant', help='restrict to a single tenant id')
        parser.add_argument(
            '--indent', type=int, default=None,
            help='pretty-print with this indent (larger file; default compact)',
        )

    def handle(self, *args, **options):
        tenant = options.get('tenant')

        students = Student.objects.all()
        classes = Class.objects.all()
        embeddings = StudentEmbedding.objects.select_related('student').all()
        enrolments = Enrollment.objects.select_related('student').all()

        if tenant:
            students = students.filter(tenant_id=tenant)
            classes = classes.filter(tenant_id=tenant)
            embeddings = embeddings.filter(tenant_id=tenant)
            enrolments = enrolments.filter(tenant_id=tenant)

        payload = {
            'format_version': FORMAT_VERSION,
            'exported_at': datetime.now(timezone.utc).isoformat(),
            'tenant_filter': tenant,
            'students': [
                {
                    'id': str(s.id),
                    'tenant_id': str(s.tenant_id),
                    'student_id': s.student_id,
                    'name': s.name,
                    'grade': s.grade,
                    'section': s.section,
                    'is_active': s.is_active,
                }
                for s in students
            ],
            'classes': [
                {
                    'id': c.id,
                    'tenant_id': str(c.tenant_id),
                    'class_name': c.class_name,
                    'subject': c.subject,
                    'grade': c.grade,
                    'section': c.section,
                    'academic_year': c.academic_year,
                    'is_active': c.is_active,
                }
                for c in classes
            ],
            'embeddings': [
                {
                    'student_id': str(e.student_id),
                    'tenant_id': str(e.tenant_id),
                    # list() so a pgvector column and a SQLite JSON array both
                    # serialise identically and restore onto either backend.
                    'embedding': list(e.embedding),
                    'backend': e.backend,
                    'detector': e.detector,
                    'version': e.version,
                    'quality_score': e.quality_score,
                    'is_active': e.is_active,
                }
                for e in embeddings
            ],
            'enrolments': [
                {
                    'student_id': str(en.student_id),
                    'tenant_id': str(en.tenant_id),
                    'academic_year': en.academic_year,
                    'status': en.status,
                    'embedding_generated': en.embedding_generated,
                    'quality_score': en.quality_score,
                }
                for en in enrolments
            ],
        }

        counts = {k: len(v) for k, v in payload.items() if isinstance(v, list)}
        if not counts.get('embeddings'):
            self.stdout.write(self.style.WARNING(
                'No embeddings found — this backup contains no face data.'
            ))

        try:
            with open(options['output'], 'w', encoding='utf-8') as handle:
                json.dump(payload, handle, indent=options['indent'])
        except OSError as exc:
            raise CommandError(f'Could not write {options["output"]}: {exc}')

        self.stdout.write(self.style.SUCCESS(f'Wrote {options["output"]}'))
        for name, count in counts.items():
            self.stdout.write(f'  {name}: {count}')
        self.stdout.write(
            'Admin accounts are not included — recreate them with create_admin.py.'
        )
