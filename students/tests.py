"""
Tests for face-embedding nearest-neighbour matching.

These exercise the SQLite scan path, since the test database is SQLite. The
PostgreSQL path delegates ordering to pgvector's CosineDistance and returns
``1 - distance``, which is the same similarity measure asserted here.
"""
import uuid

from django.test import TestCase

from admins.models import Admin
from .face import cosine_similarity
from .matching import best_match
from .models import Student, StudentEmbedding


def _unit_vector(index, dimensions=512):
	"""A 512-dim basis vector — orthogonal to every other basis vector."""
	vector = [0.0] * dimensions
	vector[index] = 1.0
	return vector


def _blend(a, b, weight):
	"""Normalised mix of two vectors, so similarity sits strictly between them."""
	mixed = [x * (1 - weight) + y * weight for x, y in zip(a, b)]
	magnitude = sum(v * v for v in mixed) ** 0.5
	return [v / magnitude for v in mixed]


class EnrolmentIdentityCheckTests(TestCase):
	"""
	Enrolment must refuse a face that is not the student it is filed under.

	Without this, any face could be attached to any record — a student could
	enrol their own face under a classmate's name and have it mark that
	classmate present every morning.

	_check_enrolment_identity is called directly with a stub request; the view
	around it is exercised by the fuller API tests.
	"""

	class _StubRequest:
		def __init__(self, user, data=None):
			self.user = user
			self.data = data or {}

	def setUp(self):
		from .views import _check_enrolment_identity
		self.check = _check_enrolment_identity

		self.tenant_id = uuid.uuid4()
		self.coordinator = Admin.objects.create(
			tenant_id=self.tenant_id, admin_name='coord', email='coord@example.com',
			password_hash='x', role='admin', authorization_level=2,
		)
		self.teacher = Admin.objects.create(
			tenant_id=self.tenant_id, admin_name='teach', email='teach@example.com',
			password_hash='x', role='teacher', authorization_level=1,
		)
		self.alice = Student.objects.create(
			tenant_id=self.tenant_id, student_id='STU-A', name='Alice',
			grade='10', section='A',
		)
		self.bob = Student.objects.create(
			tenant_id=self.tenant_id, student_id='STU-B', name='Bob',
			grade='10', section='A',
		)

		self.alice_face = _unit_vector(0)
		self.bob_face = _unit_vector(1)

	def _enrol(self, student, vector):
		return StudentEmbedding.objects.create(
			student=student, tenant_id=self.tenant_id, embedding=vector,
			backend='deepface', version=1, is_active=True,
		)

	def _face(self, vector):
		return {'embedding': vector, 'quality_score': 0.99, 'backend': 'deepface'}

	def test_first_photo_for_a_student_is_accepted(self):
		result = self.check(self._StubRequest(self.coordinator), self.alice, self._face(self.alice_face))
		self.assertIsNone(result)

	def test_same_face_may_add_another_photo(self):
		self._enrol(self.alice, self.alice_face)
		near_identical = _blend(self.alice_face, _unit_vector(9), 0.05)
		result = self.check(self._StubRequest(self.coordinator), self.alice, self._face(near_identical))
		self.assertIsNone(result)

	def test_different_face_cannot_be_added_to_an_existing_student(self):
		"""The reported bug: enrolling one's own face under someone else's record."""
		self._enrol(self.alice, self.alice_face)
		result = self.check(self._StubRequest(self.coordinator), self.alice, self._face(self.bob_face))
		self.assertIsNotNone(result)
		self.assertEqual(result['code'], 'identity_mismatch')

	def test_face_already_enrolled_elsewhere_is_refused(self):
		"""Filing an already-known face under a second name makes attendance ambiguous."""
		self._enrol(self.bob, self.bob_face)
		result = self.check(self._StubRequest(self.coordinator), self.alice, self._face(self.bob_face))
		self.assertIsNotNone(result)
		self.assertEqual(result['code'], 'duplicate_face')
		self.assertEqual(result['conflicting_student']['student_id'], 'STU-B')

	def test_unrelated_face_is_fine_as_a_first_photo(self):
		self._enrol(self.bob, self.bob_face)
		result = self.check(self._StubRequest(self.coordinator), self.alice, self._face(self.alice_face))
		self.assertIsNone(result)

	def test_override_lets_a_coordinator_through(self):
		self._enrol(self.alice, self.alice_face)
		request = self._StubRequest(self.coordinator, {'override': 'true'})
		self.assertIsNone(self.check(request, self.alice, self._face(self.bob_face)))

	def test_override_is_refused_below_level_two(self):
		self._enrol(self.alice, self.alice_face)
		request = self._StubRequest(self.teacher, {'override': 'true'})
		result = self.check(request, self.alice, self._face(self.bob_face))
		self.assertIsNotNone(result)
		self.assertEqual(result['code'], 'override_forbidden')

	def test_check_is_scoped_to_the_students_tenant(self):
		"""Another school's enrolment must not block or influence this one."""
		other_tenant = uuid.uuid4()
		stranger = Student.objects.create(
			tenant_id=other_tenant, student_id='STU-X', name='Stranger',
			grade='10', section='A',
		)
		StudentEmbedding.objects.create(
			student=stranger, tenant_id=other_tenant, embedding=self.alice_face,
			backend='deepface', version=1, is_active=True,
		)
		result = self.check(self._StubRequest(self.coordinator), self.alice, self._face(self.alice_face))
		self.assertIsNone(result)

	def test_embeddings_from_another_backend_are_ignored(self):
		"""ArcFace and Facenet512 vectors are not comparable — see backends.py."""
		StudentEmbedding.objects.create(
			student=self.alice, tenant_id=self.tenant_id, embedding=self.alice_face,
			backend='onnx', version=1, is_active=True,
		)
		result = self.check(self._StubRequest(self.coordinator), self.alice, self._face(self.bob_face))
		self.assertIsNone(result)


