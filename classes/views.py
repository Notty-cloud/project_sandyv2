from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from admins.permissions import RoleLevelPermission
from admins.tenancy import TenantScopedMixin
from .models import Class
from .serializers import ClassSerializer


class ClassViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
    serializer_class = ClassSerializer
    queryset = Class.objects.select_related('teacher').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['grade', 'section', 'academic_year', 'is_active', 'teacher']
    search_fields = ['class_name', 'subject']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            self.required_roles = ('admin',)
            self.minimum_authorization_level = 2
        return super().get_permissions()
