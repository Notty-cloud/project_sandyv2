-- S002__teacher_dashboard_queries.sql
-- Reference queries for the Teacher Dashboard API layer.
-- All queries assume RLS is active — set tenant context before running:
--   SET app.current_tenant_id = '<tenant-uuid>';
--
-- Replace :teacher_id, :class_id, :date, :academic_year with bound parameters.


-- ─── 1. TEACHER: GET MY CLASSES ───────────────────────────────────────────────
-- Used on dashboard load — shows all classes assigned to the logged-in teacher.
SELECT
    c.id            AS class_id,
    c.class_name,
    c.grade,
    c.section,
    c.subject,
    c.academic_year,
    COUNT(e.id)     AS total_enrolled
FROM classes c
LEFT JOIN students s
    ON s.grade = c.grade
    AND s.section = c.section
    AND s.tenant_id = c.tenant_id
LEFT JOIN enrollments e
    ON e.student_id = s.id
    AND e.academic_year = c.academic_year
    AND e.status = 'enrolled'
WHERE c.teacher_id = :teacher_id
  AND c.is_active = true
GROUP BY c.id
ORDER BY c.grade, c.section;


-- ─── 2. TEACHER: GET TODAY'S ATTENDANCE FOR A CLASS ──────────────────────────
-- Used when a teacher opens a specific class on the dashboard.
-- Shows each student's attendance status for a given date.
SELECT
    s.id                        AS student_id,
    s.student_id                AS student_code,
    s.name                      AS student_name,
    COALESCE(a.status, 'absent') AS status,
    a.checkin_time,
    a.confidence,
    a.is_manual_override,
    a.override_reason,
    a.location
FROM students s
JOIN enrollments e
    ON e.student_id = s.id
    AND e.academic_year = :academic_year
    AND e.status = 'enrolled'
JOIN classes c
    ON c.id = :class_id
    AND c.grade = s.grade
    AND c.section = s.section
LEFT JOIN student_attendance a
    ON a.student_id = s.id
    AND a.class_id = :class_id
    AND a.date = :date
WHERE s.is_active = true
ORDER BY s.name;


-- ─── 3. TEACHER: ATTENDANCE SUMMARY FOR A CLASS (DATE RANGE) ─────────────────
-- Used for the weekly/monthly summary view per class.
-- Returns per-student totals: present, late, absent counts.
SELECT
    s.id                                                        AS student_id,
    s.student_id                                                AS student_code,
    s.name                                                      AS student_name,
    COUNT(*) FILTER (WHERE a.status = 'present')                AS present_count,
    COUNT(*) FILTER (WHERE a.status = 'late')                   AS late_count,
    COUNT(*) FILTER (WHERE a.status = 'absent' OR a.id IS NULL) AS absent_count,
    ROUND(
        COUNT(*) FILTER (WHERE a.status IN ('present', 'late'))::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )                                                           AS attendance_rate_pct
FROM students s
JOIN enrollments e
    ON e.student_id = s.id
    AND e.academic_year = :academic_year
    AND e.status = 'enrolled'
JOIN classes c
    ON c.id = :class_id
    AND c.grade = s.grade
    AND c.section = s.section
LEFT JOIN student_attendance a
    ON a.student_id = s.id
    AND a.class_id = :class_id
    AND a.date BETWEEN :start_date AND :end_date
WHERE s.is_active = true
GROUP BY s.id, s.student_id, s.name
ORDER BY attendance_rate_pct ASC;


-- ─── 4. TEACHER: FLAG STUDENTS BELOW ATTENDANCE THRESHOLD ────────────────────
-- Used for at-risk attendance alerts on the dashboard.
-- Returns students below a given attendance rate (e.g. 80%).
SELECT
    s.id            AS student_id,
    s.student_id    AS student_code,
    s.name          AS student_name,
    s.grade,
    s.section,
    ROUND(
        COUNT(*) FILTER (WHERE a.status IN ('present', 'late'))::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    )               AS attendance_rate_pct
FROM students s
JOIN enrollments e
    ON e.student_id = s.id
    AND e.academic_year = :academic_year
    AND e.status = 'enrolled'
JOIN classes c
    ON c.id = :class_id
    AND c.grade = s.grade
    AND c.section = s.section
LEFT JOIN student_attendance a
    ON a.student_id = s.id
    AND a.class_id = :class_id
    AND a.date BETWEEN :start_date AND :end_date
WHERE s.is_active = true
GROUP BY s.id, s.student_id, s.name, s.grade, s.section
HAVING
    ROUND(
        COUNT(*) FILTER (WHERE a.status IN ('present', 'late'))::NUMERIC
        / NULLIF(COUNT(*), 0) * 100, 2
    ) < :threshold_pct   -- e.g. 80.00
ORDER BY attendance_rate_pct ASC;


-- ─── 5. TEACHER: MANUAL OVERRIDE HISTORY FOR A CLASS ─────────────────────────
-- Audit trail — shows all manually overridden attendance records for a class.
SELECT
    a.date,
    s.name              AS student_name,
    s.student_id        AS student_code,
    a.status,
    a.override_reason,
    adm.admin_name      AS overridden_by,
    a.created_at
FROM student_attendance a
JOIN students s      ON s.id = a.student_id
JOIN admins adm      ON adm.id = a.overridden_by
WHERE a.class_id = :class_id
  AND a.is_manual_override = TRUE
  AND a.date BETWEEN :start_date AND :end_date
ORDER BY a.date DESC, s.name;


-- ─── 6. PRINCIPAL/ADMIN: SCHOOL-WIDE ATTENDANCE FOR A DATE ───────────────────
-- Used on the admin dashboard — bird's eye view across all classes for a day.
SELECT
    c.grade,
    c.section,
    c.class_name,
    adm.admin_name                                              AS teacher_name,
    COUNT(DISTINCT s.id)                                        AS total_students,
    COUNT(*) FILTER (WHERE a.status = 'present')                AS present,
    COUNT(*) FILTER (WHERE a.status = 'late')                   AS late,
    COUNT(*) FILTER (WHERE a.status = 'absent' OR a.id IS NULL) AS absent
FROM classes c
JOIN admins adm ON adm.id = c.teacher_id
JOIN students s
    ON s.grade = c.grade
    AND s.section = c.section
    AND s.tenant_id = c.tenant_id
JOIN enrollments e
    ON e.student_id = s.id
    AND e.academic_year = :academic_year
    AND e.status = 'enrolled'
LEFT JOIN student_attendance a
    ON a.student_id = s.id
    AND a.class_id = c.id
    AND a.date = :date
WHERE c.is_active = true
  AND c.academic_year = :academic_year
GROUP BY c.id, c.grade, c.section, c.class_name, adm.admin_name
ORDER BY c.grade, c.section;


-- ─── 7. ENROLLMENT STATUS CHECK ──────────────────────────────────────────────
-- Used when a teacher tries to take attendance — flags students without embeddings.
SELECT
    s.id            AS student_id,
    s.student_id    AS student_code,
    s.name          AS student_name,
    e.status        AS enrollment_status,
    e.embedding_generated,
    e.quality_score
FROM students s
JOIN enrollments e
    ON e.student_id = s.id
    AND e.academic_year = :academic_year
JOIN classes c
    ON c.grade = s.grade
    AND c.section = s.section
    AND c.id = :class_id
WHERE s.is_active = true
  AND (e.status != 'enrolled' OR e.embedding_generated = FALSE)
ORDER BY e.status, s.name;
