"""
API-level tests for the three endpoints the product actually depends on:
enrol, identify, and mark-attendance-by-face.

Face extraction is mocked. Running DeepFace here would make the suite slow,
require real photographs in the repository, and test TensorFlow rather than
this application — the interesting behaviour is what surrounds the embedding:
authentication, tenant scoping, validation, the identity check, threshold
handling, duplicate suppression and attendance status.

Vectors are constructed so their cosine similarity is known exactly, which is
what lets a threshold be asserted rather than approximated.
"""
import uuid
from datetime import datetime
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from admins.models import Admin
from attendance.models import StudentAttendance
from classes.models import Class
from students.models import Student, StudentEmbedding

DIMENSIONS = 512


def _unit_vector(index):
	"""Basis vector — orthogonal to every other, so cosine similarity is 0."""
	vector = [0.0] * DIMENSIONS
	vector[index] = 1.0
	return vector


def _near(vector, index, weight=0.06):
	"""A vector close to `vector` but not identical — a second photo of one face."""
	mixed = [v + (weight if i == index else 0.0) for i, v in enumerate(vector)]
	magnitude = sum(v * v for v in mixed) ** 0.5
	return [v / magnitude for v in mixed]


def _face(embedding, quality=0.98, backend='deepface', detector='retinaface'):
	"""What students.backends.extract_embedding returns."""
	return {
		'embedding': embedding,
		'quality_score': quality,
		'face_count': 1,
		'backend': backend,
		'detector': detector,
	}


def _image(name='face.jpg'):
	return SimpleUploadedFile(name, b'not-a-real-jpeg', content_type='image/jpeg')


class FaceApiTestCase(TestCase):
	"""Shared fixtures: one tenant, two students, an admin and a coordinator."""

	def setUp(self):
		cache.clear()
		self.tenant_id = uuid.uuid4()
		self.other_tenant = uuid.uuid4()

		self.admin = self._admin('head', 'head@example.com', 'admin', 3, self.tenant_id)
		self.coordinator = self._admin('coord', 'coord@example.com', 'admin', 2, self.tenant_id)
		self.teacher = self._admin('teach', 'teach@example.com', 'teacher', 1, self.tenant_id)

		self.alice = Student.objects.create(
			tenant_id=self.tenant_id, student_id='STU-A', name='Alice',
			grade='10', section='A',
		)
		self.bob = Student.objects.create(
			tenant_id=self.tenant_id, student_id='STU-B', name='Bob',
			grade='10', section='A',
		)
		self.outsider = Student.objects.create(
			tenant_id=self.other_tenant, student_id='STU-X', name='Outsider',
			grade='10', section='A',
		)

		self.alice_face = _unit_vector(0)
		self.bob_face = _unit_vector(1)

		self.client = APIClient()
		self.login('head')

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

	def enrol(self, student, face, **extra):
		"""POST the enrol endpoint with extraction mocked to return `face`."""
		with patch('students.views.extract_embedding', return_value=face):
			payload = {
				'image': _image(),
				'academic_year': '2026-2027',
				'enrolled_by': str(self.admin.id),
				**extra,
			}
			return self.client.post(
				f'/api/students/{student.id}/enroll/', payload, format='multipart',
			)

	def given_enrolled(self, student, embedding, backend='deepface', detector='retinaface'):
		"""Insert an embedding directly, bypassing the endpoint."""
		return StudentEmbedding.objects.create(
			student=student, tenant_id=student.tenant_id, embedding=embedding,
			backend=backend, detector=detector,
			version=StudentEmbedding.objects.filter(student=student).count() + 1,
			quality_score=0.95, is_active=True,
		)


