import jwt
from django.conf import settings
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed

from .models import Admin, TokenBlacklist


class AdminJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        auth = get_authorization_header(request).split()
        if not auth or auth[0].lower() != b'bearer':
            return None

        if len(auth) != 2:
            raise AuthenticationFailed('Invalid Authorization header.')

        token = auth[1].decode('utf-8')

        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        except jwt.ExpiredSignatureError as exc:
            raise AuthenticationFailed('Token has expired.') from exc
        except jwt.InvalidTokenError as exc:
            raise AuthenticationFailed('Invalid token.') from exc

        admin_id = payload.get('admin_id')
        jti = payload.get('jti')
        if not admin_id or not jti:
            raise AuthenticationFailed('Token is missing required claims.')

        if TokenBlacklist.objects.filter(jti=jti).exists():
            raise AuthenticationFailed('Token has been revoked.')

        try:
            admin = Admin.objects.get(id=admin_id, is_active=True)
        except Admin.DoesNotExist as exc:
            raise AuthenticationFailed('Admin account not found or inactive.') from exc

        if admin.is_locked:
            raise AuthenticationFailed('Admin account is locked.')

        request.admin = admin
        return admin, payload