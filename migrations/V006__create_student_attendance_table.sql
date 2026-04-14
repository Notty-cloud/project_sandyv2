-- V006__create_student_attendance_table.sql (SQLite)
CREATE TABLE student_attendance (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id           TEXT NOT NULL,
    student_id          TEXT NOT NULL REFERENCES students(id),
    class_id            INTEGER REFERENCES classes(id),
    date                TEXT NOT NULL,                             -- ISO format: YYYY-MM-DD
    checkin_time        TEXT,                                      -- ISO format: YYYY-MM-DD HH:MM:SS
    status              TEXT NOT NULL CHECK (status IN ('present', 'absent', 'late')),
    confidence          REAL,
    is_manual_override  INTEGER DEFAULT 0,                         -- 1=true, 0=false
    override_reason     TEXT,
    overridden_by       TEXT REFERENCES admins(id),
    location            TEXT,
    created_at          TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_attendance_student_date ON student_attendance(student_id, date);
CREATE INDEX idx_attendance_tenant_date ON student_attendance(tenant_id, date);
CREATE INDEX idx_attendance_class ON student_attendance(class_id);
