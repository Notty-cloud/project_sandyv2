-- V002__create_students_table.sql
CREATE TABLE students (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id       UUID NOT NULL,
    student_id      VARCHAR(50) UNIQUE NOT NULL,
    name            VARCHAR(255) NOT NULL,
    grade           VARCHAR(50) NOT NULL,
    section         VARCHAR(20) NOT NULL,
    is_active       BOOLEAN DEFAULT true,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_students_tenant ON students(tenant_id);
CREATE INDEX idx_students_grade_section ON students(grade, section);
