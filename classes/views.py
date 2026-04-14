from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Class
from .serializers import ClassSerializer


class ClassViewSet(viewsets.ModelViewSet):
    serializer_class = ClassSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tenant_id', 'grade', 'section', 'academic_year', 'is_active', 'teacher']
    search_fields = ['class_name', 'subject']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = Class.objects.select_related('teacher').all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs
