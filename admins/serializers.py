from rest_framework import serializers
from .models import Admin


class AdminSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ['id', 'tenant_id', 'admin_name', 'email', 'role', 'authorization_level', 'is_active', 'created_at', 'updated_at']
        read_only_fields = ['id', 'created_at', 'updated_at']


class AdminCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Admin
        fields = ['id', 'tenant_id', 'admin_name', 'email', 'password_hash', 'role', 'authorization_level']
        read_only_fields = ['id']
        extra_kwargs = {'password_hash': {'write_only': True}}
