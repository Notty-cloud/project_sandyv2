"""
ai_engine/services/embedding_service.py

Django ORM integration for the face embedding pipeline.

Orchestrates the full flow:
    1. Run face_pipeline.extract_embedding() on an image
    2. Deactivate any prior active embeddings for the student
    3. Persist a new StudentEmbedding record (version auto-incremented)
    4. Mark the student's latest Enrollment as embedding_generated=True
       and status='enrolled'
"""

import logging
from uuid import UUID

from django.db import transaction

from ai_engine.face_pipeline import extract_embedding

logger = logging.getLogger(__name__)


class EmbeddingService:
    def generate_for_student(
        self,
        student_id: UUID,
        tenant_id: UUID,
        image_input,
        enrolled_by_id: UUID = None,
    ) -> dict:
        """
        Run the full face pipeline and persist the result for a student.

        Args:
            student_id    (UUID): Primary key of the Student record.
            tenant_id     (UUID): Tenant the student belongs to (RLS scope).
            image_input:         Accepted by face_pipeline — str path, bytes,
                                 PIL.Image, Django UploadedFile, or np.ndarray.
            enrolled_by_id (UUID, optional): Admin who triggered enrollment.

        Returns:
            dict:
                embedding     (list[float]) — 512 floats, L2-normalized
                quality_score (float)       — detection confidence 0.0–1.0
                version       (int)         — embedding version number stored

        Raises:
            Student.DoesNotExist:  student_id not found for this tenant
            FaceNotDetectedError:  no face in the provided image
            LowQualityFaceError:   detection confidence below threshold
        """
        from admins.models import Admin
        from enrollments.models import Enrollment
        from students.models import Student, StudentEmbedding

        # ── Run the AI pipeline (outside the DB transaction) ──────────────────
        result = extract_embedding(image_input)
        embedding_list = result['embedding'].tolist()
        quality_score = result['quality_score']

        with transaction.atomic():
            # Fetch the student, scoped to the tenant for safety
            student = Student.objects.get(id=student_id, tenant_id=tenant_id)

            # Determine the next version number
            last_embedding = (
                StudentEmbedding.objects
                .filter(student=student)
                .order_by('-version')
                .first()
            )
            next_version = (last_embedding.version + 1) if last_embedding else 1

            # Deactivate all previous active embeddings for this student
            StudentEmbedding.objects.filter(
                student=student,
                is_active=True,
            ).update(is_active=False)

            # Resolve the enrolled_by Admin (nullable foreign key)
            enrolled_by = None
            if enrolled_by_id:
                try:
                    enrolled_by = Admin.objects.get(id=enrolled_by_id)
                except Admin.DoesNotExist:
                    logger.warning(
                        'enrolled_by Admin %s not found — storing embedding without admin reference.',
                        enrolled_by_id,
                    )

            # Persist new embedding record
            StudentEmbedding.objects.create(
                student=student,
                tenant_id=tenant_id,
                embedding=embedding_list,
                version=next_version,
                quality_score=quality_score,
                enrolled_by=enrolled_by,
                is_active=True,
            )

            # Mark the student's most recent enrollment as complete
            updated = (
                Enrollment.objects
                .filter(student=student, tenant_id=tenant_id)
                .order_by('-created_at')
                .update(
                    embedding_generated=True,
                    status='enrolled',
                    quality_score=quality_score,
                )
            )

            if updated == 0:
                logger.warning(
                    'No Enrollment record found for student %s — embedding saved but '
                    'enrollment status was not updated.',
                    student_id,
                )

        logger.info(
            'Embedding v%d generated for student %s (tenant=%s, quality=%.4f)',
            next_version,
            student_id,
            tenant_id,
            quality_score,
        )

        return {
            'embedding': embedding_list,
            'quality_score': quality_score,
            'version': next_version,
        }
