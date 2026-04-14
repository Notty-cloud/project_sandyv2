from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from admins.permissions import RoleLevelPermission
from .models import Enrollment
from .serializers import EnrollmentSerializer


class EnrollmentViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('admin',)
    minimum_authorization_level = 2
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

    def perform_create(self, serializer):
        serializer.save(enrolled_by=self.request.user)


class EnrollmentCreateView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('admin',)
    minimum_authorization_level = 2

    def post(self, request):
        serializer = EnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save(enrolled_by=request.user)
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)
