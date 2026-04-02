-- V006__create_student_attendance_table.sql
CREATE TABLE student_attendance (
    id                  BIGSERIAL PRIMARY KEY,
    tenant_id           UUID NOT NULL,
    student_id          UUID NOT NULL REFERENCES students(id),
    class_id            BIGINT REFERENCES classes(id),
    date                DATE NOT NULL,
    checkin_time        TIMESTAMP WITH TIME ZONE,
    status              VARCHAR(20) NOT NULL CHECK (status IN ('present', 'absent', 'late')),
    confidence          FLOAT,
    is_manual_override  BOOLEAN DEFAULT FALSE,
    override_reason     TEXT,
    overridden_by       UUID REFERENCES admins(id),
    location            VARCHAR(100),                   -- building or camera location
    created_at          TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_attendance_student_date ON student_attendance(student_id, date);
CREATE INDEX idx_attendance_tenant_date ON student_attendance(tenant_id, date);
CREATE INDEX idx_attendance_class ON student_attendance(class_id);
