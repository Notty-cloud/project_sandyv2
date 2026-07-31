# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Project Sandy is a facial recognition-based school attendance system. A React SPA communicates with a Django REST API, which delegates face detection and embedding to a dedicated Python AI engine.

## Commands

### Frontend (React/Vite) — run from project root
```bash
npm install          # Install dependencies
npm run dev          # Dev server at http://localhost:5173
npm run build        # Production build
npm run preview      # Preview production build
```

### Backend (Django) — run from project root
```bash
python manage.py runserver 3000   # API server at http://localhost:3000 (must specify port)
python manage.py migrate          # Apply database migrations
python manage.py load_seed_data   # Load POC sample data into SQLite
python manage.py prune_token_blacklist  # Prune expired blacklisted tokens (run daily in prod)
pip install -r requirements.txt   # Install Python dependencies
```

### Admin bootstrapping
Use `create_admin.py` — **not** `createsuperuser` — to create the first Level-3 Admin account:
```bash
python create_admin.py
```
This creates a custom `Admin` record (not a Django User) and enforces password strength requirements.

### Running tests
```bash
python manage.py test admins      # Only admins app has tests (19 cases covering auth/lockout/blacklist)
```

### Environment setup
Copy `.env.example` to `.env` and populate:

| Variable | Notes |
|----------|-------|
| `SECRET_KEY` | Required in production |
| `JWT_SECRET_KEY` | Required in production |
| `DEBUG` | Set `True` for local dev |
| `DATABASE_URL` | Optional; falls back to SQLite if unset |
| `REDIS_URL` | Optional; token blacklist falls back to DB if Redis unavailable |
| `VITE_API_BASE_URL` | Frontend only; defaults to `http://localhost:3000/api` |
| `FACE_MATCHING_THRESHOLD` | Cosine similarity cutoff (default 0.65) |
| `FACE_QUALITY_THRESHOLD` | Detection confidence threshold (default 0.6) |
| `FACE_BACKEND` | `deepface` (default) or `onnx` — see Face recognition below |

No model files need to be downloaded for the default backend. DeepFace fetches
its Facenet512 weights automatically, and the Docker image pre-fetches them at
build time via `scripts/warm_face_models.py`.

## Architecture

### Request flow
Browser → React SPA (`:5173`) → Axios (with JWT header) → Django REST API (`:3000`) → Django app views → face backend (in-process) → DeepFace/TensorFlow

Vite proxies `/api` calls from `:5173` to `:3000` in development (`vite.config.js`).

### Frontend (`src/`)
- **`App.jsx`** — route definitions and role guards (`isLevel3Admin()`, `isLevel2Admin()`, `isAdminRole()`); unauthorized routes redirect to `/dashboard`
- **`pages/`** — eight views: `SignIn`, `Dashboard`, `AttendanceView`, `EnrollmentHub`, `ManualOverride`, `StudentManagement`, `ClassManagement`, `AdminManagement`
- **`services/api.js`** — single Axios instance; request interceptor attaches `Authorization: Bearer <token>` from localStorage and auto-redirects to `/signin` on 401
- **`services/auth.js`** — thin wrapper for two localStorage keys: `authToken` (JWT string) and `userData` (serialized user object); `App.jsx` listens to `window.storage` events for cross-tab logout

### Backend Django apps (`config/urls.py` routes into each)
Both `/api/` and `/api/v1/` prefixes are registered and route to the same app routers, allowing a future versioning migration path.

| App | Responsibility |
|-----|---------------|
| `admins` | JWT login/logout, password change, account lockout after N failed attempts, audit log |
| `students` | Student CRUD and stored facial embeddings (512-float vectors) |
| `classes` | Class management |
| `enrollments` | Enrollment workflow: `pending` → `enrolled` / `failed` / `expired` |
| `attendance` | Attendance records with confidence scores |
| `ai_engine` | **Experimental** ONNX face pipeline — not used by default, see below |

### Authentication
JWT tokens are issued by `admins/views.py` using PyJWT + bcrypt (BCryptSHA256PasswordHasher). Tokens carry `admin_id` and `jti` claims; role and level are resolved from the `Admin` table at validation time. Logout immediately blacklists the token by `jti`.

Token blacklist check order (in `admins/authentication.py`):
1. Redis cache lookup (fast path)
2. PostgreSQL `TokenBlacklist` table fallback if Redis is unavailable

### Multi-tenancy
Every model has a `tenant_id` UUID field (not a FK). All queries must be scoped by tenant. Each Admin account creates its own tenant namespace via `create_admin.py`.

### Face recognition — two backends
Selected by `FACE_BACKEND`; the abstraction lives in `students/backends.py`.

**`deepface` — production baseline (default).** `students/face.py` runs DeepFace
with Facenet512. Weights download automatically and are baked into the image at
build time. Requires TensorFlow (~2.4 GB installed), which dominates image size
and build time.

**`onnx` — experimental.** `ai_engine/face_pipeline.py` runs a two-stage ONNX
pipeline: SCRFD-10GF (`det_10g.onnx`) for detection and 5-point landmarks at
640×640, then ArcFace ResNet50 (`w600k_r50.onnx`) for the embedding.
`face_pipeline.py` manages thread-safe ONNX sessions; `services/embedding_service.py`
is a higher-level wrapper. Kept because ONNX Runtime is ~75 MB against
TensorFlow's ~2.4 GB and runs on ARM — the plausible basis for on-site edge
devices. To enable:

```bash
pip install -r requirements-onnx.txt   # onnxruntime, deliberately not in requirements.txt
# place det_10g.onnx and w600k_r50.onnx in ai_engine/models/ (see its .gitkeep)
FACE_BACKEND=onnx python manage.py runserver 3000
```

**The two are not interchangeable.** Facenet512 and ArcFace embed into different
vector spaces, so comparing a vector from one against the other yields
plausible-looking noise. `StudentEmbedding.backend` records the producer and all
matching filters on it. Changing `FACE_BACKEND` on a populated system means
re-enrolling every student. Group identification (`identify-group`) is
DeepFace-only — the ONNX pipeline returns a single face per image.

Compare them on real photos before switching:

```bash
python scripts/benchmark_face_backends.py path/to/faces --runs 3
```

It reports latency and, more importantly, *separation* — mean same-person
similarity minus mean different-person similarity, computed within each backend.
A fast backend that cannot tell people apart is useless, and a threshold tuned
for Facenet512 will not necessarily suit ArcFace.

### Database conditional logic
`StudentEmbedding.embedding` field switches on the configured database engine:
- **PostgreSQL**: `pgvector.VectorField` with an HNSW index for fast cosine similarity search
- **SQLite (dev fallback)**: JSON array — no native vector operations, slower matching

Switch to PostgreSQL via `DATABASE_URL` env var for production or pgvector-dependent features.

### Database schema highlights
- `Student` — UUID PK, tenant-aware
- `StudentEmbedding` — 512-float embedding with version field; multiple embeddings per student supported
- `StudentAttendance` — confidence score, timestamp, class FK
- `AdminAuditLog` — compliance-focused event log written on every auth event

## Key conventions
- API base URL is configured via `VITE_API_BASE_URL` (defaults to `http://localhost:3000/api`)
- Frontend uses Tailwind utility classes; custom color palette is defined in `tailwind.config.js`
- Django apps follow the standard `models.py / serializers.py / views.py / urls.py` layout
- Face matching uses cosine similarity against stored embeddings; threshold is configurable via env var
- Only `admins/tests.py` has real test coverage; other app test files are empty stubs
