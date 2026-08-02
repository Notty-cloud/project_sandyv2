"""
Tests for CSV roster import.

The parser is exercised directly and through the endpoint. Bulk creation is
where a small mistake becomes hundreds of wrong records, so these lean on the
failure modes: duplicates, malformed rows, encodings, tenant leakage, and the
guarantee that a preview reports exactly what the real import would do.
"""
import uuid

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from admins.models import Admin
from .importer import ImportError_, parse_students_csv
from .models import Student

GOOD_CSV = (
	'student_id,name,grade,section\n'
	'STU-001,Ana Alpha,10,A\n'
	'STU-002,Ben Beta,10,B\n'
	'STU-003,Cleo Gamma,9,A\n'
)


def _csv_file(text, name='roster.csv', encoding='utf-8'):
	return SimpleUploadedFile(name, text.encode(encoding), content_type='text/csv')


class ParserTests(TestCase):
	def test_parses_a_clean_file(self):
		rows, errors = parse_students_csv(GOOD_CSV.encode())
		self.assertEqual(len(rows), 3)
		self.assertEqual(errors, [])
		self.assertEqual(rows[0]['student_id'], 'STU-001')
		self.assertTrue(rows[0]['is_active'])

	def test_header_case_and_spacing_are_forgiving(self):
		text = ' Student ID , NAME , Grade , Section \nSTU-9,Zoe,11,C\n'
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(errors, [])
		self.assertEqual(rows[0]['name'], 'Zoe')

	def test_unknown_columns_are_ignored(self):
		"""Registry exports carry extra fields; rejecting the file would send
		people back to manual entry."""
		text = 'student_id,name,grade,section,guardian_phone\nSTU-1,Ana,10,A,555-0100\n'
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(errors, [])
		self.assertEqual(len(rows), 1)

	def test_excel_byte_order_mark_is_handled(self):
		"""Excel writes a BOM; without stripping it the first column reads
		'﻿student_id' and the file looks like it lacks student_id."""
		rows, errors = parse_students_csv(GOOD_CSV.encode('utf-8-sig'))
		self.assertEqual(len(rows), 3)
		self.assertEqual(errors, [])

	def test_semicolon_delimiter_is_accepted(self):
		text = 'student_id;name;grade;section\nSTU-1;Ana;10;A\n'
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(errors, [])
		self.assertEqual(rows[0]['student_id'], 'STU-1')

	def test_missing_required_column_rejects_the_file(self):
		with self.assertRaises(ImportError_) as caught:
			parse_students_csv(b'student_id,name\nSTU-1,Ana\n')
		self.assertIn('grade', str(caught.exception))

	def test_blank_lines_are_not_errors(self):
		rows, errors = parse_students_csv((GOOD_CSV + '\n\n').encode())
		self.assertEqual(len(rows), 3)
		self.assertEqual(errors, [])

	def test_a_row_missing_a_field_is_reported_not_fatal(self):
		text = GOOD_CSV + 'STU-004,,9,B\n'
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(len(rows), 3)
		self.assertEqual(len(errors), 1)
		self.assertEqual(errors[0]['row'], 5)
		self.assertIn('name', errors[0]['error'])

	def test_duplicate_within_the_file_is_reported_once(self):
		text = GOOD_CSV + 'STU-001,Ana Again,10,A\n'
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(len(rows), 3)
		self.assertEqual(len(errors), 1)
		self.assertIn('appears twice', errors[0]['error'])

	def test_existing_student_id_is_skipped(self):
		rows, errors = parse_students_csv(GOOD_CSV.encode(), existing_student_ids=['STU-002'])
		self.assertEqual([r['student_id'] for r in rows], ['STU-001', 'STU-003'])
		self.assertEqual(len(errors), 1)
		self.assertIn('already exists', errors[0]['error'])

	def test_is_active_accepts_common_spellings(self):
		text = (
			'student_id,name,grade,section,is_active\n'
			'STU-1,Ana,10,A,no\n'
			'STU-2,Ben,10,A,TRUE\n'
		)
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(errors, [])
		self.assertFalse(rows[0]['is_active'])
		self.assertTrue(rows[1]['is_active'])

	def test_unparseable_is_active_is_reported(self):
		text = 'student_id,name,grade,section,is_active\nSTU-1,Ana,10,A,maybe\n'
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(rows, [])
		self.assertIn('is_active', errors[0]['error'])

	def test_overlong_value_is_reported_not_raised(self):
		"""Caught here rather than as a database error partway through."""
		text = f'student_id,name,grade,section\nSTU-1,{"x" * 300},10,A\n'
		rows, errors = parse_students_csv(text.encode())
		self.assertEqual(rows, [])
		self.assertIn('too long', errors[0]['error'])

	def test_empty_file_is_rejected(self):
		with self.assertRaises(ImportError_):
			parse_students_csv(b'')

	def test_header_without_rows_is_rejected(self):
		with self.assertRaises(ImportError_):
			parse_students_csv(b'student_id,name,grade,section\n')

	def test_oversized_file_is_rejected(self):
		with self.assertRaises(ImportError_) as caught:
			parse_students_csv(b'x' * (3 * 1024 * 1024))
		self.assertIn('too large', str(caught.exception))


