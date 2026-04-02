-- V005__create_enrollments_table.sql (SQLite)
CREATE TABLE enrollments (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id           TEXT NOT NULL,
    student_id          TEXT NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    enrollment_date     TEXT NOT NULL DEFAULT (date('now')),
    academic_year       TEXT NOT NULL,
    status              TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'enrolled', 'failed', 'expired')),
    embedding_generated INTEGER DEFAULT 0,                         -- 1=true, 0=false
    quality_score       REAL,
    enrolled_by         TEXT REFERENCES admins(id),
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE INDEX idx_enrollments_status ON enrollments(status);
CREATE INDEX idx_enrollments_tenant ON enrollments(tenant_id);
