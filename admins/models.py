import uuid
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Admin(models.Model):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    admin_name = models.CharField(max_length=255, unique=True)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    authorization_level = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1), MaxValueValidator(3)],
    )
    is_active = models.BooleanField(default=True)
    is_locked = models.BooleanField(default=False)
    failed_login_attempts = models.PositiveSmallIntegerField(default=0)
    must_change_password = models.BooleanField(default=True)
    last_login_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'admins'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_admins_tenant'),
            models.Index(fields=['email'], name='idx_admins_email'),
        ]

    def __str__(self):
        return f'{self.admin_name} ({self.role})'

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class AuthAuditLog(models.Model):
    EVENT_CHOICES = [
        ('login_success', 'Login Success'),
        ('login_failure', 'Login Failure'),
        ('logout', 'Logout'),
        ('password_change', 'Password Change'),
        ('account_unlocked', 'Account Unlocked'),
    ]

    admin = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL)
    attempted_admin_name = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    event_type = models.CharField(max_length=50, choices=EVENT_CHOICES)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'auth_audit_logs'
        indexes = [
            models.Index(fields=['attempted_admin_name'], name='idx_auth_audit_name'),
            models.Index(fields=['event_type', 'created_at'], name='idx_auth_audit_event'),
        ]


class TokenBlacklist(models.Model):
    admin = models.ForeignKey(Admin, on_delete=models.CASCADE, related_name='revoked_tokens')
    jti = models.CharField(max_length=255, unique=True)
    expires_at = models.DateTimeField()
    blacklisted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'token_blacklist'
        indexes = [
            models.Index(fields=['expires_at'], name='idx_token_blacklist_exp'),
        ]
