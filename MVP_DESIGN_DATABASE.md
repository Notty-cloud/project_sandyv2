# MVP Design — Feature 2: Database & Data Layer

> Scope: The minimum database schema, indexing, data flow, and retention policies required to support enrollment, attendance, watchlist alerts, and consent management for a single school campus.

---

## 1. MVP Boundary

### In Scope

- PostgreSQL 15+ with `pgvector` extension
- Core tables: `student`, `biometric_template`, `attendance_log`, `camera_location`, `watchlist`, `security_alert`
- Basic indexing for sub-500ms recognition queries
- Referential integrity and cascade deletes for opt-out purges
- Append-only `audit_log` for compliance
- `docker-compose` provisioning

### Out of Scope (Post-MVP)

- Monthly table partitioning on `attendance_log`
- Cold-storage archival cron jobs
- Multi-tenant / multi-campus sharding
- Dedicated vector database (Milvus, Pinecone)
- Read replicas or high-availability clustering
- Automated 30-day biometric purge cron (manual purge via opt-out is sufficient for MVP)

---

## 2. Technology Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| RDBMS | PostgreSQL 15+ | Mature, open-source, native JSON support |
| Vector search | `pgvector` extension | Cosine similarity on 512-d embeddings without a separate service |
| Container | Official `postgres:15` Docker image | One-command setup via `docker-compose` |
| Migrations | Plain SQL files (`database/schema.sql`) | Simple, version-controlled, no ORM dependency |

---

## 3. Schema — MVP Entities

### 3.1 `student`

| Column | Type | Constraints |
|--------|------|-------------|
| `student_id` | `VARCHAR(20)` | **PK** |
| `first_name` | `VARCHAR(50)` | `NOT NULL` |
| `last_name` | `VARCHAR(50)` | `NOT NULL` |
| `is_opted_out` | `BOOLEAN` | `DEFAULT FALSE` |
| `guardian_email` | `VARCHAR(255)` | |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` |

---

### 3.2 `biometric_template`

| Column | Type | Constraints |
|--------|------|-------------|
| `template_id` | `UUID` | **PK** `DEFAULT gen_random_uuid()` |
| `student_id` | `VARCHAR(20)` | **FK → `student`**, `UNIQUE`, `ON DELETE CASCADE` |
| `face_embedding` | `VECTOR(512)` | `NOT NULL` |
| `algorithm_version` | `VARCHAR(10)` | `NOT NULL` |
| `updated_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` |

> 1 : 1 relationship with `student`. The `UNIQUE` constraint on `student_id` enforces this. Cascade delete ensures opt-out purges destroy the embedding automatically.

---

### 3.3 `camera_location`

| Column | Type | Constraints |
|--------|------|-------------|
| `location_id` | `UUID` | **PK** `DEFAULT gen_random_uuid()` |
| `device_name` | `VARCHAR(100)` | `NOT NULL` |
| `ip_address` | `INET` | `NOT NULL` |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` |

---

### 3.4 `attendance_log`

| Column | Type | Constraints |
|--------|------|-------------|
| `log_id` | `BIGSERIAL` | **PK** |
| `student_id` | `VARCHAR(20)` | **FK → `student`** |
| `location_id` | `UUID` | **FK → `camera_location`** |
| `timestamp` | `TIMESTAMPTZ` | `DEFAULT NOW()`, Indexed |
| `confidence_score` | `DECIMAL(5,2)` | `NOT NULL` |
| `needs_verification` | `BOOLEAN` | `DEFAULT FALSE` |

> `needs_verification` is `TRUE` when the confidence score falls in the $70\%$–$91\%$ partial-match band.

---

### 3.5 `watchlist`

| Column | Type | Constraints |
|--------|------|-------------|
| `watchlist_id` | `UUID` | **PK** `DEFAULT gen_random_uuid()` |
| `full_name` | `VARCHAR(100)` | `NOT NULL` |
| `face_embedding` | `VECTOR(512)` | `NOT NULL` |
| `risk_level` | `VARCHAR(10)` | `CHECK (risk_level IN ('low','medium','high','critical'))` |
| `reason` | `TEXT` | |
| `is_active` | `BOOLEAN` | `DEFAULT TRUE` |
| `created_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` |

> MVP uses a `VARCHAR` + `CHECK` constraint instead of a custom `ENUM` type for simpler migrations.

---

### 3.6 `security_alert`

| Column | Type | Constraints |
|--------|------|-------------|
| `alert_id` | `UUID` | **PK** `DEFAULT gen_random_uuid()` |
| `watchlist_id` | `UUID` | **FK → `watchlist`** |
| `location_id` | `UUID` | **FK → `camera_location`** |
| `severity_level` | `VARCHAR(10)` | `CHECK (severity_level IN ('low','medium','high','critical'))` |
| `is_resolved` | `BOOLEAN` | `DEFAULT FALSE` |
| `triggered_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` |

---

### 3.7 `audit_log`

| Column | Type | Constraints |
|--------|------|-------------|
| `audit_id` | `BIGSERIAL` | **PK** |
| `actor` | `VARCHAR(100)` | `NOT NULL` |
| `action` | `VARCHAR(50)` | `NOT NULL` (e.g., `'ENROLL'`, `'PURGE'`, `'ALERT_DISMISS'`) |
| `target_table` | `VARCHAR(50)` | |
| `target_id` | `VARCHAR(50)` | |
| `detail` | `JSONB` | Optional context |
| `performed_at` | `TIMESTAMPTZ` | `DEFAULT NOW()` |

