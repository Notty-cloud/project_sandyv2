import numpy as np
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from django_filters.rest_framework import DjangoFilterBackend
from admins.permissions import RoleLevelPermission
from admins.tenancy import TenantScopedMixin, request_tenant_id, scope_to_tenant
from .models import Student, StudentEmbedding
from .serializers import StudentSerializer, StudentDetailSerializer, StudentEmbeddingSerializer
from .backends import active_backend, extract_embedding
from .face import extract_all_embeddings
from .matching import best_match


def _check_enrolment_identity(request, student, face_data):
    """
    Refuse a photo that is not the student it is being filed under.

    Two ways an enrolment goes wrong:

      * the face does not match the photos already on this student — someone is
        adding a different person to an existing record;
      * the face matches a *different* student more strongly — the photo is
        being filed under the wrong name.

    Returns an error dict to send back, or None when the photo is acceptable.
    Pass ``override=true`` to bypass; a genuinely poor first photo has to be
    correctable. Overrides require authorisation level 2 (coordinator+).
    """
    from django.conf import settings

    threshold = getattr(settings, 'FACE_MATCHING_THRESHOLD', 0.65)
    embedding = face_data['embedding']
    backend = face_data['backend']

    override = str(request.data.get('override', '')).lower() in ('1', 'true', 'yes')
    if override:
        if getattr(request.user, 'authorization_level', 0) < 2:
            return {
                'image': 'Overriding the identity check requires authorisation level 2 or higher.',
                'code': 'override_forbidden',
            }
        return None

    tenant_scoped = StudentEmbedding.objects.filter(
        tenant_id=student.tenant_id, is_active=True, backend=backend,
    ).select_related('student')

    # Does this face match the photos already held for this student?
    own = tenant_scoped.filter(student=student)
    if own.exists():
        _, own_score = best_match(own, embedding)
        if own_score < threshold:
            return {
                'image': (
                    f'This face does not match the photos already enrolled for '
                    f'{student.name} (similarity {own_score:.2f}, needs {threshold:.2f}). '
                    f'Check you have the right student, or re-enrol with override if '
                    f'the existing photos are wrong.'
                ),
                'code': 'identity_mismatch',
                'confidence': round(own_score, 4),
            }
        return None

    # First photo for this student: make sure it is not someone already enrolled
    # elsewhere, which is how a face ends up filed under two names.
    others = tenant_scoped.exclude(student=student)
    if others.exists():
        other_embedding, other_score = best_match(others, embedding)
        if other_score >= threshold and other_embedding is not None:
            return {
                'image': (
                    f'This face is already enrolled as '
                    f'{other_embedding.student.name} ({other_embedding.student.student_id}) '
                    f'(similarity {other_score:.2f}). Enrolling it for {student.name} too '
                    f'would make attendance ambiguous. Use override if these really are '
                    f'different people.'
                ),
                'code': 'duplicate_face',
                'confidence': round(other_score, 4),
                'conflicting_student': {
                    'id': str(other_embedding.student.id),
                    'name': other_embedding.student.name,
                    'student_id': other_embedding.student.student_id,
                },
            }

    return None


class StudentViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
    queryset = Student.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['grade', 'section', 'is_active']
    search_fields = ['name', 'student_id']

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

        # ── Identity check ────────────────────────────────────────────────
        # A photo containing *a* face is not enough: without this, any face can
        # be attached to any student, and someone could enrol their own face
        # under a classmate's record and have it mark that classmate present.
        identity_error = _check_enrolment_identity(request, student, face_data)
        if identity_error:
            return Response(identity_error, status=status.HTTP_409_CONFLICT)

        # ── Save embedding ────────────────────────────────────────────────
        from admins.models import Admin
        try:
            # Scoped: an account from another tenant must not be recordable here.
            enrolled_by = scope_to_tenant(Admin.objects.all(), request).get(id=enrolled_by_id)
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
                backend=face_data['backend'],
                detector=face_data.get('detector', ''),
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
        url_path='import-csv',
        parser_classes=[MultiPartParser, FormParser],
    )
    def import_csv(self, request):
        """
        POST /api/v1/students/import-csv/
        Create students in bulk from a CSV roster.

        Form fields:
          file    (file)   — CSV with header: student_id,name,grade,section[,is_active]
          dry_run (bool)   — validate and report without writing anything

        Students are created in the caller's own tenant; the file cannot place
        them elsewhere. Bad rows are reported individually and skipped rather
        than failing the file, so a roster with three problems still imports the
        rest. Requires authorisation level 2 — bulk-creating student records is
        not a teacher-level action.
        """
        from django.db import transaction

        from .importer import ImportError_, parse_students_csv

        if getattr(request.user, 'authorization_level', 0) < 2:
            return Response(
                {'detail': 'Importing a roster requires authorisation level 2 or higher.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        upload = request.FILES.get('file')
        if not upload:
            return Response({'file': 'A CSV file is required.'}, status=status.HTTP_400_BAD_REQUEST)

        tenant_id = request_tenant_id(request)
        existing = Student.objects.filter(tenant_id=tenant_id).values_list('student_id', flat=True)

        try:
            rows, errors = parse_students_csv(upload.read(), existing_student_ids=existing)
        except ImportError_ as exc:
            return Response({'file': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        dry_run = str(request.data.get('dry_run', '')).lower() in ('1', 'true', 'yes')

        if dry_run:
            return Response({
                'dry_run': True,
                'would_create': len(rows),
                'skipped': len(errors),
                'errors': errors,
                'preview': rows[:10],
            }, status=status.HTTP_200_OK)

        # One transaction: a roster half-imported because row 400 failed is
        # harder to reason about than one that either landed or did not.
        with transaction.atomic():
            created = Student.objects.bulk_create([
                Student(
                    tenant_id=tenant_id,
                    student_id=row['student_id'],
                    name=row['name'],
                    grade=row['grade'],
                    section=row['section'],
                    is_active=row['is_active'],
                )
                for row in rows
            ])

        return Response({
            'dry_run': False,
            'created': len(created),
            'skipped': len(errors),
            'errors': errors,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(
        detail=False,
        methods=['post'],
        url_path='identify',
        parser_classes=[MultiPartParser, FormParser],
    )
    def identify(self, request):
        """
        Identify a student from a face photo.

        The tenant is taken from the authenticated account — a tenant_id in the
        request body is ignored, so a caller cannot match faces against another
        school's enrolled students.

        Form fields:
          image      (file)   — face photo
          threshold  (float)  — match threshold, default 0.65
        """
        tenant_id = request_tenant_id(request)
        image_file = request.FILES.get('image')

        try:
            threshold = float(request.data.get('threshold', 0.65))
            assert 0.0 < threshold <= 1.0
        except (ValueError, AssertionError):
            return Response({'threshold': 'Must be a number between 0.0 and 1.0.'}, status=status.HTTP_400_BAD_REQUEST)

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
            # Never compare across backends — different models, different spaces.
            backend=face_data['backend'],
        ).select_related('student')

        # Pushed into the database on PostgreSQL so the HNSW index is used.
        best_embedding, best_score = best_match(active_embeddings, query_embedding)

        if best_embedding is None:
            return Response({'match': None, 'message': 'No enrolled students found for this tenant.'}, status=status.HTTP_404_NOT_FOUND)

        if best_score >= threshold:
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

        The tenant is taken from the authenticated account; a tenant_id in the
        request body is ignored.

        Form fields:
          image      (file)   — photo containing one or more faces
          threshold  (float)  — match threshold, default 0.65
        """
        tenant_id = request_tenant_id(request)
        image_file = request.FILES.get('image')

        try:
            threshold = float(request.data.get('threshold', 0.65))
            assert 0.0 < threshold <= 1.0
        except (ValueError, AssertionError):
            return Response({'threshold': 'Must be a number between 0.0 and 1.0.'}, status=status.HTTP_400_BAD_REQUEST)

        if not image_file:
            return Response({'error': 'image is required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            faces = extract_all_embeddings(image_file)
        except ValueError as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Face processing failed: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # extract_all_embeddings is DeepFace-only (the ONNX pipeline returns a
        # single face), so group identification always matches deepface vectors.
        active_embeddings = StudentEmbedding.objects.filter(
            tenant_id=tenant_id, is_active=True, backend='deepface',
        ).select_related('student')

        results = []
        for face in faces:
            # One indexed nearest-neighbour query per detected face.
            best_emb, best_score = best_match(active_embeddings, face['embedding'])

            results.append({
                'face_index': face['face_index'],
                'facial_area': face.get('facial_area'),
                'quality_score': face['quality_score'],
                'match': StudentSerializer(best_emb.student).data if (best_score >= threshold and best_emb) else None,
                'confidence': round(best_score, 4),
            })

        return Response({'face_count': len(faces), 'results': results}, status=status.HTTP_200_OK)


class StudentEmbeddingViewSet(TenantScopedMixin, viewsets.ModelViewSet):
    permission_classes = [RoleLevelPermission]
    required_roles = ('teacher', 'admin')
    minimum_authorization_level = 1
    serializer_class = StudentEmbeddingSerializer
    queryset = StudentEmbedding.objects.all()
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['student', 'is_active']
