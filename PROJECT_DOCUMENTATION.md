# Project Sandy — Facial Recognition School Attendance System
### Project Documentation v1.0

---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Scope](#2-scope)
3. [Timeline](#3-timeline)
4. [Milestones](#4-milestones)
5. [RACI & Assigned Team Members](#5-raci--assigned-team-members)
6. [Success Criteria](#6-success-criteria)
7. [SDLC](#7-sdlc)
   - 7.1 [Planning](#71-planning)
   - 7.2 [Requirements Analysis](#72-requirements-analysis)
   - 7.3 [System Design](#73-system-design)
   - 7.4 [Development](#74-development)
   - 7.5 [Testing](#75-testing)
   - 7.6 [Deployment](#76-deployment)
   - 7.7 [Maintenance](#77-maintenance)
8. [Document Management](#8-document-management)

---

## 1. Purpose

Project Sandy is a facial recognition-based school attendance system developed as a capstone AI application. The system replaces manual attendance registers with an automated, biometric solution capable of identifying enrolled students via live camera or uploaded photographs, recording attendance in real time, and providing administrative oversight through a web-based interface.

The project serves as a demonstration of applied artificial intelligence within an institutional context, covering the full software development lifecycle from planning through to testing, with deployment to a public-facing environment as a concluding deliverable.

**Objectives:**
- Design and build a functional AI agent capable of identifying individuals using facial recognition
- Apply responsible AI principles and data privacy considerations throughout development
- Demonstrate effective use of an agreed SDLC, version control, and collaborative development practices
- Deliver a multi-role, multi-tenant web application suitable for real-world adoption

---

## 2. Scope

**In Scope:**
- Student facial enrollment via live webcam capture or uploaded photograph
- Real-time attendance marking using face identification and cosine similarity matching
- Role-based access control with three tiers: Teacher, Coordinator, and Head Teacher
- Class and subject management (multi-subject per grade and section)
- Manual attendance override capability
- Admin account management (create, edit, deactivate, unlock)
- Group photo identification (identify multiple students in a single image)
- Multi-tenant data isolation (supporting multiple schools on a single deployment)
- Secure JWT-based authentication with account lockout after repeated failed attempts
- Audit logging of all authentication events
- Deployment to Railway cloud platform with a registered domain

**Target Institutions:**
- Ellerslie School
- Alma Parris School

**Out of Scope:**
- Mobile application (native iOS or Android)
- Offline/local-only operation without internet connectivity
- Integration with third-party student information systems (SIS)
- Payroll or HR-linked attendance functionality
- Fingerprint or other biometric modalities

**Executive Summary:**

Project Sandy addresses the administrative burden of manual attendance tracking in schools by introducing a biometric system that is both fast and auditable. By combining a React-based web interface with a Django REST API and a DeepFace-powered AI engine, the system enables teachers to enrol students once and mark attendance through facial recognition thereafter. The system is designed with security, privacy, and role segregation at its core, ensuring that sensitive biometric data is handled responsibly. The business value lies in reduced administrative overhead, improved attendance accuracy, and a foundation for data-driven reporting.

**KPIs:**
- Face identification accuracy above 65% cosine similarity threshold
- Enrollment-to-recognition success rate across varied lighting conditions
- System response time for face identification under 5 seconds per image
- Zero plaintext storage of biometric or credential data
- All four SDLC phases completed and evidenced through version control history

---

## 3. Timeline

| | |
|---|---|
| **Start Date** | [Insert Start Date — e.g. January 2026] |
| **End Date** | [Start Date + 4 months] |
| **Total Duration** | 4 months |
| **Current Phase** | Testing |

---

## 4. Milestones

### 4.1 Completed Milestones

| Function | Purpose | Scope | Start Date | Completion Date |
|---|---|---|---|---|
| Planning | Define project goals, assign roles, establish version control, agree SDLC | Project scope, team structure, GitHub repository, branching strategy | [Month 1] | [Month 1] |
| Requirements Analysis | Identify functional and non-functional requirements, define stakeholder needs | User stories, system requirements, role hierarchy, privacy considerations | [Month 1] | [Month 1] |
| System Design | Architect the full system — database schema, API endpoints, UI wireframes, AI pipeline | React SPA, Django REST API, DeepFace AI engine, SQLite schema | [Month 1–2] | [Month 2] |
| Development | Build all system components: frontend, backend, AI engine, authentication, role-based access | All core features implemented and integrated | [Month 2] | [Month 4] |

### 4.2 Current Milestones

| Function | Purpose | Scope | Start Date | Due Date |
|---|---|---|---|---|
| Testing | Validate all functional requirements against actual behaviour; identify and resolve defects | Functional testing, integration testing, UAT with fixture data across all roles | [Month 4] | [End Date] |

---

## 5. RACI & Assigned Team Members

**RACI Key:**
- **R — Responsible:** Does the work
- **A — Accountable:** Owns the outcome (one per function)
- **C — Consulted:** Provides expertise or input
- **I — Informed:** Kept up to date

| Function | Kevin Bayley (Backend) | Shanade Alleyne (Frontend) | Samuel Springer (AI) | Nathan Graham (AI) | Druell Alstrom (QA) | Ashlie Fields (QA) |
|---|---|---|---|---|---|---|
| Project Planning & Coordination | A | C | C | C | C | C |
| Requirements Analysis | A | R | R | R | R | R |
| System Architecture & Design | A/R | C | C | C | I | I |
| Database Design & Data Layer | A/R | I | C | C | I | I |
| REST API Development | A/R | C | C | I | I | I |
| Authentication & Security | A/R | C | I | I | I | I |
| Frontend Development (React/Vite) | C | A/R | I | I | I | I |
| UI/UX Design (Tailwind) | I | A/R | I | I | C | C |
| AI Engine — Face Detection | C | I | A/R | R | I | I |
| AI Engine — Embedding & Matching | C | I | A/R | R | I | I |
| Frontend–Backend Integration | A | R | C | C | I | I |
| Testing & Quality Assurance | I | I | I | I | A/R | R |
| Test Data & Fixture Management | A | I | I | I | R | R |
| Version Control & Branching | A | R | R | R | R | R |
| Documentation | A | R | R | R | R | R |
| Deployment | A | C | C | C | I | I |
| Responsible AI & Privacy Review | A | C | R | R | C | C |

---

## 6. Success Criteria

- **Foundational Learning:** The project demonstrates challenges encountered and lessons learned throughout development, evidencing growth in applied AI, full-stack development, and collaborative working.

- **Functional AI Agent:** A working facial recognition agent is delivered that can enrol students, identify faces across varied conditions, and return cosine similarity scores above a defined threshold (0.65).

- **SDLC Adherence:** The project visibly follows all four agreed phases — Planning, Design, Build, and Test — with each phase documented and evidenced through commit history, milestones, and this document.

- **Version Control Practices:** The GitHub repository demonstrates effective use of branching strategies, meaningful commit messages, pull requests, and issue tracking throughout the development lifecycle.

- **Responsible AI & Security:**
  - No raw biometric data (face images) is persisted; only 512-dimensional normalised embeddings are stored
  - No personally identifiable data is committed to the public repository (no real student records, no face photographs in version control)
  - All passwords are hashed using bcrypt_sha256; JWT tokens are used for session management
  - Fixture/demo data used for testing contains only fictional student names
  - Privacy implications for both target institutions (Ellerslie School and Alma Parris School) have been considered in the system design

---

## 7. SDLC

### 7.1 Planning

**Overview:**
The planning phase established the project foundation — agreeing on the problem to solve, the technology stack, team responsibilities, and how work would be managed and tracked.

**Activities Completed:**
- Problem statement defined: manual attendance is time-consuming, error-prone, and difficult to audit
- Project name "Sandy" agreed upon
- Technology stack selected:
  - **Frontend:** React 18 + Vite + Tailwind CSS
  - **Backend:** Django 5 + Django REST Framework
  - **AI Engine:** DeepFace (Facenet512 model), ONNX Runtime
  - **Authentication:** PyJWT + bcrypt_sha256
  - **Database:** SQLite (development), PostgreSQL (production via Railway)
  - **Version Control:** GitHub (`dev` branch as primary working branch)
- Roles and responsibilities assigned (see RACI, Section 5)
- Repository created at [GitHub Repository URL]
- Branching strategy agreed: feature branches merged into `dev` via pull requests
- Self-funded deployment plan agreed: Railway cloud platform with a registered domain

**Key Decisions:**
- Multi-tenant architecture chosen to support multiple schools (Ellerslie, Alma Parris) on a single deployment
- Role hierarchy of three tiers (Teacher, Coordinator, Head Teacher) to match real institutional structures
- Facial embeddings stored as 512-float vectors rather than raw images, to minimise privacy exposure

---

### 7.2 Requirements Analysis

**Functional Requirements:**

| ID | Requirement | Priority |
|---|---|---|
| FR-01 | System shall allow authorised users to enrol a student by capturing a face via webcam or uploading an image | High |
| FR-02 | System shall generate a 512-dimensional facial embedding for each enrolled student | High |
| FR-03 | System shall identify a student from a submitted photo using cosine similarity against stored embeddings | High |
| FR-04 | System shall mark attendance automatically upon successful face identification | High |
| FR-05 | System shall support manual attendance override by authorised users | Medium |
| FR-06 | System shall enforce role-based access: Teacher (L1), Coordinator (L2), Head Teacher (L3) | High |
| FR-07 | System shall allow group photo submission and return identification results per detected face | Medium |
| FR-08 | System shall support class and subject management (multiple subjects per grade/section) | High |
| FR-09 | System shall lock accounts after repeated failed login attempts | High |
| FR-10 | System shall log all authentication events for audit purposes | Medium |

**Non-Functional Requirements:**

| ID | Requirement |
|---|---|
| NFR-01 | Face identification response time shall not exceed 5 seconds under normal conditions |
| NFR-02 | All passwords shall be stored using bcrypt_sha256 hashing; no plaintext credentials |
| NFR-03 | JWT tokens shall expire within a configurable time window |
| NFR-04 | No real student photographs or personally identifiable data shall be committed to the repository |
| NFR-05 | The system shall support multi-tenant data isolation via tenant_id on all records |
| NFR-06 | The API shall validate all inputs at system boundaries and return structured error responses |

**Stakeholder Analysis:**

| Stakeholder | Role | Needs |
|---|---|---|
| Head Teacher | Administrator | Full system control, account management, audit visibility |
| Coordinator | Administrator | Enrolment management, class coordination, student oversight |
| Teacher | End user | Quick attendance marking, student enrolment for their classes only |
| Student | Subject of system | Accurate identification, privacy of biometric data |
| School Management | Institutional owner | Reliable records, compliance with data handling obligations |

---

### 7.3 System Design

**Architecture Overview:**

```
Browser (React SPA :5173)
    │
    │  HTTP + JWT Bearer token
    ▼
Django REST API (:3000)
    │
    ├── admins app       — authentication, JWT, account lockout, audit log
    ├── students app     — student CRUD, face enrolment, identification
    ├── classes app      — class/subject management
    ├── enrollments app  — enrolment workflow and status tracking
    ├── attendance app   — attendance records with confidence scores
    └── ai_engine        — DeepFace (Facenet512) face detection & embedding
```

**Database Schema Highlights:**

| Table | Key Fields | Purpose |
|---|---|---|
| `admins_admin` | id (UUID), tenant_id, role, authorization_level, password_hash | Staff accounts with role-based access |
| `students_student` | id (UUID), tenant_id, student_id, grade, section | Student records |
| `students_studentembedding` | student FK, embedding (512 floats), version, quality_score | Stored facial embeddings |
| `classes_class` | tenant_id, grade, section, subject, teacher FK | Subject-level classes |
| `enrollments_enrollment` | student FK, academic_year, status, embedding_generated | Enrolment workflow state |
| `attendance_studentattendance` | student FK, class FK, confidence, timestamp | Attendance records |
| `admins_authadditlog` | admin FK, event_type, ip_address, timestamp | Audit trail |

**Role Hierarchy:**

| Profile | Role | Level | Permissions |
|---|---|---|---|
| Teacher | teacher | 1 | Mark attendance, view and enrol own class students |
| Coordinator | admin | 2 | All teacher permissions + enrolment management + class management |
| Head Teacher | admin | 3 | Full access including account management and system administration |

**AI Pipeline:**
1. Image submitted via multipart form
2. DeepFace detects face(s) using SCRFD / OpenCV detector
3. Facenet512 model generates 512-dimensional embedding per face
4. Embedding is L2-normalised to a unit vector
5. Cosine similarity computed against all active embeddings for the tenant
6. Match returned if similarity ≥ 0.65 threshold

**Security Design:**
- Passwords hashed with `bcrypt_sha256` (Django's `make_password`)
- JWT tokens signed with `HS256`, carrying role and authorization level claims
- Account lockout after configurable number of failed attempts (`LOGIN_LOCKOUT_THRESHOLD`)
- Login endpoint rate-limited (5 requests/minute per IP)
- CORS restricted to known frontend origins
- No face images persisted — only embeddings stored

---

### 7.4 Development

**Frontend (Shanade Alleyne):**
- React 18 SPA built with Vite and Tailwind CSS
- Pages: Sign In, Dashboard, Attendance View, Enrolment Hub, Manual Override, Class Management, Admin Management
- Role-aware rendering: Teacher view vs Coordinator/Head Teacher view within the same components
- WebRTC camera integration for live face capture (`getUserMedia`)
- Enrollment modal with four phases: Enrol → Enrolled → Verify → Recognition Result
- Group photo identification modal
- JWT stored in `localStorage`; Axios interceptor attaches token to all requests and redirects on 401

**Backend (Kevin Bayley):**
- Django REST Framework with `ModelViewSet` per resource
- Custom `RoleLevelPermission` class enforcing role and authorization level per action
- `AdminJWTAuthentication` middleware validating Bearer tokens on all protected endpoints
- Multi-tenant data isolation via `tenant_id` on all models
- Atomic transactions for embedding creation (prevents duplicate version numbers under concurrency)
- Audit log written on every login attempt, logout, and password change
- Demo data fixture (`fixtures/demo_data.json`) for rapid tester onboarding

**AI Engine (Samuel Springer & Nathan Graham):**
- DeepFace library with Facenet512 model (512-dim embeddings)
- Detector chain: OpenCV (primary, no download required) → RetinaFace → MTCNN
- `enforce_detection=False` fallback ensures enrolment never completely fails on difficult images
- `extract_all_embeddings()` function detects and embeds all faces in a group photo
- Cosine similarity computation using L2-normalised vectors
- UTF-8 stdout/stderr patch applied to prevent Windows cp1252 encoding errors from DeepFace's emoji logger

**Version Control Practices:**
- Repository: GitHub (`dev` as the primary branch)
- Commit convention: `type: description` (feat, fix, chore, refactor)
- All changes pushed to `dev` branch; significant features committed with descriptive messages
- Demo fixture committed to allow teammates to reproduce the exact test environment

---

### 7.5 Testing

**Status:** In Progress

**Testing Approach:**

| Type | Description | Responsible |
|---|---|---|
| Functional Testing | Verify each feature behaves according to requirements | Druell Alstrom, Ashlie Fields |
| Integration Testing | Verify frontend–backend–AI pipeline works end-to-end | Druell Alstrom, Ashlie Fields |
| Role-Based Access Testing | Confirm each role can only access permitted features | Druell Alstrom, Ashlie Fields |
| Security Testing | Verify account lockout, JWT expiry, and CORS enforcement | Druell Alstrom, Ashlie Fields |
| User Acceptance Testing (UAT) | Testers use demo fixture accounts to simulate real use | All contributors |

**Test Accounts (Demo Fixture):**

| Username | Password | Role |
|---|---|---|
| `admin` | `Admin@sandy1` | Head Teacher — full access |
| `coordinator1` | `Coord@sandy1` | Coordinator — enrolment + class management |
| `teacher1` | `Teach@sandy1` | Teacher — Grade 10A (Mathematics, English) |
| `teacher2` | `Teach2@sandy1` | Teacher — Grade 10A & 10B (Science) |

**Test Environment Setup:**
```bash
git pull origin dev
del db.sqlite3              # Windows: removes old database
python manage.py migrate
python manage.py loaddata fixtures/demo_data.json
python manage.py runserver 3000   # Backend
npm run dev                        # Frontend (separate terminal)
```

**Key Test Scenarios:**

| ID | Scenario | Expected Outcome |
|---|---|---|
| TC-01 | Teacher logs in and views only their assigned classes | Only Grade 10A classes shown for teacher1 |
| TC-02 | Teacher enrols a student using live camera capture | Embedding generated, status set to Enrolled |
| TC-03 | Teacher enrols a student using an uploaded image | Same outcome as TC-02 |
| TC-04 | Coordinator runs face verification after enrolment | Cosine similarity score displayed |
| TC-05 | Group photo uploaded with multiple students | Each detected face matched and listed |
| TC-06 | Invalid credentials entered 5 times | Account locked, unlock required from Head Teacher |
| TC-07 | Teacher attempts to access Class Management | Redirected to Dashboard (access denied) |
| TC-08 | Head Teacher creates a new Coordinator account | Account appears in Admin Management |
| TC-09 | Manual attendance override applied | Attendance record updated with override flag |
| TC-10 | Escape key or backdrop click closes enrolment modal | Modal closes, camera stream released |

---

### 7.6 Deployment

**Status:** Planned (post-testing)

**Platform:** Railway (railway.app)
**Domain:** Custom domain to be registered
**Database:** PostgreSQL (Railway managed instance, replacing SQLite)
**Funding:** Self-funded by contributors

**Deployment Steps (Planned):**
1. Switch `DATABASE_URL` in environment to Railway PostgreSQL instance
2. Set all production environment variables (`SECRET_KEY`, `JWT_SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS`, `FRONTEND_ORIGIN`)
3. Run `python manage.py migrate` against production database
4. Run `python manage.py loaddata fixtures/demo_data.json` to seed initial accounts
5. Configure custom domain in Railway dashboard and update `ALLOWED_HOSTS` and `CORS_ALLOWED_ORIGINS`
6. Build frontend: `npm run build`
7. Serve frontend via Railway static hosting or a CDN
8. Verify HTTPS is enforced on all endpoints

**Environment Variables Required:**

| Variable | Purpose |
|---|---|
| `SECRET_KEY` | Django secret key |
| `JWT_SECRET_KEY` | JWT signing secret |
| `DEBUG` | Set to `False` in production |
| `ALLOWED_HOSTS` | Domain and Railway subdomain |
| `DATABASE_URL` | PostgreSQL connection string |
| `FRONTEND_ORIGIN` | Deployed frontend URL (for CORS) |
| `ACCESS_TOKEN_LIFETIME_HOURS` | JWT token expiry |
| `LOGIN_LOCKOUT_THRESHOLD` | Max failed attempts before lockout |

---

### 7.7 Maintenance

As the system moves into a live environment, the maintenance phase will address ongoing operational needs and iterative improvements based on user feedback from Ellerslie School and Alma Parris School.

**Planned Updates:**
- Transition from SQLite to PostgreSQL for multi-user concurrency
- Implement attendance reporting and export (CSV/PDF) for administrative use
- Add a student management interface (currently students are added via API/admin shell)
- Introduce push notifications or email alerts for attendance anomalies
- Improve face recognition accuracy with multi-embedding enrolment (up to 5 photos per student already supported)
- Add a student-facing view for parents or guardians to view attendance records

**Security & Compliance Maintenance:**
- Rotate `JWT_SECRET_KEY` and `SECRET_KEY` on a periodic basis
- Review and update `bcrypt` cost factor as hardware improves
- Audit stored embeddings for data retention compliance
- Review GDPR/data privacy obligations for any expansion beyond the two target schools

**Version Control During Maintenance:**
- All updates will follow the same branching strategy used during development
- Bug fixes committed as `fix:` prefixed commits
- Feature additions committed as `feat:` prefixed commits
- Patch releases tagged in GitHub with semantic versioning (`v1.x.x`)

---

## 8. Document Management

### 8.1 Version History

| Version | Date | Author | Change Description |
|---|---|---|---|
| 1.0 | 2026-05-13 | Kevin Bayley | Initial project documentation draft |

### 8.2 Contributors

| Name | Role | Responsibility |
|---|---|---|
| Kevin Bayley | Backend Developer | Data layer, REST API, authentication, deployment |
| Shanade Alleyne | Frontend Developer | React SPA, UI/UX, camera integration |
| Samuel Springer | AI Engineer | Face detection pipeline, embedding model, cosine similarity |
| Nathan Graham | AI Engineer | AI engine implementation and integration |
| Druell Alstrom | QA Engineer | Test planning, functional and integration testing |
| Ashlie Fields | QA Engineer | Test execution, defect reporting, UAT coordination |

### 8.3 Approvers

| Name | Role | Date |
|---|---|---|
| Curtis Miller | Head of AI Applications Department | |
| Ian Freer | Head of AI Department | |

---

*Project Sandy — Facial Recognition School Attendance System*
*Documentation v1.0 — Confidential*
