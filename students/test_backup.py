"""
Round-trip tests for backup_face_data / restore_face_data.

Face embeddings cannot be regenerated — losing them means physically
re-enrolling every student — so these assert the vectors survive export and
import bit-for-bit, not merely that the commands run.
"""
import json
import os
import tempfile
import uuid

from django.core.management import call_command
from django.test import TestCase

from classes.models import Class
from enrollments.models import Enrollment
from .face import cosine_similarity
from .models import Student, StudentEmbedding


def _vector(seed, dimensions=512):
	"""Deterministic, non-trivial vector — not a basis vector, so a silently
	truncated or reordered restore would be detected."""
	return [((seed * 37 + i * 13) % 100) / 100.0 for i in range(dimensions)]


class BackupRestoreRoundTripTests(TestCase):
	def setUp(self):
		self.tenant_id = uuid.uuid4()
		self.path = os.path.join(tempfile.mkdtemp(), 'backup.json')

		self.klass = Class.objects.create(
			tenant_id=self.tenant_id, class_name='10A Maths', subject='Maths',
			grade='10', section='A', academic_year='2026',
		)
		self.student = Student.objects.create(
			tenant_id=self.tenant_id, student_id='STU-1', name='Ana',
			grade='10', section='A',
		)
		self.embedding_values = _vector(3)
		StudentEmbedding.objects.create(
			student=self.student, tenant_id=self.tenant_id,
			embedding=self.embedding_values, backend='deepface',
			detector='retinaface', version=1, quality_score=0.97, is_active=True,
		)
		Enrollment.objects.create(
			student=self.student, tenant_id=self.tenant_id,
			academic_year='2026-2027', status='enrolled',
			embedding_generated=True, quality_score=0.97,
		)

	def _backup(self, **kwargs):
		call_command('backup_face_data', output=self.path, **kwargs)
		with open(self.path, encoding='utf-8') as handle:
			return json.load(handle)

	def test_backup_contains_the_face_data(self):
		payload = self._backup()
		self.assertEqual(len(payload['students']), 1)
		self.assertEqual(len(payload['embeddings']), 1)
		self.assertEqual(len(payload['embeddings'][0]['embedding']), 512)
		self.assertEqual(payload['embeddings'][0]['detector'], 'retinaface')

	def test_backup_excludes_admin_accounts(self):
		"""The file is meant to be copied around; password hashes must not ride along."""
		payload = self._backup()
		self.assertNotIn('admins', payload)
		self.assertNotIn('password_hash', json.dumps(payload))

	def test_restore_reproduces_the_embedding_exactly(self):
		self._backup()
		StudentEmbedding.objects.all().delete()
		Student.objects.all().delete()

		call_command('restore_face_data', self.path, no_input=True)

		restored = StudentEmbedding.objects.get()
		self.assertEqual(len(restored.embedding), 512)
		# Bit-for-bit, not merely similar: a match threshold would hide drift.
		self.assertEqual(list(restored.embedding), self.embedding_values)
		self.assertAlmostEqual(
			cosine_similarity(restored.embedding, self.embedding_values), 1.0, places=6,
		)
		self.assertEqual(restored.detector, 'retinaface')
		self.assertEqual(restored.backend, 'deepface')

	def test_restore_preserves_student_identity(self):
		original_id = str(self.student.id)
		self._backup()
		Student.objects.all().delete()

		call_command('restore_face_data', self.path, no_input=True)

		student = Student.objects.get()
		self.assertEqual(str(student.id), original_id)
		self.assertEqual(student.name, 'Ana')
		self.assertEqual(student.tenant_id, self.tenant_id)

	def test_restore_is_idempotent(self):
		self._backup()
		call_command('restore_face_data', self.path, no_input=True)
		call_command('restore_face_data', self.path, no_input=True)

		self.assertEqual(Student.objects.count(), 1)
		self.assertEqual(StudentEmbedding.objects.count(), 1)

	def test_tenant_filter_limits_the_export(self):
		other_tenant = uuid.uuid4()
		other = Student.objects.create(
			tenant_id=other_tenant, student_id='STU-9', name='Other',
			grade='10', section='A',
		)
		StudentEmbedding.objects.create(
			student=other, tenant_id=other_tenant, embedding=_vector(9),
			backend='deepface', version=1, is_active=True,
		)

		payload = self._backup(tenant=str(self.tenant_id))
		self.assertEqual(len(payload['students']), 1)
		self.assertEqual(payload['students'][0]['name'], 'Ana')
		self.assertEqual(len(payload['embeddings']), 1)

	def test_restore_rejects_an_unknown_format(self):
		from django.core.management.base import CommandError

		with open(self.path, 'w', encoding='utf-8') as handle:
			json.dump({'format_version': 999, 'students': []}, handle)

		with self.assertRaises(CommandError):
			call_command('restore_face_data', self.path, no_input=True)
