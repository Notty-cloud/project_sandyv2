-- V004__create_classes_table.sql (SQLite)
CREATE TABLE classes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tenant_id       TEXT NOT NULL,
    grade           TEXT NOT NULL,
    section         TEXT NOT NULL,
    class_name      TEXT,
    subject         TEXT,
    teacher_id      TEXT REFERENCES admins(id),
    is_active       INTEGER DEFAULT 1,                             -- 1=true, 0=false
    academic_year   TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),

    UNIQUE(tenant_id, grade, section, academic_year)
);

CREATE INDEX idx_classes_tenant ON classes(tenant_id);
CREATE INDEX idx_classes_teacher ON classes(teacher_id);