class ImportEndpointTests(TestCase):
	def setUp(self):
		cache.clear()
		self.tenant_id = uuid.uuid4()
		self.other_tenant = uuid.uuid4()
		self.coordinator = self._admin('coord', 'coord@example.com', 'admin', 2, self.tenant_id)
		self.teacher = self._admin('teach', 'teach@example.com', 'teacher', 1, self.tenant_id)
		self.client = APIClient()
		self.login('coord')

	def _admin(self, name, email, role, level, tenant_id):
		return Admin.objects.create(
			tenant_id=tenant_id, admin_name=name, email=email,
			password_hash=make_password('SecurePass1!', hasher='bcrypt_sha256'),
			role=role, authorization_level=level, must_change_password=False,
		)

	def login(self, admin_name):
		response = self.client.post(
			'/api/auth/login/',
			{'admin_name': admin_name, 'password': 'SecurePass1!'},
			format='json',
		)
		self.assertEqual(response.status_code, 200, response.data)
		self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access_token']}")

	def post(self, text=GOOD_CSV, **extra):
		return self.client.post(
			'/api/students/import-csv/',
			{'file': _csv_file(text), **extra},
			format='multipart',
		)

	def test_requires_authentication(self):
		self.client.credentials()
		self.assertIn(self.post().status_code, (401, 403))

	def test_a_teacher_cannot_import(self):
		self.login('teach')
		response = self.post()
		self.assertEqual(response.status_code, 403)
		self.assertEqual(Student.objects.count(), 0)

	def test_file_is_required(self):
		response = self.client.post('/api/students/import-csv/', {}, format='multipart')
		self.assertEqual(response.status_code, 400)
		self.assertIn('file', response.data)

	def test_imports_into_the_callers_tenant(self):
		response = self.post()
		self.assertEqual(response.status_code, 201, response.data)
		self.assertEqual(response.data['created'], 3)
		self.assertEqual(Student.objects.count(), 3)
		for student in Student.objects.all():
			self.assertEqual(student.tenant_id, self.tenant_id)

	def test_dry_run_writes_nothing(self):
		response = self.post(dry_run='true')
		self.assertEqual(response.status_code, 200)
		self.assertTrue(response.data['dry_run'])
		self.assertEqual(response.data['would_create'], 3)
		self.assertEqual(Student.objects.count(), 0)

	def test_dry_run_matches_the_real_import(self):
		"""A preview that disagrees with the import it precedes is worse than none."""
		text = GOOD_CSV + 'STU-004,,9,B\n'
		preview = self.post(text, dry_run='true')
		actual = self.post(text)

		self.assertEqual(preview.data['would_create'], actual.data['created'])
		self.assertEqual(preview.data['skipped'], actual.data['skipped'])

	def test_bad_rows_do_not_stop_the_good_ones(self):
		text = GOOD_CSV + 'STU-004,,9,B\nSTU-005,Eve,11,C\n'
		response = self.post(text)

		self.assertEqual(response.data['created'], 4)
		self.assertEqual(response.data['skipped'], 1)
		self.assertEqual(Student.objects.count(), 4)

	def test_reimporting_the_same_file_creates_nothing_new(self):
		self.post()
		second = self.post()

		self.assertEqual(second.data['created'], 0)
		self.assertEqual(second.data['skipped'], 3)
		self.assertEqual(Student.objects.count(), 3)

	def test_a_malformed_file_is_rejected_with_a_reason(self):
		response = self.post('nonsense\n')
		self.assertEqual(response.status_code, 400)
		self.assertIn('Missing required column', response.data['file'])

	def test_another_tenants_ids_do_not_block_this_one(self):
		"""Two schools may legitimately both number their students STU-001."""
		Student.objects.create(
			tenant_id=self.other_tenant, student_id='OTHER-1', name='Outsider',
			grade='10', section='A',
		)
		response = self.post()
		self.assertEqual(response.data['created'], 3)
