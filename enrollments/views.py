from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from .models import Enrollment
from .serializers import EnrollmentSerializer


class EnrollmentViewSet(viewsets.ModelViewSet):
    serializer_class = EnrollmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tenant_id', 'student', 'academic_year', 'status', 'embedding_generated']
    search_fields = ['student__name', 'student__student_id']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = Enrollment.objects.select_related('student', 'enrolled_by').all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs
