from django.db import models
from admins.models import Admin


class Class(models.Model):
    tenant_id = models.UUIDField()
    grade = models.CharField(max_length=50)
    section = models.CharField(max_length=20)
    class_name = models.CharField(max_length=100, null=True, blank=True)
    subject = models.CharField(max_length=100, null=True, blank=True)
    teacher = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL, related_name='classes')
    is_active = models.BooleanField(default=True)
    academic_year = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'classes'
        unique_together = ('tenant_id', 'grade', 'section', 'subject', 'academic_year')
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_classes_tenant'),
            models.Index(fields=['teacher'], name='idx_classes_teacher'),
        ]

    def __str__(self):
        return f'{self.class_name or self.grade} {self.section}'
