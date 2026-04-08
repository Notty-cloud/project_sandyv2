from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView


class AdminTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        try:
            from admins.models import Admin
            admin = Admin.objects.get(email=user.email)
            token['tenant_id'] = str(admin.tenant_id)
            token['role'] = admin.role
            token['admin_id'] = str(admin.id)
            token['admin_name'] = admin.admin_name
        except Admin.DoesNotExist:
            token['tenant_id'] = None
            token['role'] = 'teacher'
            token['admin_id'] = None
            token['admin_name'] = user.username
        return token


class AdminTokenObtainPairView(TokenObtainPairView):
    serializer_class = AdminTokenObtainPairSerializer
