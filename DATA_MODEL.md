# Data Model & Schema Specification

---

## 1. Naming Conventions & Design Standards

| Standard | Detail |
|----------|--------|
| **Case Style** | `snake_case` for all table and column names |
| **Pluralization** | Table names are singular (e.g., `student` not `students`) |
| **Normalization** | Third Normal Form (3NF) with indexed foreign keys to minimize join overhead |
| **Primary Keys** | All tables use `UUID` or `BIGSERIAL` for unique identification |

---

## 2. Entity Definitions

### 2.1 `camera_location` *(New)*
> Defines the physical source of the video stream.

| Column | Type | Notes |
|--------|------|-------|
| `location_id` | `UUID` | PK |
| `device_name` | `VARCHAR(100)` | e.g., `"North Gate Entrance"` |
| `ip_address` | `INET` | |
| `is_active` | `BOOLEAN` | Default: `TRUE` |
| `created_at` | `TIMESTAMPTZ` | |

---

### 2.2 `student`

| Column | Type | Notes |
|--------|------|-------|
| `student_id` | `VARCHAR(20)` | PK — Internal School ID |
| `first_name` | `VARCHAR(50)` | |
| `last_name` | `VARCHAR(50)` | |
| `is_opted_out` | `BOOLEAN` | Default: `FALSE` |
| `guardian_email` | `VARCHAR(255)` | |

---

### 2.3 `biometric_template`

| Column | Type | Notes |
|--------|------|-------|
| `template_id` | `UUID` | PK |
| `student_id` | `VARCHAR(20)` | FK → `student` |
| `face_embedding` | `VECTOR(512)` | Stored via `pgvector` or similar |
| `algorithm_version` | `VARCHAR(10)` | Tracks which AI model generated the vector |
| `updated_at` | `TIMESTAMPTZ` | |

---

### 2.4 `attendance_log`

| Column | Type | Notes |
|--------|------|-------|
| `log_id` | `BIGSERIAL` | PK |
| `student_id` | `VARCHAR(20)` | FK → `student` |
| `location_id` | `UUID` | FK → `camera_location` |
| `timestamp` | `TIMESTAMPTZ` | Indexed for reporting |
| `confidence_score` | `DECIMAL(5,2)` | e.g., `98.45` |

---

### 2.5 `watchlist`

| Column | Type | Notes |
|--------|------|-------|
| `watchlist_id` | `UUID` | PK |
| `full_name` | `VARCHAR(100)` | Display name of restricted individual |
| `face_embedding` | `VECTOR(512)` | Stored via `pgvector` |
| `risk_level` | `ENUM` | `'low'`, `'medium'`, `'high'`, `'critical'` |
| `reason` | `TEXT` | Notes on why the individual is restricted |
| `added_by` | `VARCHAR(100)` | Admin who created the record |
| `is_active` | `BOOLEAN` | Default: `TRUE` |
| `created_at` | `TIMESTAMPTZ` | |

---

### 2.6 `security_alert` *(New)*

| Column | Type | Notes |
|--------|------|-------|
| `alert_id` | `UUID` | PK |
| `watchlist_id` | `UUID` | FK → `watchlist` |
| `location_id` | `UUID` | FK → `camera_location` |
| `severity_level` | `ENUM` | `'low'`, `'medium'`, `'high'`, `'critical'` |
| `is_resolved` | `BOOLEAN` | Default: `FALSE` |
| `triggered_at` | `TIMESTAMPTZ` | |

---

## 3. Relationships & Cardinality

| Relationship | Cardinality | Description |
|-------------|-------------|-------------|
| `camera_location` → `attendance_log` | 1 : M | One camera captures thousands of entry events |
| `student` → `biometric_template` | 1 : 1 | Strict mapping to prevent identity conflicts |
| `watchlist` → `security_alert` | 1 : M | A single restricted individual can trigger multiple alerts as they move |
| `camera_location` → `security_alert` | 1 : M | A specific camera can be the source of multiple security events |

---

## 4. Indexing Strategy for Performance

> To meet the `< 500ms` latency requirement, the following indexes are mandatory:

| Index | Table | Column(s) | Type | Purpose |
|-------|-------|-----------|------|---------|
| `idx_attendance_timestamp` | `attendance_log` | `timestamp` | B-Tree | Fast range queries for reporting |
| `idx_attendance_student` | `attendance_log` | `student_id` | B-Tree | Quick lookup by student |
| `idx_attendance_location` | `attendance_log` | `location_id` | B-Tree | Filter by camera |
| `idx_face_embedding` | `biometric_template` | `face_embedding` | HNSW | Sub-500ms vector similarity search |
| `idx_alert_triggered` | `security_alert` | `triggered_at` | B-Tree | Chronological alert queries |

---

## 5. Data Retention & Integrity

- **Referential Integrity:** `ON DELETE CASCADE` applied to `biometric_template` when a parent `student` record is removed.
- **Scheduled Biometric Purge:** A cron job runs every 30 days to permanently delete `biometric_template` records for students who have graduated or been withdrawn, in compliance with the SRS data retention policy.
- **Partitioning:** `attendance_log` is partitioned by **month** to ensure current-semester queries don't degrade as the database grows over years.
- **Purge Policy:** A cron job runs monthly to archive `attendance_log` entries older than **365 days** to cold storage, maintaining primary database performance.

---

## 6. Visual ER Diagram

```
student (1) ──────────────── (1) biometric_template
   │
   │ (1)
   │
   └──────────────────────── (M) attendance_log (M) ──── (1) camera_location
                                                                    │
watchlist (1) ──────────────────────────── (M) security_alert (M) ──┘
```

---

## Summary

By adding the `camera_location` and `security_alert` entities, the schema closes the loop on physical hardware and the security response workflow. Using specialized vector indexing (**HNSW**) ensures that as the student body grows from 500 to 5,000, recognition speed stays under the critical `500ms` threshold.
