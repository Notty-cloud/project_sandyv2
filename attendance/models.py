from django.db import models
from admins.models import Admin
from students.models import Student
from classes.models import Class


class StudentAttendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    tenant_id = models.UUIDField()
    student = models.ForeignKey(Student, on_delete=models.PROTECT, related_name='attendance_records')
    class_ref = models.ForeignKey(Class, null=True, blank=True, on_delete=models.SET_NULL, related_name='attendance_records')
    date = models.DateField()
    checkin_time = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    confidence = models.FloatField(null=True, blank=True)
    is_manual_override = models.BooleanField(default=False)
    override_reason = models.TextField(null=True, blank=True)
    overridden_by = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL)
    location = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'student_attendance'
        indexes = [
            models.Index(fields=['student', 'date'], name='idx_attendance_student_date'),
            models.Index(fields=['tenant_id', 'date'], name='idx_attendance_tenant_date'),
            models.Index(fields=['class_ref'], name='idx_attendance_class'),
        ]

    def __str__(self):
        return f'{self.student} — {self.status} on {self.date}'
