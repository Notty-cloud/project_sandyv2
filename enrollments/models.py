from django.db import models
from admins.models import Admin
from students.models import Student


class Enrollment(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('enrolled', 'Enrolled'),
        ('failed', 'Failed'),
        ('expired', 'Expired'),
    ]

    tenant_id = models.UUIDField()
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    enrollment_date = models.DateField(auto_now_add=True)
    academic_year = models.CharField(max_length=20)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    embedding_generated = models.BooleanField(default=False)
    quality_score = models.FloatField(null=True, blank=True)
    enrolled_by = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL)
    notes = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'enrollments'
        indexes = [
            models.Index(fields=['student'], name='idx_enrollments_student'),
            models.Index(fields=['status'], name='idx_enrollments_status'),
            models.Index(fields=['tenant_id'], name='idx_enrollments_tenant'),
        ]

    def __str__(self):
        return f'{self.student} — {self.status} ({self.academic_year})'
