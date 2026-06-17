import numpy as np
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from admins.permissions import RoleLevelPermission
from .models import Student, StudentEmbedding
from .serializers import StudentSerializer, StudentDetailSerializer, StudentEmbeddingSerializer
from .face import extract_embedding, extract_all_embeddings, cosine_similarity


class StudentViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
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
        elif image_file.size > 10 * 1024 * 1024:
            errors['image'] = 'File too large. Maximum size is 10 MB.'
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

        if quality_score < 0.1:
            return Response(
                {'image': 'Face detected but confidence too low. Use better lighting and face the camera directly.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Save embedding ────────────────────────────────────────────────
        from admins.models import Admin
        try:
            enrolled_by = Admin.objects.get(id=enrolled_by_id)
        except Admin.DoesNotExist:
            return Response({'enrolled_by': 'Admin not found.'}, status=status.HTTP_400_BAD_REQUEST)

        from django.db import transaction

        # Enforce 5-photo limit and create embedding atomically to avoid duplicate versions
        with transaction.atomic():
            student_locked = Student.objects.select_for_update().get(pk=student.pk)
            active_count = StudentEmbedding.objects.filter(student=student_locked, is_active=True).count()
            if active_count >= 5:
                return Response(
                    {'image': 'Maximum of 5 enrollment photos reached. Remove an old one before adding more.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            last_version = StudentEmbedding.objects.filter(student=student_locked).order_by('-version').first()
            next_version = (last_version.version + 1) if last_version else 1

            embedding_record = StudentEmbedding.objects.create(
                student=student_locked,
                tenant_id=student_locked.tenant_id,
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

        try:
            threshold = float(request.data.get('threshold', 0.65))
            assert 0.0 < threshold <= 1.0
        except (ValueError, AssertionError):
            return Response({'threshold': 'Must be a number between 0.0 and 1.0.'}, status=status.HTTP_400_BAD_REQUEST)

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

        if face_data['quality_score'] < 0.1:
            return Response(
                {'error': 'Face detected but confidence too low. Use better lighting and face the camera directly.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        active_embeddings = StudentEmbedding.objects.filter(
            tenant_id=tenant_id,
            is_active=True,
        ).select_related('student')

        if not active_embeddings.exists():
            return Response({'match': None, 'message': 'No enrolled students found for this tenant.'}, status=status.HTTP_404_NOT_FOUND)

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
            }, status=status.HTTP_200_OK)

        return Response({'match': None, 'confidence': round(best_score, 4), 'message': 'No match above threshold.'}, status=status.HTTP_404_NOT_FOUND)

    @action(
        detail=False,
        methods=['post'],
        url_path='identify-group',
        parser_classes=[MultiPartParser, FormParser],
    )
    def identify_group(self, request):
        """
        POST /api/v1/students/identify-group/
        Detect every face in a group photo and return the best DB match for each.

        Form fields:
          image      (file)   — photo containing one or more faces
          tenant_id  (string) — required
          threshold  (float)  — match threshold, default 0.65
        """
        tenant_id = request.data.get('tenant_id')
        image_file = request.FILES.get('image')

        try:
            threshold = float(request.data.get('threshold', 0.65))
            assert 0.0 < threshold <= 1.0
        except (ValueError, AssertionError):
            return Response({'threshold': 'Must be a number between 0.0 and 1.0.'}, status=status.HTTP_400_BAD_REQUEST)

        if not tenant_id:
            return Response({'error': 'tenant_id is required.'}, status=status.HTTP_400_BAD_REQUEST)
        if not image_file:
            return Response({'error': 'image is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            faces = extract_all_embeddings(image_file)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Face processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        active_embeddings = list(
            StudentEmbedding.objects.filter(tenant_id=tenant_id, is_active=True).select_related('student')
        )

        results = []
        for face in faces:
            best_score = -1.0
            best_emb = None
            for emb in active_embeddings:
                score = cosine_similarity(face['embedding'], emb.embedding)
                if score > best_score:
                    best_score = score
                    best_emb = emb

            results.append({
                'face_index': face['face_index'],
                'facial_area': face.get('facial_area'),
                'quality_score': face['quality_score'],
                'match': StudentSerializer(best_emb.student).data if (best_score >= threshold and best_emb) else None,
                'confidence': round(best_score, 4),
            })

        return Response({'face_count': len(faces), 'results': results}, status=status.HTTP_200_OK)


class StudentEmbeddingViewSet(viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
    serializer_class = StudentEmbeddingSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['tenant_id', 'student', 'is_active']

    def get_queryset(self):
        tenant_id = self.request.query_params.get('tenant_id')
        qs = StudentEmbedding.objects.all()
        if tenant_id:
            qs = qs.filter(tenant_id=tenant_id)
        return qs
