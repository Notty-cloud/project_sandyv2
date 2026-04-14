-- S001__sample_data.sql
-- Sample data for local development and testing.
-- Run AFTER all migrations (V000–V007) have been applied.
-- All records share the same tenant_id for simplicity.

-- ─── SETUP ───────────────────────────────────────────────────────────────────
-- Set tenant context for RLS (required since V007)
SET app.current_tenant_id = '00000000-0000-0000-0000-000000000001';

-- Shared constants used across all inserts
DO $$ BEGIN
    RAISE NOTICE 'Seeding sample data for tenant: 00000000-0000-0000-0000-000000000001';
END $$;


-- ─── ADMINS ──────────────────────────────────────────────────────────────────
INSERT INTO admins (id, tenant_id, admin_name, email, password_hash, role, authorization_level)
VALUES
    (
        '11111111-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        'Maria Santos',
        'maria.santos@school.edu',
        '$2b$12$placehashprincipal000000000000000000000000000000000000',  -- bcrypt placeholder
        'principal',
        3
    ),
    (
        '11111111-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        'Jose Reyes',
        'jose.reyes@school.edu',
        '$2b$12$placehashteacher0000000000000000000000000000000000000',
        'teacher',
        1
    ),
    (
        '11111111-0000-0000-0000-000000000003',
        '00000000-0000-0000-0000-000000000001',
        'Ana Cruz',
        'ana.cruz@school.edu',
        '$2b$12$placehashteacher0000000000000000000000000000000000001',
        'teacher',
        1
    );


-- ─── STUDENTS ────────────────────────────────────────────────────────────────
INSERT INTO students (id, tenant_id, student_id, name, grade, section)
VALUES
    ('22222222-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000001', 'STU-001', 'Carlos Dela Cruz',  'Grade 10', 'A'),
    ('22222222-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'STU-002', 'Bianca Flores',     'Grade 10', 'A'),
    ('22222222-0000-0000-0000-000000000003', '00000000-0000-0000-0000-000000000001', 'STU-003', 'Ramon Villanueva',  'Grade 10', 'B'),
    ('22222222-0000-0000-0000-000000000004', '00000000-0000-0000-0000-000000000001', 'STU-004', 'Sofia Mendoza',     'Grade 11', 'A'),
    ('22222222-0000-0000-0000-000000000005', '00000000-0000-0000-0000-000000000001', 'STU-005', 'Luis Castillo',     'Grade 11', 'A');


-- ─── CLASSES ─────────────────────────────────────────────────────────────────
INSERT INTO classes (id, tenant_id, grade, section, class_name, subject, teacher_id, academic_year)
VALUES
    (1, '00000000-0000-0000-0000-000000000001', 'Grade 10', 'A', 'G10-A Mathematics', 'Mathematics', '11111111-0000-0000-0000-000000000002', '2025-2026'),
    (2, '00000000-0000-0000-0000-000000000001', 'Grade 10', 'B', 'G10-B Mathematics', 'Mathematics', '11111111-0000-0000-0000-000000000002', '2025-2026'),
    (3, '00000000-0000-0000-0000-000000000001', 'Grade 11', 'A', 'G11-A Science',     'Science',     '11111111-0000-0000-0000-000000000003', '2025-2026');


-- ─── ENROLLMENTS ─────────────────────────────────────────────────────────────
-- Statuses: pending | enrolled | failed | expired
INSERT INTO enrollments (tenant_id, student_id, academic_year, status, embedding_generated, enrolled_by)
VALUES
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001', '2025-2026', 'enrolled', TRUE,  '11111111-0000-0000-0000-000000000002'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000002', '2025-2026', 'enrolled', TRUE,  '11111111-0000-0000-0000-000000000002'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000003', '2025-2026', 'pending',  FALSE, '11111111-0000-0000-0000-000000000002'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000004', '2025-2026', 'enrolled', TRUE,  '11111111-0000-0000-0000-000000000003'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000005', '2025-2026', 'failed',   FALSE, '11111111-0000-0000-0000-000000000003');


-- ─── STUDENT EMBEDDINGS ──────────────────────────────────────────────────────
-- Placeholder 512-dim zero vectors — replace with real embeddings from your face pipeline.
-- Only inserted for students whose enrollment status = 'enrolled'.
INSERT INTO student_embeddings (student_id, tenant_id, embedding, version, quality_score, enrolled_by)
VALUES
    (
        '22222222-0000-0000-0000-000000000001',
        '00000000-0000-0000-0000-000000000001',
        array_fill(0.0, ARRAY[512])::VECTOR(512),
        1, 0.91,
        '11111111-0000-0000-0000-000000000002'
    ),
    (
        '22222222-0000-0000-0000-000000000002',
        '00000000-0000-0000-0000-000000000001',
        array_fill(0.0, ARRAY[512])::VECTOR(512),
        1, 0.87,
        '11111111-0000-0000-0000-000000000002'
    ),
    (
        '22222222-0000-0000-0000-000000000004',
        '00000000-0000-0000-0000-000000000001',
        array_fill(0.0, ARRAY[512])::VECTOR(512),
        1, 0.95,
        '11111111-0000-0000-0000-000000000003'
    );


-- ─── STUDENT ATTENDANCE ──────────────────────────────────────────────────────
-- Covers 3 days across multiple classes.
-- Includes one manual override to test that flow.
INSERT INTO student_attendance (tenant_id, student_id, class_id, date, checkin_time, status, confidence, location)
VALUES
    -- 2025-09-01
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001', 1, '2025-09-01', '2025-09-01 07:02:00+08', 'present', 0.97, 'Gate A - Cam 1'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000002', 1, '2025-09-01', '2025-09-01 07:15:00+08', 'late',    0.89, 'Gate A - Cam 1'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000003', 2, '2025-09-01', NULL,                       'absent',  NULL, NULL),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000004', 3, '2025-09-01', '2025-09-01 07:01:00+08', 'present', 0.95, 'Gate B - Cam 2'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000005', 3, '2025-09-01', '2025-09-01 07:05:00+08', 'present', 0.92, 'Gate B - Cam 2'),

    -- 2025-09-02
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001', 1, '2025-09-02', '2025-09-02 07:00:00+08', 'present', 0.98, 'Gate A - Cam 1'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000002', 1, '2025-09-02', '2025-09-02 07:03:00+08', 'present', 0.91, 'Gate A - Cam 1'),
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000004', 3, '2025-09-02', NULL,                       'absent',  NULL, NULL),

    -- 2025-09-03 (manual override example)
    ('00000000-0000-0000-0000-000000000001', '22222222-0000-0000-0000-000000000001', 1, '2025-09-03', '2025-09-03 07:04:00+08', 'present', 0.96, 'Gate A - Cam 1');

-- Manual override: camera missed Bianca on 2025-09-03, teacher corrected it
INSERT INTO student_attendance
    (tenant_id, student_id, class_id, date, checkin_time, status, confidence, is_manual_override, override_reason, overridden_by, location)
VALUES
    (
        '00000000-0000-0000-0000-000000000001',
        '22222222-0000-0000-0000-000000000002',
        1,
        '2025-09-03',
        '2025-09-03 07:10:00+08',
        'present',
        NULL,
        TRUE,
        'Student was present but camera angle was obstructed. Verified by teacher.',
        '11111111-0000-0000-0000-000000000002',
        'Gate A - Cam 1'
    );
