from rest_framework import serializers
from .models import StudentAttendance


class AttendanceSerializer(serializers.ModelSerializer):
    student_name = serializers.CharField(source='student.name', read_only=True)
    class_name = serializers.CharField(source='class_ref.class_name', read_only=True)

    class Meta:
        model = StudentAttendance
        fields = ['id', 'tenant_id', 'student', 'student_name', 'class_ref', 'class_name', 'date', 'checkin_time', 'status', 'confidence', 'is_manual_override', 'override_reason', 'overridden_by', 'location', 'created_at']
        read_only_fields = ['id', 'created_at']


class AttendanceOverrideSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentAttendance
        fields = ['status', 'override_reason']

    def validate(self, data):
        if not data.get('override_reason'):
            raise serializers.ValidationError({'override_reason': 'Reason is required for a manual override.'})
        return data
