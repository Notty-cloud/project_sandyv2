from datetime import date as date_type
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from admins.permissions import RoleLevelPermission
from admins.tenancy import request_tenant_id, scope_to_tenant
from .models import StudentAttendance
from .serializers import AttendanceSerializer, AttendanceOverrideSerializer


def attendance_queryset_for_request(request):
    queryset = scope_to_tenant(
        StudentAttendance.objects.select_related('student', 'class_ref', 'overridden_by').all(),
        request,
    )

    if getattr(request.user, 'role', None) == 'teacher':
        queryset = queryset.filter(class_ref__teacher=request.user)

    return queryset


class AttendanceViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['student', 'class_ref', 'date', 'status', 'is_manual_override']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']

    def get_queryset(self):
        return attendance_queryset_for_request(self.request)

    def perform_create(self, serializer):
        serializer.save(tenant_id=request_tenant_id(self.request))

    @action(detail=True, methods=['patch'], url_path='override')
    def override(self, request, pk=None):
        """
        PATCH /attendance/{id}/override/
        Manually override a student's attendance status.
        """
        record = self.get_object()
        serializer = AttendanceOverrideSerializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(overridden_by=request.user, is_manual_override=True)
        return Response(AttendanceSerializer(record).data, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        url_path='mark-by-face',
        parser_classes=[MultiPartParser, FormParser],
    )
    def mark_by_face(self, request):
        """
        POST /api/v1/attendance/mark-by-face/

        Identify a student from a face photo and mark their attendance.

        The tenant comes from the authenticated account; a tenant_id in the
        request body is ignored, so attendance cannot be marked against another
        school's students or classes.

        Form fields:
          image       (file)   — face photo from camera
          class_id    (int)    — required
          date        (string) — YYYY-MM-DD, defaults to today
          threshold   (float)  — match confidence threshold, default 0.65
          location    (string) — camera/location label, optional
        """
        from students.models import StudentEmbedding
        from students.backends import extract_embedding
        from students.matching import best_match
        from django.utils import timezone

        tenant_id = request_tenant_id(request)
        class_id = request.data.get('class_id')
        image_file = request.FILES.get('image')
        location = request.data.get('location', '')

        try:
            threshold = float(request.data.get('threshold', 0.65))
            assert 0.0 < threshold <= 1.0
        except (ValueError, AssertionError):
            return Response({'threshold': 'Must be a number between 0.0 and 1.0.'}, status=status.HTTP_400_BAD_REQUEST)

        from datetime import datetime as dt
        raw_date = request.data.get('date')
        try:
            attendance_date = dt.strptime(raw_date, '%Y-%m-%d').date() if raw_date else date_type.today()
        except ValueError:
            return Response({'date': 'Invalid date format. Use YYYY-MM-DD.'}, status=status.HTTP_400_BAD_REQUEST)

        # ── Validation ────────────────────────────────────────────────────
        errors = {}
        if not class_id:  errors['class_id'] = 'Required.'
        if not image_file:
            errors['image'] = 'Required.'
        elif image_file.size > 10 * 1024 * 1024:
            errors['image'] = 'File too large. Maximum size is 10 MB.'
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ── Extract face embedding ────────────────────────────────────────
        try:
            face_data = extract_embedding(image_file)
        except ValueError as e:
            return Response({'error': str(e), 'match': None}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Face processing failed: {str(e)}', 'match': None},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        query_embedding = face_data['embedding']
        face_confidence = face_data['quality_score']

        # ── Find best matching student (HNSW-indexed on PostgreSQL) ──────
        best_emb, best_score = best_match(
            StudentEmbedding.objects
            .filter(
                tenant_id=tenant_id,
                is_active=True,
                # Cross-backend comparison is meaningless — see students/backends.py
                backend=face_data['backend'],
            )
            .select_related('student'),
            query_embedding,
        )

        if best_emb is None:
            return Response({'error': 'No enrolled students found.', 'match': None},
                            status=status.HTTP_404_NOT_FOUND)

        if best_score < threshold:
            return Response({
                'match': None,
                'confidence': round(best_score, 4),
                'message': f'No match above threshold ({threshold}). Confidence: {round(best_score * 100, 1)}%',
            }, status=status.HTTP_404_NOT_FOUND)

        student = best_emb.student

        # ── Create or update attendance record ────────────────────────────
        from classes.models import Class
        try:
            class_obj = Class.objects.get(id=class_id, tenant_id=tenant_id)
        except Class.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Determine status: late if past configured cutoff time
        from django.conf import settings as django_settings
        now = timezone.localtime(timezone.now())
        cutoff_hour = getattr(django_settings, 'ATTENDANCE_CUTOFF_HOUR', 7)
        cutoff_minute = getattr(django_settings, 'ATTENDANCE_CUTOFF_MINUTE', 10)
        attendance_status = 'late' if (now.hour > cutoff_hour or
            (now.hour == cutoff_hour and now.minute >= cutoff_minute)) else 'present'

        record, created = StudentAttendance.objects.get_or_create(
            tenant_id=tenant_id,
            student=student,
            class_ref=class_obj,
            date=attendance_date,
            defaults={
                'checkin_time': timezone.now(),
                'status': attendance_status,
                'confidence': round(best_score, 4),
                'location': location,
            },
        )

        if not created:
            return Response({
                'match': {'id': str(student.id), 'name': student.name, 'student_id': student.student_id},
                'confidence': round(best_score, 4),
                'message': f'{student.name} already marked {record.status} for this class today.',
                'already_marked': True,
            })

        return Response({
            'match': {'id': str(student.id), 'name': student.name, 'student_id': student.student_id},
            'confidence': round(best_score, 4),
            'face_confidence': face_confidence,
            'status': attendance_status,
            'message': f'{student.name} marked {attendance_status}.',
            'already_marked': False,
        }, status=status.HTTP_201_CREATED)


class AttendanceListView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1

    def get(self, request):
        queryset = attendance_queryset_for_request(request).order_by('-date', '-created_at')
        serializer = AttendanceSerializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AttendanceOverrideView(APIView):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 2

    def post(self, request):
        attendance_id = request.data.get('attendance_id')
        if not attendance_id:
            return Response({'attendance_id': 'This field is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            record = attendance_queryset_for_request(request).get(id=attendance_id)
        except StudentAttendance.DoesNotExist:
            return Response({'detail': 'Attendance record not found.'}, status=status.HTTP_404_NOT_FOUND)

        serializer = AttendanceOverrideSerializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save(overridden_by=request.user, is_manual_override=True)
        return Response(AttendanceSerializer(record).data, status=status.HTTP_200_OK)
