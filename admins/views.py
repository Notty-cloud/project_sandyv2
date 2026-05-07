import uuid
from datetime import datetime, timezone as dt_timezone

import jwt
from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import filters, status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from .models import Admin, AuthAuditLog, TokenBlacklist
from .permissions import RoleLevelPermission
from .serializers import AdminCreateSerializer, AdminSerializer, ChangePasswordSerializer, LoginSerializer


def get_client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def issue_access_token(admin):
    issued_at = timezone.now()
    expires_at = issued_at + settings.ACCESS_TOKEN_LIFETIME
    payload = {
        'admin_id': str(admin.id),
        'admin_name': admin.admin_name,
        'role': admin.role,
        'authorization_level': admin.authorization_level,
        'type': 'access',
        'jti': str(uuid.uuid4()),
        'iat': int(issued_at.timestamp()),
        'exp': int(expires_at.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256'), expires_at


def log_auth_event(event_type, request, admin=None, attempted_admin_name='', details=None):
    AuthAuditLog.objects.create(
        admin=admin,
        attempted_admin_name=attempted_admin_name,
        ip_address=get_client_ip(request),
        event_type=event_type,
        details=details or {},
    )


class LoginRateThrottle(SimpleRateThrottle):
    scope = 'login'

    def get_cache_key(self, request, view):
        return self.cache_format % {'scope': self.scope, 'ident': self.get_ident(request)}


class AuthLoginView(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [LoginRateThrottle]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        admin_name = serializer.validated_data['admin_name']
        password = serializer.validated_data['password']

        try:
            admin = Admin.objects.get(admin_name=admin_name)
        except Admin.DoesNotExist:
            log_auth_event('login_failure', request, attempted_admin_name=admin_name)
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        if admin.is_locked:
            log_auth_event('login_failure', request, admin=admin, attempted_admin_name=admin_name, details={'reason': 'locked'})
            return Response({'detail': 'Account is locked. Contact a level 3 admin to unlock it.'}, status=status.HTTP_423_LOCKED)

        if not admin.is_active or not check_password(password, admin.password_hash):
            admin.failed_login_attempts += 1
            if admin.failed_login_attempts >= settings.LOGIN_LOCKOUT_THRESHOLD:
                admin.is_locked = True
            admin.save(update_fields=['failed_login_attempts', 'is_locked', 'updated_at'])
            log_auth_event(
                'login_failure',
                request,
                admin=admin,
                attempted_admin_name=admin_name,
                details={'failed_login_attempts': admin.failed_login_attempts},
            )
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        admin.failed_login_attempts = 0
        admin.last_login_at = timezone.now()
        admin.save(update_fields=['failed_login_attempts', 'last_login_at', 'updated_at'])

        access_token, expires_at = issue_access_token(admin)
        log_auth_event('login_success', request, admin=admin, attempted_admin_name=admin_name)

        return Response(
            {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_at': expires_at.isoformat(),
                'must_change_password': admin.must_change_password,
                'admin': AdminSerializer(admin).data,
            },
            status=status.HTTP_200_OK,
        )


class AuthLogoutView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1

    def post(self, request):
        claims = request.auth or {}
        jti = claims.get('jti')
        exp = claims.get('exp')
        if not jti or not exp:
            return Response({'detail': 'Invalid token claims.'}, status=status.HTTP_400_BAD_REQUEST)

        expires_at = datetime.fromtimestamp(exp, tz=dt_timezone.utc)
        TokenBlacklist.objects.get_or_create(
            jti=jti,
            defaults={'admin': request.user, 'expires_at': expires_at},
        )
        log_auth_event('logout', request, admin=request.user, attempted_admin_name=request.user.admin_name)
        return Response({'detail': 'Logged out successfully.'}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        request.user.password_hash = make_password(serializer.validated_data['new_password'], hasher='bcrypt_sha256')
        request.user.must_change_password = False
        request.user.save(update_fields=['password_hash', 'must_change_password', 'updated_at'])
        log_auth_event('password_change', request, admin=request.user, attempted_admin_name=request.user.admin_name)
        return Response({'detail': 'Password updated successfully.'}, status=status.HTTP_200_OK)


class AdminManagementView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('admin',)
    minimum_authorization_level = 3

    def get(self, request):
        queryset = Admin.objects.all().order_by('admin_name')
        tenant_id = request.query_params.get('tenant_id')
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return Response(AdminSerializer(queryset, many=True).data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = AdminCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin = serializer.save()
        return Response(AdminSerializer(admin).data, status=status.HTTP_201_CREATED)


class AdminUnlockView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('admin',)
    minimum_authorization_level = 3

    def post(self, request, admin_id):
        try:
            admin = Admin.objects.get(id=admin_id)
        except Admin.DoesNotExist:
            return Response({'detail': 'Admin account not found.'}, status=status.HTTP_404_NOT_FOUND)

        admin.is_locked = False
        admin.failed_login_attempts = 0
        admin.save(update_fields=['is_locked', 'failed_login_attempts', 'updated_at'])
        log_auth_event(
            'account_unlocked',
            request,
            admin=request.user,
            attempted_admin_name=admin.admin_name,
            details={'unlocked_admin_id': str(admin.id)},
        )
        return Response(AdminSerializer(admin).data, status=status.HTTP_200_OK)


class AdminViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('admin',)
    minimum_authorization_level = 3
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tenant_id', 'role', 'is_active']
    search_fields = ['admin_name', 'email']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        queryset = Admin.objects.all()
        if tenant_id:
            queryset = queryset.filter(tenant_id=tenant_id)
        return queryset

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateSerializer
        return AdminSerializer
