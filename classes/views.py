from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from admins.permissions import RoleLevelPermission
from .models import Class
from .serializers import ClassSerializer


class ClassViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
    serializer_class = ClassSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tenant_id', 'grade', 'section', 'academic_year', 'is_active', 'teacher']
    search_fields = ['class_name', 'subject']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            self.required_roles = ('admin',)
            self.minimum_authorization_level = 2
        return super().get_permissions()

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = Class.objects.select_related('teacher').all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs
