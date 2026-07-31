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