> Append-only compliance log. No `UPDATE` or `DELETE` operations are issued against this table.

---

## 4. ER Diagram

```
student (1) ────────── (1) biometric_template
   │
   │ 1
   │
   └──────────── M attendance_log M ──────── 1 camera_location
                                                       │
                                                       1
                                                       │
watchlist 1 ──────────── M security_alert M ───────────┘

audit_log (standalone — no FK relationships)
```

---

## 5. Indexing Strategy — MVP

| Index | Table | Column(s) | Type | Purpose |
|-------|-------|-----------|------|---------|
| `idx_bt_embedding` | `biometric_template` | `face_embedding` | HNSW (`vector_cosine_ops`) | Sub-500ms nearest-neighbor search |
| `idx_bt_student` | `biometric_template` | `student_id` | B-Tree (implicit via `UNIQUE`) | Fast lookup for opt-out cascade |
| `idx_al_timestamp` | `attendance_log` | `timestamp` | B-Tree | Date-range queries for daily attendance |
| `idx_al_student` | `attendance_log` | `student_id` | B-Tree | Per-student attendance history |
| `idx_sa_triggered` | `security_alert` | `triggered_at` | B-Tree | Recent-alerts dashboard query |
| `idx_wl_embedding` | `watchlist` | `face_embedding` | HNSW (`vector_cosine_ops`) | Compare unknown faces against watchlist |

---

## 6. Key Queries

### 6.1 Match a face embedding (attendance)

```sql
SELECT s.student_id, s.first_name, s.last_name,
       1 - (bt.face_embedding <=> $1::vector) AS similarity
FROM biometric_template bt
JOIN student s ON s.student_id = bt.student_id
WHERE s.is_opted_out = FALSE
ORDER BY bt.face_embedding <=> $1::vector
LIMIT 1;
```

> Application layer checks: if `similarity >= 0.92` → confirmed; if `0.70–0.91` → verification needed; otherwise → no match.

### 6.2 Check against watchlist

```sql
SELECT w.watchlist_id, w.full_name, w.risk_level,
       1 - (w.face_embedding <=> $1::vector) AS similarity
FROM watchlist w
WHERE w.is_active = TRUE
ORDER BY w.face_embedding <=> $1::vector
LIMIT 1;
```

### 6.3 Daily attendance summary

```sql
SELECT s.student_id, s.first_name, s.last_name,
       MIN(al.timestamp) AS first_seen,
       al.location_id
FROM attendance_log al
JOIN student s ON s.student_id = al.student_id
WHERE al.timestamp >= $1::date
  AND al.timestamp <  $1::date + INTERVAL '1 day'
GROUP BY s.student_id, s.first_name, s.last_name, al.location_id
ORDER BY s.last_name;
```

---

## 7. Data Flow — MVP

```
          ┌─────────────┐
          │  RTSP Camera │
          └──────┬───────┘
                 │ video frames
                 ▼
          ┌─────────────┐
          │  Edge Node   │  (Python AI engine)
          │  - detect    │
          │  - embed     │
          │  - compare   │
          └──────┬───────┘
                 │ JSON event { student_id, location_id, confidence, timestamp }
                 ▼
          ┌─────────────┐
          │  Backend API │  (Node.js / Express)
          │  - validate  │
          │  - write log │
          │  - audit     │
          └──────┬───────┘
                 │ SQL
                 ▼
          ┌─────────────┐
          │  PostgreSQL  │
          │  + pgvector  │
          └─────────────┘
```

---

## 8. Data Integrity & Retention — MVP

| Policy | Detail |
|--------|--------|
| Referential integrity | `ON DELETE CASCADE` on `biometric_template.student_id` — deleting a student destroys their embedding |
| Opt-out purge | Setting `student.is_opted_out = TRUE` + deleting the `biometric_template` row in a single transaction |
| Raw images | **Never persisted.** Frames are held in memory during inference, then discarded |
| Audit immutability | No `UPDATE` or `DELETE` on `audit_log`; application enforces append-only |
| Backup | `pg_dump` nightly to a local encrypted volume (automated backup infra is post-MVP) |

> Monthly partitioning, cold-storage archival, and the 30-day graduated-student purge cron are deferred to post-MVP.

---

## 9. Docker Provisioning

The MVP database is provisioned via `docker-compose` with an init script:

```yaml
services:
  postgres:
    image: pgvector/pgvector:pg15
    environment:
      POSTGRES_DB: sandy_mvp
      POSTGRES_USER: sandy_app
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "5432:5432"
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./database/schema.sql:/docker-entrypoint-initdb.d/01_schema.sql
volumes:
  pgdata:
```

> Uses the `pgvector/pgvector` image which ships with the `vector` extension pre-installed.

---

## 10. MVP Exit Criteria

| Criterion | Measurement |
|-----------|-------------|
| Schema deploys cleanly | `docker-compose up` creates all tables + indexes without errors |
| Embedding insert + query | Insert 10 student embeddings; nearest-neighbor query returns correct match in $< 500$ms |
| Cascade delete | Deleting a student record removes the linked `biometric_template` row |
| Audit trail | Enrollment + purge actions produce entries in `audit_log` |
| Watchlist query | Insert a watchlist embedding; comparison query returns it with correct similarity |
