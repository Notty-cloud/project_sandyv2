"""
Nearest-neighbour lookup for face embeddings.

On PostgreSQL the search is pushed into the database so the HNSW index on
StudentEmbedding.embedding is used — the index exists precisely so matching
does not get slower as more students enrol.

On SQLite the embedding column is a JSONField and no vector operators exist,
so the same query is answered by scanning in Python. That path is O(n) and is
for local development only; production runs PostgreSQL.
"""
from django.conf import settings

_USING_POSTGRES = settings.DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql'


def best_match(queryset, query_embedding):
    """
    Return ``(embedding, similarity)`` for the closest embedding in ``queryset``.

    ``similarity`` is cosine similarity in [-1, 1]; higher is more alike.
    Returns ``(None, -1.0)`` when the queryset is empty.

    ``queryset`` must already be scoped to the caller's tenant — this function
    applies no filtering of its own.
    """
    if _USING_POSTGRES:
        from pgvector.django import CosineDistance

        embedding = (
            queryset
            .annotate(distance=CosineDistance('embedding', query_embedding))
            .order_by('distance')
            .first()
        )
        if embedding is None:
            return None, -1.0
        # pgvector returns cosine *distance*; similarity is its complement.
        return embedding, 1.0 - float(embedding.distance)

    from .face import cosine_similarity

    best, best_score = None, -1.0
    for embedding in queryset:
        score = cosine_similarity(query_embedding, embedding.embedding)
        if score > best_score:
            best, best_score = embedding, score
    return best, best_score
