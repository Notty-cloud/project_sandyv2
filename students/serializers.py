from rest_framework import serializers
from .models import Student, StudentEmbedding


class StudentEmbeddingSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentEmbedding
        fields = ['id', 'student', 'tenant_id', 'embedding', 'version', 'quality_score', 'enrolled_at', 'enrolled_by', 'is_active']
        read_only_fields = ['id', 'enrolled_at']

    def validate_embedding(self, value):
        if not isinstance(value, list) or len(value) != 512:
            raise serializers.ValidationError('Embedding must be a list of exactly 512 floats.')
        if not all(isinstance(v, (int, float)) for v in value):
            raise serializers.ValidationError('All embedding values must be numeric.')
        return value


class StudentSerializer(serializers.ModelSerializer):
    photo_count = serializers.SerializerMethodField()

    def get_photo_count(self, obj):
        # Prefer the annotation from StudentViewSet.get_queryset. Counting here
        # costs one query per student — 201 queries for a 200-student roster,
        # which over a network round-trip is the difference between a page that
        # loads and one that hangs. The fallback keeps single-object callers
        # (and anything serialising an unannotated queryset) correct.
        annotated = getattr(obj, 'active_photo_count', None)
        if annotated is not None:
            return annotated
        return obj.embeddings.filter(is_active=True).count()

    class Meta:
        model = Student
        fields = ['id', 'tenant_id', 'student_id', 'name', 'grade', 'section', 'is_active', 'created_at', 'updated_at', 'photo_count']
        read_only_fields = ['id', 'created_at', 'updated_at', 'photo_count']


class StudentDetailSerializer(serializers.ModelSerializer):
    embeddings = StudentEmbeddingSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['id', 'tenant_id', 'student_id', 'name', 'grade', 'section', 'is_active', 'created_at', 'updated_at', 'embeddings']
        read_only_fields = ['id', 'created_at', 'updated_at']
