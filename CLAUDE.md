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

The ONNX model files (~266 MB total) must be placed in `ai_engine/models/` before the backend can process faces:
- `det_10g.onnx` — SCRFD-10GF face detector
- `w600k_r50.onnx` — ArcFace ResNet50 embedding model

## Architecture

### Request flow
Browser → React SPA (`:5173`) → Axios (with JWT header) → Django REST API (`:3000`) → Django app views → AI Engine (in-process) → ONNX Runtime

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
| `ai_engine` | Face detection (SCRFD-10GF) + embedding (ArcFace ResNet50) |

### Authentication
JWT tokens are issued by `admins/views.py` using PyJWT + bcrypt (BCryptSHA256PasswordHasher). Tokens carry `admin_id` and `jti` claims; role and level are resolved from the `Admin` table at validation time. Logout immediately blacklists the token by `jti`.

Token blacklist check order (in `admins/authentication.py`):
1. Redis cache lookup (fast path)
2. PostgreSQL `TokenBlacklist` table fallback if Redis is unavailable

### Multi-tenancy
Every model has a `tenant_id` UUID field (not a FK). All queries must be scoped by tenant. Each Admin account creates its own tenant namespace via `create_admin.py`.

### AI Engine (`ai_engine/`)
Two-stage ONNX pipeline:
1. **SCRFD-10GF** (`det_10g.onnx`) — detects all faces and 5-point landmarks at 640×640 input
2. **ArcFace ResNet50** (`w600k_r50.onnx`) — generates 512-dim L2-normalized embeddings

`face_pipeline.py` manages thread-safe ONNX sessions. `services/embedding_service.py` is the higher-level interface consumed by Django views.

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
