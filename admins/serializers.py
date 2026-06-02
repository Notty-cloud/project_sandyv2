import re

from django.contrib.auth.hashers import check_password, make_password
from rest_framework import serializers

from .models import Admin


def validate_password_strength(value):
    errors = []
    if len(value) < 8:
        errors.append('Password must be at least 8 characters long.')
    if not re.search(r'[A-Z]', value):
        errors.append('Password must contain at least one uppercase letter.')
    if not re.search(r'\d', value):
        errors.append('Password must contain at least one number.')
    if not re.search(r'[^A-Za-z0-9]', value):
        errors.append('Password must contain at least one special character.')
    if errors:
        raise serializers.ValidationError(errors)
    return value


class AdminSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, allow_blank=True, trim_whitespace=False)

    class Meta:
        model = Admin
        fields = [
            'id',
            'tenant_id',
            'admin_name',
            'email',
            'password',
            'role',
            'authorization_level',
            'is_active',
            'is_locked',
            'failed_login_attempts',
            'must_change_password',
            'last_login_at',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['id', 'failed_login_attempts', 'last_login_at', 'created_at', 'updated_at']

    def validate_password(self, value):
        if value:
            return validate_password_strength(value)
        return value

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        if password:
            validated_data['password_hash'] = make_password(password, hasher='bcrypt_sha256')
        return super().update(instance, validated_data)


class AdminCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = Admin
        fields = [
            'id',
            'tenant_id',
            'admin_name',
            'email',
            'password',
            'role',
            'authorization_level',
            'is_active',
            'must_change_password',
        ]
        read_only_fields = ['id']

    def validate_password(self, value):
        return validate_password_strength(value)

    def create(self, validated_data):
        password = validated_data.pop('password')
        validated_data['password_hash'] = make_password(password, hasher='bcrypt_sha256')
        return Admin.objects.create(**validated_data)


class LoginSerializer(serializers.Serializer):
    admin_name = serializers.CharField(max_length=255)
    password = serializers.CharField(trim_whitespace=False)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField(trim_whitespace=False)
    new_password = serializers.CharField(trim_whitespace=False)

    def validate_new_password(self, value):
        return validate_password_strength(value)

    def validate(self, attrs):
        admin = self.context['request'].user
        if not check_password(attrs['current_password'], admin.password_hash):
            raise serializers.ValidationError({'current_password': 'Current password is incorrect.'})
        if attrs['current_password'] == attrs['new_password']:
            raise serializers.ValidationError({'new_password': 'New password must be different from current password.'})
        return attrs
