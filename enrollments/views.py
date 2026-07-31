from rest_framework import viewsets, filters, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from admins.permissions import RoleLevelPermission
from admins.tenancy import request_tenant_id, scope_to_tenant
from .models import Enrollment
from .serializers import EnrollmentSerializer


class EnrollmentViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
    serializer_class = EnrollmentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['student', 'academic_year', 'status', 'embedding_generated']
    search_fields = ['student__name', 'student__student_id']

    def get_permissions(self):
        if self.action in ('create', 'update', 'partial_update', 'destroy'):
            self.required_roles = ('admin',)
            self.minimum_authorization_level = 2
        return super().get_permissions()

    def get_queryset(self):
        user = self.request.user
        qs = scope_to_tenant(
            Enrollment.objects.select_related('student', 'enrolled_by').all(),
            self.request,
        )

        # Teachers only see enrollments for students in their assigned classes
        if user.role == 'teacher':
            from classes.models import Class
            from django.db.models import Q
            teacher_classes = Class.objects.filter(teacher=user).values('grade', 'section')
            q = Q()
            for cls in teacher_classes:
                q |= Q(student__grade=cls['grade'], student__section=cls['section'])
            qs = qs.filter(q) if q else qs.none()

        return qs

    def perform_create(self, serializer):
        serializer.save(
            enrolled_by=self.request.user,
            tenant_id=request_tenant_id(self.request),
        )


class EnrollmentCreateView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('admin',)
    minimum_authorization_level = 2

    def post(self, request):
        serializer = EnrollmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        enrollment = serializer.save(
            enrolled_by=request.user,
            tenant_id=request_tenant_id(request),
        )
        return Response(EnrollmentSerializer(enrollment).data, status=status.HTTP_201_CREATED)
