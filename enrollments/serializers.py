from rest_framework import serializers
from .models import Enrollment


class EnrollmentSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)

    class Meta:
        model = Enrollment
        fields = ['id', 'tenant_id', 'student', 'student_name', 'enrollment_date', 'academic_year', 'status', 'embedding_generated', 'quality_score', 'enrolled_by', 'notes', 'created_at', 'updated_at']
        read_only_fields = ['id', 'enrollment_date', 'created_at', 'updated_at']
