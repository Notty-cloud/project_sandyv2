"""
Cross-tenant isolation tests.

Every model carries a tenant_id, but before these tests nothing enforced it:
the viewsets filtered on a tenant_id supplied by the *client*, so omitting the
parameter returned every school's records. These tests pin the corrected
behaviour — the tenant comes from the authenticated account and client-supplied
values are ignored.
"""
import uuid

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from classes.models import Class
from students.models import Student

from .models import Admin


class CrossTenantIsolationTests(TestCase):
	def setUp(self):
		cache.clear()
		self.tenant_a = uuid.uuid4()
		self.tenant_b = uuid.uuid4()

		self.admin_a = self._make_admin(self.tenant_a, 'head.a', 'a@example.com')
		self.admin_b = self._make_admin(self.tenant_b, 'head.b', 'b@example.com')

		self.student_a = Student.objects.create(
			tenant_id=self.tenant_a, student_id='STU-A1',
			name='Ana Alpha', grade='10', section='A',
		)
		self.student_b = Student.objects.create(
			tenant_id=self.tenant_b, student_id='STU-B1',
			name='Bea Beta', grade='10', section='A',
		)

		self.class_b = Class.objects.create(
			tenant_id=self.tenant_b, class_name='B-Maths', subject='Maths',
			grade='10', section='A', academic_year='2026',
		)

		self.client = APIClient()
		self._authenticate(self.client, 'head.a')

	def _make_admin(self, tenant_id, name, email):
		return Admin.objects.create(
			tenant_id=tenant_id,
			admin_name=name,
			email=email,
			password_hash=make_password('SecurePass1!', hasher='bcrypt_sha256'),
			role='admin',
			authorization_level=3,
			must_change_password=False,
		)

	def _authenticate(self, client, admin_name):
		response = client.post(
			'/api/auth/login/',
			{'admin_name': admin_name, 'password': 'SecurePass1!'},
			format='json',
		)
		self.assertEqual(response.status_code, 200, response.data)
		client.credentials(HTTP_AUTHORIZATION=f"Bearer {response.data['access_token']}")

	# ── Reads ────────────────────────────────────────────────────────────────

	def test_student_list_excludes_other_tenants(self):
		"""The regression that started this: no tenant_id param used to mean no filter."""
		response = self.client.get('/api/students/')
		self.assertEqual(response.status_code, 200)
		names = {row['name'] for row in response.data['results']}
		self.assertEqual(names, {'Ana Alpha'})

	def test_client_supplied_tenant_id_cannot_widen_access(self):
		response = self.client.get(f'/api/students/?tenant_id={self.tenant_b}')
		self.assertEqual(response.status_code, 200)
		names = {row['name'] for row in response.data['results']}
		self.assertEqual(names, {'Ana Alpha'})

	def test_retrieving_another_tenants_student_is_404(self):
		response = self.client.get(f'/api/students/{self.student_b.id}/')
		self.assertEqual(response.status_code, 404)

	def test_class_list_excludes_other_tenants(self):
		response = self.client.get('/api/classes/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.data['results'], [])

	def test_admin_list_excludes_other_tenants(self):
		response = self.client.get('/api/admin/')
		self.assertEqual(response.status_code, 200)
		names = {row['admin_name'] for row in response.data}
		self.assertEqual(names, {'head.a'})

	# ── Writes ───────────────────────────────────────────────────────────────

	def test_creating_a_student_ignores_supplied_tenant_id(self):
		response = self.client.post(
			'/api/students/',
			{
				'tenant_id': str(self.tenant_b),
				'student_id': 'STU-A2',
				'name': 'Carl Gamma',
				'grade': '9',
				'section': 'B',
			},
			format='json',
		)
		self.assertEqual(response.status_code, 201, response.data)
		created = Student.objects.get(student_id='STU-A2')
		self.assertEqual(created.tenant_id, self.tenant_a)

	def test_updating_another_tenants_student_is_404(self):
		response = self.client.patch(
			f'/api/students/{self.student_b.id}/',
			{'name': 'Renamed'},
			format='json',
		)
		self.assertEqual(response.status_code, 404)
		self.student_b.refresh_from_db()
		self.assertEqual(self.student_b.name, 'Bea Beta')

	def test_deleting_another_tenants_student_is_404(self):
		response = self.client.delete(f'/api/students/{self.student_b.id}/')
		self.assertEqual(response.status_code, 404)
		self.assertTrue(Student.objects.filter(pk=self.student_b.pk).exists())

	def test_cannot_unlock_another_tenants_admin(self):
		self.admin_b.is_locked = True
		self.admin_b.failed_login_attempts = 5
		self.admin_b.save(update_fields=['is_locked', 'failed_login_attempts'])

		response = self.client.post(f'/api/admin/{self.admin_b.id}/unlock/')
		self.assertEqual(response.status_code, 404)

		self.admin_b.refresh_from_db()
		self.assertTrue(self.admin_b.is_locked)

	def test_created_admin_belongs_to_creator_tenant(self):
		response = self.client.post(
			'/api/admin/',
			{
				'tenant_id': str(self.tenant_b),
				'admin_name': 'new.teacher',
				'email': 'new@example.com',
				'password': 'SecurePass1!',
				'role': 'teacher',
				'authorization_level': 1,
			},
			format='json',
		)
		self.assertEqual(response.status_code, 201, response.data)
		self.assertEqual(Admin.objects.get(admin_name='new.teacher').tenant_id, self.tenant_a)
