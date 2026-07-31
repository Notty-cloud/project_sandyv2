import uuid

from django.contrib.auth.hashers import make_password
from django.core.cache import cache
from django.test import TestCase
from rest_framework.test import APIClient

from .models import Admin, TokenBlacklist


class AuthenticationFlowTests(TestCase):
	def setUp(self):
		cache.clear()
		self.client = APIClient()
		self.tenant_id = uuid.uuid4()
		self.admin = Admin.objects.create(
			tenant_id=self.tenant_id,
			admin_name='samuel',
			email='samuel@example.com',
			password_hash=make_password('SecurePass1!', hasher='bcrypt_sha256'),
			role='admin',
			authorization_level=3,
			must_change_password=True,
		)
		self.teacher = Admin.objects.create(
			tenant_id=self.tenant_id,
			admin_name='teacher.jane',
			email='teacher@example.com',
			password_hash=make_password('TeacherPass1!', hasher='bcrypt_sha256'),
			role='teacher',
			authorization_level=1,
			must_change_password=False,
		)

	def test_login_returns_access_token_and_admin_claims(self):
		response = self.client.post(
			'/api/auth/login/',
			{'admin_name': 'samuel', 'password': 'SecurePass1!'},
			format='json',
		)

		self.assertEqual(response.status_code, 200)
		self.assertIn('access_token', response.data)
		self.assertEqual(response.data['admin']['admin_name'], 'samuel')
		self.assertTrue(response.data['must_change_password'])

	def test_failed_logins_lock_account_after_threshold(self):
		for _ in range(5):
			response = self.client.post(
				'/api/auth/login/',
				{'admin_name': 'samuel', 'password': 'WrongPass1!'},
				format='json',
			)

		self.assertEqual(response.status_code, 401)
		self.admin.refresh_from_db()
		self.assertTrue(self.admin.is_locked)
		self.assertEqual(self.admin.failed_login_attempts, 5)

	def test_logout_blacklists_current_token(self):
		login_response = self.client.post(
			'/api/auth/login/',
			{'admin_name': 'samuel', 'password': 'SecurePass1!'},
			format='json',
		)
		token = login_response.data['access_token']

		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
		logout_response = self.client.post('/api/auth/logout/', {}, format='json')

		self.assertEqual(logout_response.status_code, 200)
		self.assertEqual(TokenBlacklist.objects.count(), 1)

		denied_response = self.client.get('/api/admin/')
		self.assertEqual(denied_response.status_code, 403)

	def test_teacher_cannot_access_level_three_admin_route(self):
		login_response = self.client.post(
			'/api/auth/login/',
			{'admin_name': 'teacher.jane', 'password': 'TeacherPass1!'},
			format='json',
		)
		token = login_response.data['access_token']

		self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {token}')
		response = self.client.get('/api/admin/')

		self.assertEqual(response.status_code, 403)
