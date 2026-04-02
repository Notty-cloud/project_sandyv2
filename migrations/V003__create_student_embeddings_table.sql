-- V003__create_student_embeddings_table.sql
CREATE TABLE student_embeddings (
    id                  BIGSERIAL PRIMARY KEY,
    student_id          UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    tenant_id           UUID NOT NULL,

    embedding           VECTOR(512) NOT NULL,
    version             INTEGER NOT NULL DEFAULT 1,
    quality_score       FLOAT,
    enrolled_at         TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    enrolled_by         UUID REFERENCES admins(id),
    is_active           BOOLEAN DEFAULT true,

    UNIQUE(student_id, version)
);

-- HNSW index for fast cosine similarity search
-- NOTE: This index is global across all tenants.
-- Always filter by tenant_id in application queries before performing vector search.
CREATE INDEX idx_student_embeddings_hnsw
    ON student_embeddings USING hnsw (embedding vector_cosine_ops);

CREATE INDEX idx_student_embeddings_student ON student_embeddings(student_id);
CREATE INDEX idx_student_embeddings_tenant ON student_embeddings(tenant_id);
