-- V005__create_enrollments_table.sql
CREATE TABLE enrollments (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL,
    student_id          UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,

    enrollment_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    academic_year       VARCHAR(20) NOT NULL,
    status              VARCHAR(50) DEFAULT 'pending' CHECK (status IN ('pending', 'enrolled', 'failed', 'expired')),
    embedding_generated BOOLEAN DEFAULT FALSE,
    quality_score       FLOAT,
    enrolled_by         UUID REFERENCES admins(id),
    notes               TEXT,

    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_enrollments_student ON enrollments(student_id);
CREATE INDEX idx_enrollments_status ON enrollments(status);
CREATE INDEX idx_enrollments_tenant ON enrollments(tenant_id);