class BestMatchTests(TestCase):
	def setUp(self):
		self.tenant_id = uuid.uuid4()
		self.enroller = Admin.objects.create(
			tenant_id=self.tenant_id,
			admin_name='enroller',
			email='enroller@example.com',
			password_hash='x',
			role='admin',
			authorization_level=3,
		)

	def _enrol(self, name, student_id, vector, is_active=True):
		student = Student.objects.create(
			tenant_id=self.tenant_id, student_id=student_id,
			name=name, grade='10', section='A',
		)
		StudentEmbedding.objects.create(
			student=student, tenant_id=self.tenant_id, embedding=vector,
			version=1, quality_score=0.9, enrolled_by=self.enroller,
			is_active=is_active,
		)
		return student

	def _active(self):
		return StudentEmbedding.objects.filter(
			tenant_id=self.tenant_id, is_active=True
		).select_related('student')

	def test_returns_none_when_nothing_enrolled(self):
		embedding, score = best_match(self._active(), _unit_vector(0))
		self.assertIsNone(embedding)
		self.assertEqual(score, -1.0)

	def test_identical_vector_scores_one(self):
		self._enrol('Ana', 'STU-1', _unit_vector(0))
		embedding, score = best_match(self._active(), _unit_vector(0))
		self.assertEqual(embedding.student.name, 'Ana')
		self.assertAlmostEqual(score, 1.0, places=5)

	def test_picks_the_nearest_of_several(self):
		self._enrol('Ana', 'STU-1', _unit_vector(0))
		self._enrol('Ben', 'STU-2', _unit_vector(1))
		self._enrol('Cleo', 'STU-3', _unit_vector(2))

		# Mostly Ben, slightly Cleo — Ben must win.
		query = _blend(_unit_vector(1), _unit_vector(2), 0.25)
		embedding, score = best_match(self._active(), query)

		self.assertEqual(embedding.student.name, 'Ben')
		self.assertGreater(score, 0.9)

	def test_orthogonal_vectors_score_zero(self):
		"""A different person must not score near 1 — the failure mode that made
		every face match whoever was enrolled first."""
		self._enrol('Ana', 'STU-1', _unit_vector(0))
		_, score = best_match(self._active(), _unit_vector(7))
		self.assertAlmostEqual(score, 0.0, places=5)

	def test_inactive_embeddings_are_not_matched(self):
		self._enrol('Ana', 'STU-1', _unit_vector(0), is_active=False)
		embedding, _ = best_match(self._active(), _unit_vector(0))
		self.assertIsNone(embedding)

	def test_agrees_with_direct_cosine_similarity(self):
		"""best_match must report the same measure the rest of the code uses."""
		vector = _blend(_unit_vector(3), _unit_vector(4), 0.4)
		self._enrol('Ana', 'STU-1', vector)

		query = _unit_vector(3)
		_, score = best_match(self._active(), query)
		self.assertAlmostEqual(score, cosine_similarity(query, vector), places=5)


class BackendSelectionTests(TestCase):
	def test_default_backend_is_deepface(self):
		from .backends import DEEPFACE, active_backend
		self.assertEqual(active_backend(), DEEPFACE)

	def test_unknown_backend_is_rejected(self):
		from django.test import override_settings
		from .backends import active_backend

		with override_settings(FACE_BACKEND='not-a-backend'):
			with self.assertRaises(ValueError):
				active_backend()

	def test_embeddings_record_their_backend(self):
		student = Student.objects.create(
			tenant_id=uuid.uuid4(), student_id='STU-9',
			name='Dana', grade='11', section='C',
		)
		embedding = StudentEmbedding.objects.create(
			student=student, tenant_id=student.tenant_id,
			embedding=_unit_vector(0), version=1, is_active=True,
		)
		self.assertEqual(embedding.backend, 'deepface')

	def test_matching_never_crosses_backends(self):
		"""Facenet512 and ArcFace occupy different vector spaces — an identical
		vector from the other backend must not be returned as a match."""
		tenant_id = uuid.uuid4()
		student = Student.objects.create(
			tenant_id=tenant_id, student_id='STU-10',
			name='Eli', grade='11', section='C',
		)
		StudentEmbedding.objects.create(
			student=student, tenant_id=tenant_id, embedding=_unit_vector(0),
			backend='onnx', version=1, is_active=True,
		)

		deepface_scoped = StudentEmbedding.objects.filter(
			tenant_id=tenant_id, is_active=True, backend='deepface',
		).select_related('student')

		embedding, _ = best_match(deepface_scoped, _unit_vector(0))
		self.assertIsNone(embedding)


class TenantScopingOfMatchesTests(TestCase):
	"""best_match applies no filtering itself — callers must scope the queryset."""

	def test_only_the_supplied_queryset_is_searched(self):
		tenant_a, tenant_b = uuid.uuid4(), uuid.uuid4()
		for tenant, name, sid in ((tenant_a, 'Ana', 'A-1'), (tenant_b, 'Bea', 'B-1')):
			student = Student.objects.create(
				tenant_id=tenant, student_id=sid, name=name, grade='10', section='A',
			)
			StudentEmbedding.objects.create(
				student=student, tenant_id=tenant, embedding=_unit_vector(0),
				version=1, is_active=True,
			)

		scoped = StudentEmbedding.objects.filter(
			tenant_id=tenant_a, is_active=True
		).select_related('student')

		embedding, score = best_match(scoped, _unit_vector(0))
		self.assertEqual(embedding.student.name, 'Ana')
		self.assertAlmostEqual(score, 1.0, places=5)
