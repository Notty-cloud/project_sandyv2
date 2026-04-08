from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Admin
from .serializers import AdminSerializer, AdminCreateSerializer


class AdminViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tenant_id', 'role', 'is_active']
    search_fields = ['admin_name', 'email']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = Admin.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'create':
            return AdminCreateSerializer
        return AdminSerializer
