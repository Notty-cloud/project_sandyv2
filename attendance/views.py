from datetime import date as date_type
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import StudentAttendance
from .serializers import AttendanceSerializer, AttendanceOverrideSerializer


class AttendanceViewSet(viewsets.ModelViewSet):
    serializer_class = AttendanceSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['tenant_id', 'student', 'class_ref', 'date', 'status', 'is_manual_override']
    ordering_fields = ['date', 'created_at']
    ordering = ['-date']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = StudentAttendance.objects.select_related('student', 'class_ref', 'overridden_by').all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    @action(detail=True, methods=['patch'], url_path='override')
    def override(self, request, pk=None):
        """
        PATCH /attendance/{id}/override/
        Manually override a student's attendance status.
        """
        record = self.get_object()
        serializer = AttendanceOverrideSerializer(record, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
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

        Form fields:
          image       (file)   — face photo from camera
          tenant_id   (string) — required
          class_id    (int)    — required
          date        (string) — YYYY-MM-DD, defaults to today
          threshold   (float)  — match confidence threshold, default 0.65
          location    (string) — camera/location label, optional
        """
        from students.models import StudentEmbedding
        from students.face import extract_embedding, cosine_similarity
        from django.utils import timezone

        tenant_id = request.data.get('tenant_id')
        class_id = request.data.get('class_id')
        image_file = request.FILES.get('image')
        threshold = float(request.data.get('threshold', 0.65))
        location = request.data.get('location', '')
        attendance_date = request.data.get('date') or date_type.today().isoformat()

        # ── Validation ────────────────────────────────────────────────────
        errors = {}
        if not tenant_id: errors['tenant_id'] = 'Required.'
        if not class_id:  errors['class_id'] = 'Required.'
        if not image_file: errors['image'] = 'Required.'
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

        # ── Find best matching student ────────────────────────────────────
        active_embeddings = StudentEmbedding.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        ).select_related('student')

        if not active_embeddings.exists():
            return Response({'error': 'No enrolled students found.', 'match': None},
                            status=status.HTTP_404_NOT_FOUND)

        best_score = -1
        best_emb = None
        for emb in active_embeddings:
            score = cosine_similarity(query_embedding, emb.embedding)
            if score > best_score:
                best_score = score
                best_emb = emb

        if best_score < threshold or best_emb is None:
            return Response({
                'match': None,
                'confidence': round(best_score, 4),
                'message': f'No match above threshold ({threshold}). Confidence: {round(best_score * 100, 1)}%',
            })

        student = best_emb.student

        # ── Create or update attendance record ────────────────────────────
        from classes.models import Class
        try:
            class_obj = Class.objects.get(id=class_id, tenant_id=tenant_id)
        except Class.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=status.HTTP_404_NOT_FOUND)

        # Determine status: late if past 7:10 AM
        now = timezone.localtime(timezone.now())
        cutoff_hour, cutoff_minute = 7, 10
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
