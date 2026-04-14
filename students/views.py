import numpy as np
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from .models import Student, StudentEmbedding
from .serializers import StudentSerializer, StudentDetailSerializer, StudentEmbeddingSerializer
from .face import extract_embedding, cosine_similarity


class StudentViewSet(viewsets.ModelViewSet):
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['tenant_id', 'grade', 'section', 'is_active']
    search_fields = ['name', 'student_id']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = Student.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return StudentDetailSerializer
        return StudentSerializer

    @action(
        detail=True,
        methods=['post'],
        url_path='enroll',
        parser_classes=[MultiPartParser, FormParser],
    )
    def enroll(self, request, pk=None):
        """
        POST /api/v1/students/{id}/enroll/
        Accepts a face photo, generates an embedding, saves it, and marks
        the student as enrolled.

        Form fields:
          image         (file)   — required, must be a valid image
          academic_year (string) — required
          enrolled_by   (uuid)   — required, admin ID performing the enrolment
        """
        student = self.get_object()
        image_file = request.FILES.get('image')
        academic_year = request.data.get('academic_year')
        enrolled_by_id = request.data.get('enrolled_by')

        # ── Validation ────────────────────────────────────────────────────
        errors = {}
        if not image_file:
            errors['image'] = 'A face photo is required.'
        if not academic_year:
            errors['academic_year'] = 'Academic year is required.'
        if not enrolled_by_id:
            errors['enrolled_by'] = 'Admin ID is required.'
        if errors:
            return Response(errors, status=status.HTTP_400_BAD_REQUEST)

        # ── Face extraction (DeepFace Facenet512) ────────────────────────
        try:
            face_data = extract_embedding(image_file)
        except ValueError as e:
            return Response({'image': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'image': f'Face processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        embedding = face_data['embedding']
        quality_score = face_data['quality_score']

        # ── Save embedding ────────────────────────────────────────────────
        from admins.models import Admin
        try:
            enrolled_by = Admin.objects.get(id=enrolled_by_id)
        except Admin.DoesNotExist:
            return Response({'enrolled_by': 'Admin not found.'}, status=status.HTTP_400_BAD_REQUEST)

        # Enforce 5-photo limit
        active_count = StudentEmbedding.objects.filter(student=student, is_active=True).count()
        if active_count >= 5:
            return Response(
                {'image': 'Maximum of 5 enrollment photos reached. Remove an old one before adding more.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Get next version number
        last_version = StudentEmbedding.objects.filter(student=student).order_by('-version').first()
        next_version = (last_version.version + 1) if last_version else 1

        embedding_record = StudentEmbedding.objects.create(
            student=student,
            tenant_id=student.tenant_id,
            embedding=embedding,
            version=next_version,
            quality_score=quality_score,
            enrolled_by=enrolled_by,
            is_active=True,
        )

        # ── Update enrollment record ──────────────────────────────────────
        from enrollments.models import Enrollment
        enrollment, _ = Enrollment.objects.get_or_create(
            student=student,
            academic_year=academic_year,
            tenant_id=student.tenant_id,
            defaults={'enrolled_by': enrolled_by},
        )
        enrollment.status = 'enrolled'
        enrollment.embedding_generated = True
        enrollment.quality_score = quality_score
        enrollment.enrolled_by = enrolled_by
        enrollment.save()

        return Response({
            'message': f'{student.name} enrolled successfully.',
            'student': StudentSerializer(student).data,
            'embedding_version': embedding_record.version,
            'quality_score': quality_score,
            'enrollment_status': enrollment.status,
        }, status=status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        url_path='identify',
        parser_classes=[MultiPartParser, FormParser],
    )
    def identify(self, request):
        """
        Identify a student from a face photo.

        Form fields:
          image      (file)   — face photo
          tenant_id  (string) — required
          threshold  (float)  — match threshold, default 0.65
        """
        tenant_id = request.data.get('tenant_id')
        image_file = request.FILES.get('image')
        threshold = float(request.data.get('threshold', 0.65))

        if not tenant_id:
            return Response({'error': 'tenant_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not image_file:
            return Response({'error': 'image is required.'}, status=status.HTTP_400_BAD_REQUEST)

        # Extract embedding from photo
        try:
            face_data = extract_embedding(image_file)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Face processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        query_embedding = face_data['embedding']

        active_embeddings = StudentEmbedding.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        ).select_related('student')

        if not active_embeddings.exists():
            return Response({'match': None, 'message': 'No enrolled students found for this tenant.'})

        best_score = -1
        best_embedding = None

        for emb in active_embeddings:
            score = cosine_similarity(query_embedding, emb.embedding)
            if score > best_score:
                best_score = score
                best_embedding = emb

        if best_score >= threshold and best_embedding:
            return Response({
                'match': StudentSerializer(best_embedding.student).data,
                'confidence': round(best_score, 4),
                'embedding_version': best_embedding.version,
            })

        return Response({'match': None, 'confidence': round(best_score, 4), 'message': 'No match above threshold.'})


class StudentEmbeddingViewSet(viewsets.ModelViewSet):
    serializer_class = StudentEmbeddingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tenant_id', 'student', 'is_active']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = StudentEmbedding.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs
