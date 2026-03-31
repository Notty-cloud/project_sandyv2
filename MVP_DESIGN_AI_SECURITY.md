# MVP Design — Feature 1: Facial Recognition Engine & Security

> Scope: The minimum viable recognition pipeline, enrollment workflow, attendance matching, and security posture needed to demo the system at a single school campus.

---

## 1. MVP Boundary

### In Scope

- Student biometric enrollment (capture → embedding → store)
- Real-time attendance matching via facial recognition
- Consent management (opt-in / opt-out with data purge)
- Watchlist alerting for restricted individuals
- Single-school, single-campus deployment
- Basic role-based access (Registrar, System Admin, Security Officer)
- React admin dashboard (read/write)

### Out of Scope (Post-MVP)

- Multi-campus / multi-tenant management
- SIS integration (PowerSchool, Infinite Campus, etc.)
- Mobile app (Flutter) for security officers
- Live stream overlay with bounding boxes
- Geofencing / anomaly location reporting
- Behavioral analysis and fall detection
- Visitor management (QR + face pairing)
- PDF/CSV/XLSX report generation
- SMTP parent notifications
- Explainable AI confidence logs

---

## 2. AI Pipeline — MVP Architecture

### 2.1 Model Stack

| Stage | Model / Method | Output |
|-------|---------------|--------|
| Face Detection | MTCNN or RetinaFace | Bounding box + alignment landmarks |
| Liveness Check | Simple RGB-based anti-spoof classifier | `pass` / `fail` boolean |
| Embedding | ArcFace (ResNet-100 backbone) | 512-dimensional float vector |

> **MVP note:** Full IR/depth liveness is post-MVP. The MVP uses a lightweight 2D anti-spoof model to reject obvious photo attacks.

### 2.2 Inference Pipeline (Edge Node)

```
RTSP frame capture
      │
      ▼
 Face Detection (MTCNN)
      │
      ▼
 Liveness Check ── fail ──▶ discard frame
      │ pass
      ▼
 ArcFace Embedding (512-d)
      │
      ▼
 Cosine Similarity vs. local cache
      │
      ├─ score ≥ 0.92 ──▶ LOG: attendance confirmed
      ├─ 0.70–0.91 ─────▶ LOG: "Verification Needed" flag
      └─ score < 0.70 ──▶ compare against watchlist cache
                              ├─ match ──▶ ALERT: security event
                              └─ no match ▶ LOG: unknown face (discard)
```

### 2.3 Performance Targets (MVP)

| Metric | Target |
|--------|--------|
| Cold start (model load → first detection) | $< 1.5$s |
| Warm match (frame → identity) | $< 500$ms |
| Minimum confidence for auto-attendance | $\geq 92\%$ |
| Verification band (manual review) | $70\%$–$91\%$ |

### 2.4 Embedding Storage

- Vectors are stored in PostgreSQL via **pgvector** extension.
- Embeddings are salted before storage so raw vectors cannot reconstruct a face.
- Edge nodes cache the active student embedding set in memory at startup and refresh on a configurable interval.

---

## 3. Core Workflows (MVP)

### 3.1 Student Enrollment

**Actors:** Registrar (primary), Student (secondary)

1. Registrar selects a student from the local roster.
2. System checks that a consent flag is set to `TRUE`.
3. Registrar activates the enrollment camera.
4. System captures 3–5 frames (left, center, right).
5. System runs each frame through the pipeline → generates embedding.
6. System stores the best-quality embedding in `biometric_template`; raw images are **never persisted**.
7. Student status set to `"Active - Biometric"`.

### 3.2 Automated Attendance

**Actors:** Student (primary)

1. Student enters a check-in zone covered by an RTSP camera.
2. Edge node runs the inference pipeline.
3. On match ($\geq 92\%$), system writes to `attendance_log` with student ID, camera location, timestamp, and confidence score.
4. Partial matches ($70\%$–$91\%$) are logged with a `"Verification Needed"` flag for manual review.

### 3.3 Consent Opt-Out & Data Purge

**Actors:** Parent/Guardian (primary), Registrar (secondary)

1. Registrar selects the student record and triggers **"Revoke Consent & Purge."**
2. System deletes the student's `biometric_template` record (embedding permanently destroyed).
3. `student.is_opted_out` set to `TRUE`.
4. Student remains in the roster for manual attendance only.

### 3.4 Watchlist Alert

**Actors:** Security Officer (primary)

1. An unmatched face is compared against the watchlist embedding cache.
2. On match, system creates a `security_alert` record with severity level and camera location.
3. Dashboard displays the alert in real time.

> **MVP note:** Alerts appear on the React dashboard only. Push notifications to mobile are post-MVP.

---

## 4. Security & Compliance — MVP Baseline

### 4.1 Data Protection

| Control | Implementation |
|---------|---------------|
| Embedding security | Salted vector embeddings; raw images never stored |
| Transport encryption | HTTPS / TLS 1.2+ for all API traffic |
| At-rest encryption | PostgreSQL `pgcrypto` for sensitive columns |
| Access control | API-key + role-based middleware (Registrar, Admin, Security) |

### 4.2 Privacy & Legal

| Requirement | MVP Implementation |
|-------------|-------------------|
| FERPA (US) | Student biometric data classified as PII; access restricted by role |
| Consent | Digital consent flag per student; enrollment blocked if `FALSE` |
| Right to be Forgotten | Opt-out workflow permanently deletes all biometric data |
| Data minimization | Raw images discarded immediately after embedding extraction |

### 4.3 MVP Auth Model

- **Registrar:** enroll/unenroll students, view attendance, trigger opt-out purges.
- **System Admin:** manage cameras, view system health, access all data.
- **Security Officer:** view watchlist alerts, dismiss false positives.

> **MVP note:** A simple API-key-per-role scheme is sufficient. Full IdP integration (Auth0/Keycloak + MFA) is post-MVP.

### 4.4 Logging & Audit

- All enrollment, purge, and alert-dismiss actions are logged with actor, timestamp, and affected record.
- Logs are append-only within the MVP; no modification or deletion permitted.

---

## 5. Deployment — MVP

| Component | Target |
|-----------|--------|
| Edge node | Single on-premise machine (Ubuntu, Docker) running the AI engine (Python) |
| Backend API | Node.js / Express in a Docker container |
| Frontend | React SPA served from the same host or a simple cloud VM |
| Database | PostgreSQL 15+ with `pgvector` extension |
| Orchestration | `docker-compose` (K3s / Kubernetes is post-MVP) |

---

## 6. MVP Exit Criteria

| Criterion | Measurement |
|-----------|-------------|
| Enrollment works end-to-end | 10 test students enrolled, embeddings stored, raw images discarded |
| Attendance recognition | 10/10 enrolled students correctly identified within 2 seconds |
| Opt-out purge | Biometric record fully deleted; student falls back to manual attendance |
| Watchlist alert | Known watchlist face triggers dashboard alert within 3 seconds |
| No critical security findings | Basic pen-test passes with zero critical vulnerabilities |
