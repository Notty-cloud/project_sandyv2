-- V003__create_student_embeddings_table.sql (SQLite)
-- NOTE: SQLite has no pgvector support.
-- Embeddings are stored as JSON text: '[0.12, 0.95, ...]' (512 floats).
-- Cosine similarity search must be done in the application layer:
--   1. Load all active embeddings for the tenant from this table.
--   2. Parse the JSON array.
--   3. Compute cosine similarity against the captured face vector.
--   4. Return the student_id with the highest score above your threshold.

CREATE TABLE student_embeddings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    student_id      TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    tenant_id       TEXT NOT NULL,
    embedding       TEXT NOT NULL,                                 -- JSON array of 512 floats
    version         INTEGER NOT NULL DEFAULT 1,
    quality_score   REAL,
    enrolled_at     TEXT DEFAULT (datetime('now')),
    enrolled_by     TEXT REFERENCES admins(id),
    is_active       INTEGER DEFAULT 1,                             -- 1=true, 0=false

    UNIQUE(student_id, version)
);

CREATE INDEX idx_student_embeddings_student ON student_embeddings(student_id);
CREATE INDEX idx_student_embeddings_tenant ON student_embeddings(tenant_id);