class EnrolEndpointTests(FaceApiTestCase):
	def test_requires_authentication(self):
		self.client.credentials()
		response = self.client.post(f'/api/students/{self.alice.id}/enroll/', {}, format='multipart')
		self.assertIn(response.status_code, (401, 403))

	def test_image_is_required(self):
		response = self.client.post(
			f'/api/students/{self.alice.id}/enroll/',
			{'academic_year': '2026-2027', 'enrolled_by': str(self.admin.id)},
			format='multipart',
		)
		self.assertEqual(response.status_code, 400)
		self.assertIn('image', response.data)

	def test_academic_year_is_required(self):
		with patch('students.views.extract_embedding', return_value=_face(self.alice_face)):
			response = self.client.post(
				f'/api/students/{self.alice.id}/enroll/',
				{'image': _image(), 'enrolled_by': str(self.admin.id)},
				format='multipart',
			)
		self.assertEqual(response.status_code, 400)
		self.assertIn('academic_year', response.data)

	def test_successful_enrolment_stores_backend_and_detector(self):
		response = self.enrol(self.alice, _face(self.alice_face))
		self.assertEqual(response.status_code, 200, response.data)

		embedding = StudentEmbedding.objects.get(student=self.alice)
		self.assertEqual(embedding.backend, 'deepface')
		self.assertEqual(embedding.detector, 'retinaface')
		self.assertEqual(embedding.version, 1)
		self.assertEqual(len(embedding.embedding), DIMENSIONS)

	def test_undetectable_face_is_rejected(self):
		with patch('students.views.extract_embedding', side_effect=ValueError('No face detected.')):
			response = self.client.post(
				f'/api/students/{self.alice.id}/enroll/',
				{'image': _image(), 'academic_year': '2026-2027', 'enrolled_by': str(self.admin.id)},
				format='multipart',
			)
		self.assertEqual(response.status_code, 400)
		self.assertIn('No face detected', str(response.data))

	def test_very_low_quality_is_rejected(self):
		response = self.enrol(self.alice, _face(self.alice_face, quality=0.05))
		self.assertEqual(response.status_code, 400)
		self.assertNotIn('quality', str(response.data).lower()[:0])  # message is user-facing
		self.assertFalse(StudentEmbedding.objects.filter(student=self.alice).exists())

	def test_a_second_photo_of_the_same_face_is_accepted(self):
		self.enrol(self.alice, _face(self.alice_face))
		response = self.enrol(self.alice, _face(_near(self.alice_face, 1)))
		self.assertEqual(response.status_code, 200, response.data)
		self.assertEqual(StudentEmbedding.objects.filter(student=self.alice).count(), 2)

	def test_a_different_face_cannot_be_added_to_an_existing_student(self):
		"""The bug found in production: one person enrolled under another's record."""
		self.enrol(self.alice, _face(self.alice_face))
		response = self.enrol(self.alice, _face(self.bob_face))

		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data['code'], 'identity_mismatch')
		self.assertEqual(StudentEmbedding.objects.filter(student=self.alice).count(), 1)

	def test_a_face_already_enrolled_elsewhere_is_refused(self):
		self.enrol(self.bob, _face(self.bob_face))
		response = self.enrol(self.alice, _face(self.bob_face))

		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data['code'], 'duplicate_face')
		self.assertEqual(response.data['conflicting_student']['student_id'], 'STU-B')
		self.assertFalse(StudentEmbedding.objects.filter(student=self.alice).exists())

	def test_override_allows_a_coordinator_past_the_check(self):
		self.enrol(self.alice, _face(self.alice_face))
		self.login('coord')
		response = self.enrol(self.alice, _face(self.bob_face), override='true')

		self.assertEqual(response.status_code, 200, response.data)
		self.assertEqual(StudentEmbedding.objects.filter(student=self.alice).count(), 2)

	def test_override_is_refused_to_a_teacher(self):
		self.enrol(self.alice, _face(self.alice_face))
		self.login('teach')
		response = self.enrol(self.alice, _face(self.bob_face), override='true')

		self.assertEqual(response.status_code, 409)
		self.assertEqual(response.data['code'], 'override_forbidden')

	def test_cannot_enrol_a_student_from_another_tenant(self):
		response = self.enrol(self.outsider, _face(self.alice_face))
		self.assertEqual(response.status_code, 404)
		self.assertFalse(StudentEmbedding.objects.filter(student=self.outsider).exists())

	def test_photo_limit_is_enforced(self):
		for i in range(5):
			self.given_enrolled(self.alice, _near(self.alice_face, i + 1))
		response = self.enrol(self.alice, _face(_near(self.alice_face, 7)))

		self.assertEqual(response.status_code, 400)
		self.assertIn('Maximum of 5', str(response.data))


