"""
Restore a file written by backup_face_data.

    python manage.py restore_face_data backup.json
    python manage.py restore_face_data backup.json --wipe

Idempotent by default: students and classes are matched on their original ids
and updated in place, and an embedding is skipped when that student already has
one at the same version. Re-running will not create duplicates.

--wipe deletes existing students, embeddings and enrolments first. It is the
option to use when recovering onto a dirty database; it is irreversible, so it
asks for confirmation unless --no-input is given.

Everything happens inside one transaction — a partial restore would leave
students without their face data, which is worse than no restore at all.
"""
import json

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from classes.models import Class
from enrollments.models import Enrollment
from students.models import Student, StudentEmbedding

SUPPORTED_FORMAT = 1


class Command(BaseCommand):
    help = 'Restore students, classes and face embeddings from a backup file.'

    def add_arguments(self, parser):
        parser.add_argument('path', help='backup file written by backup_face_data')
        parser.add_argument(
            '--wipe', action='store_true',
            help='delete existing students, embeddings and enrolments first',
        )
        parser.add_argument(
            '--no-input', action='store_true', help='skip the confirmation prompt',
        )

    def handle(self, *args, **options):
        try:
            with open(options['path'], encoding='utf-8') as handle:
                payload = json.load(handle)
        except OSError as exc:
            raise CommandError(f'Could not read {options["path"]}: {exc}')
        except json.JSONDecodeError as exc:
            raise CommandError(f'{options["path"]} is not valid JSON: {exc}')

        version = payload.get('format_version')
        if version != SUPPORTED_FORMAT:
            raise CommandError(
                f'Unsupported backup format {version!r}; this command reads '
                f'format {SUPPORTED_FORMAT}.'
            )

        students = payload.get('students', [])
        classes = payload.get('classes', [])
        embeddings = payload.get('embeddings', [])
        enrolments = payload.get('enrolments', [])

        self.stdout.write(
            f'Backup from {payload.get("exported_at", "unknown date")}: '
            f'{len(students)} students, {len(classes)} classes, '
            f'{len(embeddings)} embeddings, {len(enrolments)} enrolments'
        )

        if options['wipe'] and not options['no_input']:
            existing = Student.objects.count()
            answer = input(
                f'--wipe will delete {existing} existing students and all their '
                f'face data. This cannot be undone. Type "yes" to continue: '
            )
            if answer.strip().lower() != 'yes':
                raise CommandError('Aborted.')

        with transaction.atomic():
            if options['wipe']:
                Enrollment.objects.all().delete()
                StudentEmbedding.objects.all().delete()
                Student.objects.all().delete()
                self.stdout.write('  wiped existing student data')

            for row in classes:
                Class.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'tenant_id': row['tenant_id'],
                        'class_name': row['class_name'],
                        'subject': row['subject'],
                        'grade': row['grade'],
                        'section': row['section'],
                        'academic_year': row['academic_year'],
                        'is_active': row['is_active'],
                    },
                )

            for row in students:
                Student.objects.update_or_create(
                    id=row['id'],
                    defaults={
                        'tenant_id': row['tenant_id'],
                        'student_id': row['student_id'],
                        'name': row['name'],
                        'grade': row['grade'],
                        'section': row['section'],
                        'is_active': row['is_active'],
                    },
                )

            restored, skipped = 0, 0
            for row in embeddings:
                exists = StudentEmbedding.objects.filter(
                    student_id=row['student_id'], version=row['version'],
                ).exists()
                if exists:
                    skipped += 1
                    continue
                StudentEmbedding.objects.create(
                    student_id=row['student_id'],
                    tenant_id=row['tenant_id'],
                    embedding=row['embedding'],
                    backend=row.get('backend', 'deepface'),
                    detector=row.get('detector', ''),
                    version=row['version'],
                    quality_score=row.get('quality_score'),
                    is_active=row.get('is_active', True),
                )
                restored += 1

            for row in enrolments:
                Enrollment.objects.update_or_create(
                    student_id=row['student_id'],
                    academic_year=row['academic_year'],
                    defaults={
                        'tenant_id': row['tenant_id'],
                        'status': row['status'],
                        'embedding_generated': row['embedding_generated'],
                        'quality_score': row.get('quality_score'),
                    },
                )

        self.stdout.write(self.style.SUCCESS('Restore complete.'))
        self.stdout.write(f'  students now:   {Student.objects.count()}')
        self.stdout.write(f'  embeddings now: {StudentEmbedding.objects.count()}')
        if skipped:
            self.stdout.write(f'  skipped {skipped} embeddings already present')
        self.stdout.write(
            'Admin accounts are not part of a backup — recreate with create_admin.py.'
        )
