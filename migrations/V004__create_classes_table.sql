-- V004__create_classes_table.sql
CREATE TABLE classes (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       UUID NOT NULL,
    grade           VARCHAR(50) NOT NULL,
    section         VARCHAR(20) NOT NULL,
    class_name      VARCHAR(100),
    subject         VARCHAR(100),
    teacher_id      UUID REFERENCES admins(id),
    is_active       BOOLEAN DEFAULT true,
    academic_year   VARCHAR(20),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    UNIQUE(tenant_id, grade, section, academic_year)
);

CREATE INDEX idx_classes_tenant ON classes(tenant_id);
CREATE INDEX idx_classes_teacher ON classes(teacher_id);
