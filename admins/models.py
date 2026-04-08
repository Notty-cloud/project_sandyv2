import uuid
from django.db import models


class Admin(models.Model):
    ROLE_CHOICES = [
        ('teacher', 'Teacher'),
        ('admin', 'Admin'),
        ('principal', 'Principal'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    admin_name = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    password_hash = models.CharField(max_length=255)
    role = models.CharField(max_length=50, choices=ROLE_CHOICES)
    authorization_level = models.IntegerField(default=1)  # 1=teacher, 2=admin, 3=principal
    is_active = models.BooleanField(default=True)
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
