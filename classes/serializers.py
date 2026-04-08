from rest_framework import serializers
from .models import Class


class ClassSerializer(serializers.ModelSerializer):
    teacher_name = serializers.CharField(source='teacher.admin_name', read_only=True)

    class Meta:
        model = Class
        fields = ['id', 'tenant_id', 'grade', 'section', 'class_name', 'subject', 'teacher', 'teacher_name', 'is_active', 'academic_year', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']
