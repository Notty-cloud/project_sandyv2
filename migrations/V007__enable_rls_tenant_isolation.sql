-- V007__enable_rls_tenant_isolation.sql
-- Row Level Security (RLS) for multi-tenant isolation.
-- All queries must set app.current_tenant_id before executing:
--   SET app.current_tenant_id = '<tenant-uuid>';

-- ─── ADMINS ──────────────────────────────────────────────────────────────────
ALTER TABLE admins ENABLE ROW LEVEL SECURITY;

CREATE POLICY admins_tenant_isolation ON admins
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ─── STUDENTS ────────────────────────────────────────────────────────────────
ALTER TABLE students ENABLE ROW LEVEL SECURITY;

CREATE POLICY students_tenant_isolation ON students
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ─── STUDENT EMBEDDINGS ──────────────────────────────────────────────────────
ALTER TABLE student_embeddings ENABLE ROW LEVEL SECURITY;

CREATE POLICY student_embeddings_tenant_isolation ON student_embeddings
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ─── CLASSES ─────────────────────────────────────────────────────────────────
ALTER TABLE classes ENABLE ROW LEVEL SECURITY;

CREATE POLICY classes_tenant_isolation ON classes
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ─── ENROLLMENTS ─────────────────────────────────────────────────────────────
ALTER TABLE enrollments ENABLE ROW LEVEL SECURITY;

CREATE POLICY enrollments_tenant_isolation ON enrollments
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ─── STUDENT ATTENDANCE ──────────────────────────────────────────────────────
ALTER TABLE student_attendance ENABLE ROW LEVEL SECURITY;

CREATE POLICY student_attendance_tenant_isolation ON student_attendance
    USING (tenant_id = current_setting('app.current_tenant_id')::UUID);

-- ─── SUPERUSER BYPASS ────────────────────────────────────────────────────────
-- Service-role / migration user bypasses RLS (default postgres behavior).
-- Application user must be a non-superuser role for RLS to apply.
-- Example setup (run once manually as superuser):
--
--   CREATE ROLE app_user NOINHERIT LOGIN PASSWORD '...';
--   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
--   GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user;
