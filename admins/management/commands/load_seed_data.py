"""
Management command: python manage.py load_seed_data

Creates seed admins, students, classes, enrollments, and attendance
records in the SQLite database for local development and POC testing.

Also creates matching Django User accounts so JWT login works.
"""
import uuid
import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from datetime import date, datetime

TENANT_ID = uuid.UUID('00000000-0000-0000-0000-000000000001')
ACADEMIC_YEAR = '2025-2026'


class Command(BaseCommand):
    help = 'Load sample seed data for POC testing'

    def handle(self, *args, **options):
        from admins.models import Admin
        from students.models import Student, StudentEmbedding
        from classes.models import Class
        from enrollments.models import Enrollment
        from attendance.models import StudentAttendance

        self.stdout.write('Clearing existing seed data...')
        StudentAttendance.objects.all().delete()
        Enrollment.objects.all().delete()
        StudentEmbedding.objects.all().delete()
        Class.objects.all().delete()
        Student.objects.all().delete()
        Admin.objects.all().delete()
        User.objects.filter(username__in=['maria.santos', 'jose.reyes', 'ana.cruz']).delete()

        # ── ADMINS ────────────────────────────────────────────────────────
        self.stdout.write('Creating admins...')
        hashed = make_password('Password123!')

        admin_data = [
            {
                'id': uuid.UUID('11111111-0000-0000-0000-000000000001'),
                'username': 'maria.santos',
                'admin_name': 'Maria Santos',
                'email': 'maria.santos@school.edu',
                'role': 'principal',
                'authorization_level': 3,
            },
            {
                'id': uuid.UUID('11111111-0000-0000-0000-000000000002'),
                'username': 'jose.reyes',
                'admin_name': 'Jose Reyes',
                'email': 'jose.reyes@school.edu',
                'role': 'teacher',
                'authorization_level': 1,
            },
            {
                'id': uuid.UUID('11111111-0000-0000-0000-000000000003'),
                'username': 'ana.cruz',
                'admin_name': 'Ana Cruz',
                'email': 'ana.cruz@school.edu',
                'role': 'teacher',
                'authorization_level': 1,
            },
        ]

        admins = {}
        for a in admin_data:
            # Create Django User so JWT login works
            user = User.objects.create(
                username=a['username'],
                email=a['email'],
                password=hashed,
                is_staff=a['role'] in ('admin', 'principal'),
            )
            # Create Admin record
            admin = Admin.objects.create(
                id=a['id'],
                tenant_id=TENANT_ID,
                admin_name=a['admin_name'],
                email=a['email'],
                password_hash=hashed,
                role=a['role'],
                authorization_level=a['authorization_level'],
            )
            admins[a['username']] = admin
            self.stdout.write(f'  OK {a["admin_name"]} ({a["role"]}) — login: {a["username"]} / Password123!')

        # ── STUDENTS ──────────────────────────────────────────────────────
        self.stdout.write('Creating students...')
        student_data = [
            ('22222222-0000-0000-0000-000000000001', 'STU-001', 'Carlos Dela Cruz',  'Grade 10', 'A'),
            ('22222222-0000-0000-0000-000000000002', 'STU-002', 'Bianca Flores',     'Grade 10', 'A'),
            ('22222222-0000-0000-0000-000000000003', 'STU-003', 'Ramon Villanueva',  'Grade 10', 'B'),
            ('22222222-0000-0000-0000-000000000004', 'STU-004', 'Sofia Mendoza',     'Grade 11', 'A'),
            ('22222222-0000-0000-0000-000000000005', 'STU-005', 'Luis Castillo',     'Grade 11', 'A'),
        ]

        students = {}
        for sid, code, name, grade, section in student_data:
            s = Student.objects.create(
                id=uuid.UUID(sid),
                tenant_id=TENANT_ID,
                student_id=code,
                name=name,
                grade=grade,
                section=section,
            )
            students[code] = s
            self.stdout.write(f'  OK {name}')

        # ── CLASSES ───────────────────────────────────────────────────────
        self.stdout.write('Creating classes...')
        class_data = [
            (1, 'Grade 10', 'A', 'G10-A Mathematics', 'Mathematics', 'jose.reyes'),
            (2, 'Grade 10', 'B', 'G10-B Mathematics', 'Mathematics', 'jose.reyes'),
            (3, 'Grade 11', 'A', 'G11-A Science',     'Science',     'ana.cruz'),
        ]

        classes = {}
        for cid, grade, section, name, subject, teacher_key in class_data:
            c = Class.objects.create(
                id=cid,
                tenant_id=TENANT_ID,
                grade=grade,
                section=section,
                class_name=name,
                subject=subject,
                teacher=admins[teacher_key],
                academic_year=ACADEMIC_YEAR,
            )
            classes[cid] = c
            self.stdout.write(f'  OK {name}')

        # ── ENROLLMENTS ───────────────────────────────────────────────────
        self.stdout.write('Creating enrollments...')
        enrollment_data = [
            ('STU-001', 'enrolled', True,  'jose.reyes'),
            ('STU-002', 'enrolled', True,  'jose.reyes'),
            ('STU-003', 'pending',  False, 'jose.reyes'),
            ('STU-004', 'enrolled', True,  'ana.cruz'),
            ('STU-005', 'failed',   False, 'ana.cruz'),
        ]

        for code, status, emb_generated, teacher_key in enrollment_data:
            Enrollment.objects.create(
                tenant_id=TENANT_ID,
                student=students[code],
                academic_year=ACADEMIC_YEAR,
                status=status,
                embedding_generated=emb_generated,
                enrolled_by=admins[teacher_key],
            )
            self.stdout.write(f'  OK {code} — {status}')

        # ── EMBEDDINGS ────────────────────────────────────────────────────
        self.stdout.write('Creating placeholder embeddings...')
        zero_vector = [0.0] * 512

        for code, quality in [('STU-001', 0.91), ('STU-002', 0.87), ('STU-004', 0.95)]:
            StudentEmbedding.objects.create(
                student=students[code],
                tenant_id=TENANT_ID,
                embedding=zero_vector,
                version=1,
                quality_score=quality,
                enrolled_by=admins['jose.reyes'] if code != 'STU-004' else admins['ana.cruz'],
            )
            self.stdout.write(f'  OK Embedding for {code} (quality: {quality})')

        # ── ATTENDANCE ────────────────────────────────────────────────────
        self.stdout.write('Creating attendance records...')
        attendance_data = [
            # date        student     class  checkin               status    confidence  override
            ('2025-09-01', 'STU-001', 1, '2025-09-01 07:02:00', 'present', 0.97, False, None, None, 'Gate A - Cam 1'),
            ('2025-09-01', 'STU-002', 1, '2025-09-01 07:15:00', 'late',    0.89, False, None, None, 'Gate A - Cam 1'),
            ('2025-09-01', 'STU-003', 2, None,                  'absent',  None, False, None, None, None),
            ('2025-09-01', 'STU-004', 3, '2025-09-01 07:01:00', 'present', 0.95, False, None, None, 'Gate B - Cam 2'),
            ('2025-09-01', 'STU-005', 3, '2025-09-01 07:05:00', 'present', 0.92, False, None, None, 'Gate B - Cam 2'),
            ('2025-09-02', 'STU-001', 1, '2025-09-02 07:00:00', 'present', 0.98, False, None, None, 'Gate A - Cam 1'),
            ('2025-09-02', 'STU-002', 1, '2025-09-02 07:03:00', 'present', 0.91, False, None, None, 'Gate A - Cam 1'),
            ('2025-09-02', 'STU-004', 3, None,                  'absent',  None, False, None, None, None),
            ('2025-09-03', 'STU-001', 1, '2025-09-03 07:04:00', 'present', 0.96, False, None, None, 'Gate A - Cam 1'),
            ('2025-09-03', 'STU-002', 1, '2025-09-03 07:10:00', 'present', None, True,
             'Camera angle was obstructed. Verified by teacher.', 'jose.reyes', 'Gate A - Cam 1'),
        ]

        for row in attendance_data:
            dt, code, cls_id, checkin, status, conf, is_override, reason, by_key, location = row
            StudentAttendance.objects.create(
                tenant_id=TENANT_ID,
                student=students[code],
                class_ref=classes[cls_id],
                date=date.fromisoformat(dt),
                checkin_time=timezone.make_aware(datetime.fromisoformat(checkin)) if checkin else None,
                status=status,
                confidence=conf,
                is_manual_override=is_override,
                override_reason=reason,
                overridden_by=admins[by_key] if by_key else None,
                location=location,
            )
            self.stdout.write(f'  OK {code} on {dt} — {status}')

        self.stdout.write(self.style.SUCCESS('\nSeed data loaded successfully!'))
        self.stdout.write('\nLogin credentials:')
        self.stdout.write('  Principal : maria.santos  / Password123!')
        self.stdout.write('  Teacher 1 : jose.reyes   / Password123!')
        self.stdout.write('  Teacher 2 : ana.cruz     / Password123!')