class StudentListQueryCountTests(FaceApiTestCase):
	"""
	photo_count used to be counted per student, so listing a roster issued one
	query per row — 201 for 200 students. Over a network round-trip that is the
	difference between a page that loads and one that appears to hang.
	"""

	def _queries_to_list(self):
		from django.db import connection
		from django.test.utils import CaptureQueriesContext

		with CaptureQueriesContext(connection) as captured:
			response = self.client.get('/api/students/')
		self.assertEqual(response.status_code, 200)
		return len(captured), len(response.data['results'])

	def _add_students(self, count, prefix):
		Student.objects.bulk_create([
			Student(tenant_id=self.tenant_id, student_id=f'{prefix}-{i:03d}',
			        name=f'Student {i}', grade='10', section='A')
			for i in range(count)
		])

	def test_query_count_does_not_grow_with_roster_size(self):
		"""
		The assertion is the *shape*, not a magic number: adding a hundred
		students must not add a hundred queries. A fixed count would break on
		any unrelated middleware change while missing the regression that
		matters.
		"""
		# Both sizes stay inside one page, so the comparison is about rows
		# serialised rather than pagination.
		self._add_students(6, 'SMALL')
		few_queries, few_rows = self._queries_to_list()

		self._add_students(35, 'LARGE')
		many_queries, many_rows = self._queries_to_list()

		self.assertGreater(many_rows, few_rows + 30, 'expected the roster to grow')
		self.assertEqual(
			few_queries, many_queries,
			f'{few_rows} students took {few_queries} queries but {many_rows} took '
			f'{many_queries} — the count scales with the roster (N+1)',
		)

	def test_photo_count_is_still_accurate(self):
		self.given_enrolled(self.alice, self.alice_face)
		self.given_enrolled(self.alice, _near(self.alice_face, 2))
		self.given_enrolled(self.bob, self.bob_face)

		response = self.client.get('/api/students/')
		counts = {row['student_id']: row['photo_count'] for row in response.data['results']}

		self.assertEqual(counts['STU-A'], 2)
		self.assertEqual(counts['STU-B'], 1)

	def test_inactive_photos_are_not_counted(self):
		self.given_enrolled(self.alice, self.alice_face)
		StudentEmbedding.objects.filter(student=self.alice).update(is_active=False)

		response = self.client.get('/api/students/')
		counts = {row['student_id']: row['photo_count'] for row in response.data['results']}
		self.assertEqual(counts['STU-A'], 0)

	def test_detail_view_still_reports_photo_count(self):
		"""The serializer falls back to counting when there is no annotation."""
		self.given_enrolled(self.alice, self.alice_face)
		from students.serializers import StudentSerializer

		unannotated = Student.objects.get(pk=self.alice.pk)
		self.assertEqual(StudentSerializer(unannotated).data['photo_count'], 1)


class IdentifyEndpointTests(FaceApiTestCase):
	def identify(self, face, **extra):
		with patch('students.views.extract_embedding', return_value=face):
			return self.client.post(
				'/api/students/identify/',
				{'image': _image(), **extra},
				format='multipart',
			)

	def test_requires_authentication(self):
		self.client.credentials()
		response = self.client.post('/api/students/identify/', {}, format='multipart')
		self.assertIn(response.status_code, (401, 403))

	def test_image_is_required(self):
		response = self.client.post('/api/students/identify/', {}, format='multipart')
		self.assertEqual(response.status_code, 400)

	def test_matches_the_enrolled_student(self):
		self.given_enrolled(self.alice, self.alice_face)
		response = self.identify(_face(_near(self.alice_face, 1)))

		self.assertEqual(response.status_code, 200, response.data)
		self.assertEqual(response.data['match']['student_id'], 'STU-A')
		self.assertGreater(response.data['confidence'], 0.65)

	def test_a_different_face_is_not_matched(self):
		self.given_enrolled(self.alice, self.alice_face)
		response = self.identify(_face(self.bob_face))

		self.assertEqual(response.status_code, 404)
		self.assertIsNone(response.data['match'])
		self.assertLess(response.data['confidence'], 0.65)

	def test_returns_404_when_nobody_is_enrolled(self):
		response = self.identify(_face(self.alice_face))
		self.assertEqual(response.status_code, 404)

	def test_another_tenants_student_is_never_matched(self):
		"""Identify must not reach across schools, even for an identical face."""
		self.given_enrolled(self.outsider, self.alice_face)
		response = self.identify(_face(self.alice_face))

		self.assertEqual(response.status_code, 404)
		self.assertIsNone(response.data['match'])

	def test_a_supplied_tenant_id_is_ignored(self):
		self.given_enrolled(self.outsider, self.alice_face)
		response = self.identify(_face(self.alice_face), tenant_id=str(self.other_tenant))

		self.assertEqual(response.status_code, 404)

	def test_threshold_must_be_a_fraction(self):
		response = self.identify(_face(self.alice_face), threshold='7')
		self.assertEqual(response.status_code, 400)
		self.assertIn('threshold', response.data)

	def test_embeddings_from_another_backend_are_not_compared(self):
		"""ArcFace and Facenet512 occupy different vector spaces."""
		self.given_enrolled(self.alice, self.alice_face, backend='onnx')
		response = self.identify(_face(self.alice_face))
		self.assertEqual(response.status_code, 404)


