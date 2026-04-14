import uuid
from django.db import models
from admins.models import Admin


class Student(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    tenant_id = models.UUIDField()
    student_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=255)
    grade = models.CharField(max_length=50)
    section = models.CharField(max_length=20)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'students'
        indexes = [
            models.Index(fields=['tenant_id'], name='idx_students_tenant'),
            models.Index(fields=['grade', 'section'], name='idx_students_grade_section'),
        ]

    def __str__(self):
        return f'{self.name} ({self.student_id})'


class StudentEmbedding(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='embeddings')
    tenant_id = models.UUIDField()
    embedding = models.JSONField()                  # list of 512 floats
    version = models.IntegerField(default=1)
    quality_score = models.FloatField(null=True, blank=True)
    enrolled_at = models.DateTimeField(auto_now_add=True)
    enrolled_by = models.ForeignKey(Admin, null=True, blank=True, on_delete=models.SET_NULL)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'student_embeddings'
        unique_together = ('student', 'version')
        indexes = [
            models.Index(fields=['student'], name='idx_student_embeddings_student'),
            models.Index(fields=['tenant_id'], name='idx_student_embeddings_tenant'),
        ]

    def __str__(self):
        return f'Embedding v{self.version} for {self.student}'
