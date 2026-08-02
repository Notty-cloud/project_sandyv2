"""
Tests for the production transport-security settings.

SECURE_SSL_REDIRECT is the setting most able to break a deployment: the
platform health probe may arrive without X-Forwarded-Proto, and a 301 there
fails the deploy rather than securing anything. These assert the behaviour
directly rather than trusting the exemption pattern to be right.

The settings live behind `if not DEBUG`, which is evaluated at import, so each
test applies the individual values with override_settings instead of toggling
DEBUG.
"""
from django.test import TestCase, override_settings

PRODUCTION_TRANSPORT = dict(
	SECURE_SSL_REDIRECT=True,
	SECURE_REDIRECT_EXEMPT=[r'^health/$'],
	SECURE_HSTS_SECONDS=3600,
	SECURE_HSTS_INCLUDE_SUBDOMAINS=False,
	SECURE_HSTS_PRELOAD=False,
	SECURE_CONTENT_TYPE_NOSNIFF=True,
	X_FRAME_OPTIONS='DENY',
)


@override_settings(**PRODUCTION_TRANSPORT)
class TransportSecurityTests(TestCase):
	def test_health_check_is_not_redirected(self):
		"""The probe must get 200 over plain http, or deployments fail."""
		response = self.client.get('/health/')
		self.assertEqual(response.status_code, 200)
		self.assertEqual(response.json()['status'], 'ok')

	def test_other_routes_are_redirected_to_https(self):
		response = self.client.get('/api/students/')
		self.assertEqual(response.status_code, 301)
		self.assertTrue(response['Location'].startswith('https://'))

	def test_hsts_is_sent_over_https(self):
		response = self.client.get('/health/', secure=True)
		self.assertIn('Strict-Transport-Security', response)
		self.assertIn('max-age=3600', response['Strict-Transport-Security'])

	def test_hsts_does_not_claim_subdomains(self):
		"""The app sits on a shared *.up.railway.app host; asserting a policy
		for sibling subdomains would speak for hosts that are not ours."""
		response = self.client.get('/health/', secure=True)
		self.assertNotIn('includeSubDomains', response['Strict-Transport-Security'])
		self.assertNotIn('preload', response['Strict-Transport-Security'])

	def test_framing_is_refused(self):
		"""A framed login page is the standard clickjacking setup, and this app
		prompts for camera access."""
		response = self.client.get('/health/', secure=True)
		self.assertEqual(response['X-Frame-Options'], 'DENY')

	def test_content_type_sniffing_is_disabled(self):
		response = self.client.get('/health/', secure=True)
		self.assertEqual(response['X-Content-Type-Options'], 'nosniff')


class ApiRemainsUsableWithCsrfMiddlewareTests(TestCase):
	"""
	CsrfViewMiddleware is installed for the Django-rendered routes. DRF views
	are csrf_exempt, so the JWT API must keep working without a CSRF token —
	this fails loudly if that ever stops being true.
	"""

	def test_login_endpoint_accepts_a_post_without_a_csrf_token(self):
		response = self.client.post(
			'/api/auth/login/',
			{'admin_name': 'nobody', 'password': 'wrong'},
			content_type='application/json',
		)
		# Credentials are wrong, so 401 — but not 403, which is what a CSRF
		# rejection would look like.
		self.assertEqual(response.status_code, 401)