@override_settings(TIME_ZONE='America/Barbados')
class MarkByFaceEndpointTests(FaceApiTestCase):
	def setUp(self):
		super().setUp()
		self.klass = Class.objects.create(
			tenant_id=self.tenant_id, class_name='10A Maths', subject='Maths',
			grade='10', section='A', academic_year='2026-2027',
		)
		self.other_class = Class.objects.create(
			tenant_id=self.other_tenant, class_name='Other', subject='Maths',
			grade='10', section='A', academic_year='2026-2027',
		)

	def mark(self, face, at=None, **extra):
		payload = {'image': _image(), 'class_id': self.klass.id, **extra}
		with patch('students.backends.extract_embedding', return_value=face):
			if at is None:
				return self.client.post('/api/attendance/mark-by-face/', payload, format='multipart')
			with patch('django.utils.timezone.now', return_value=at):
				return self.client.post('/api/attendance/mark-by-face/', payload, format='multipart')

	def _at(self, hour, minute):
		return datetime(2026, 9, 1, hour, minute, tzinfo=ZoneInfo('America/Barbados'))

	def test_class_id_is_required(self):
		with patch('students.backends.extract_embedding', return_value=_face(self.alice_face)):
			response = self.client.post(
				'/api/attendance/mark-by-face/', {'image': _image()}, format='multipart',
			)
		self.assertEqual(response.status_code, 400)
		self.assertIn('class_id', response.data)

	def test_marks_a_recognised_student(self):
		self.given_enrolled(self.alice, self.alice_face)
		response = self.mark(_face(_near(self.alice_face, 1)))

		self.assertEqual(response.status_code, 201, response.data)
		self.assertEqual(response.data['match']['student_id'], 'STU-A')
		self.assertFalse(response.data['already_marked'])

		record = StudentAttendance.objects.get()
		self.assertEqual(record.student, self.alice)
		self.assertEqual(record.class_ref, self.klass)
		self.assertEqual(record.tenant_id, self.tenant_id)

	def test_arrival_before_the_cutoff_is_present(self):
		self.given_enrolled(self.alice, self.alice_face)
		response = self.mark(_face(self.alice_face), at=self._at(6, 45))
		self.assertEqual(response.data['status'], 'present')

	def test_arrival_after_the_cutoff_is_late(self):
		self.given_enrolled(self.alice, self.alice_face)
		response = self.mark(_face(self.alice_face), at=self._at(8, 30))
		self.assertEqual(response.data['status'], 'late')

	@override_settings(TIME_ZONE='Asia/Manila')
	def test_the_timezone_bug_would_be_caught(self):
		"""Under the old zone a 06:45 Barbados arrival was evaluated as 18:45."""
		self.given_enrolled(self.alice, self.alice_face)
		response = self.mark(_face(self.alice_face), at=self._at(6, 45))
		self.assertEqual(response.data['status'], 'late')

	def test_marking_twice_does_not_duplicate(self):
		self.given_enrolled(self.alice, self.alice_face)
		self.mark(_face(self.alice_face))
		second = self.mark(_face(self.alice_face))

		self.assertTrue(second.data['already_marked'])
		self.assertEqual(StudentAttendance.objects.count(), 1)

	def test_an_unrecognised_face_marks_nobody(self):
		self.given_enrolled(self.alice, self.alice_face)
		response = self.mark(_face(self.bob_face))

		self.assertEqual(response.status_code, 404)
		self.assertIsNone(response.data['match'])
		self.assertEqual(StudentAttendance.objects.count(), 0)

	def test_cannot_mark_against_another_tenants_class(self):
		self.given_enrolled(self.alice, self.alice_face)
		response = self.mark(_face(self.alice_face), class_id=self.other_class.id)

		self.assertEqual(response.status_code, 404)
		self.assertEqual(StudentAttendance.objects.count(), 0)

	def test_another_tenants_student_is_never_marked(self):
		self.given_enrolled(self.outsider, self.alice_face)
		response = self.mark(_face(self.alice_face))

		self.assertEqual(response.status_code, 404)
		self.assertEqual(StudentAttendance.objects.count(), 0)
