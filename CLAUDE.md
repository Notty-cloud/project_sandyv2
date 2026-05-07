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
python manage.py runserver        # API server at http://localhost:3000
python manage.py migrate          # Apply migrations
python manage.py createsuperuser  # Create admin user
pip install -r requirements.txt   # Install Python dependencies
```

### Environment setup
Copy `.env.example` to `.env` and populate `SECRET_KEY`, `JWT_SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `ACCESS_TOKEN_LIFETIME_HOURS`, and `LOGIN_LOCKOUT_THRESHOLD`.

The ONNX model files (~266 MB total) must be present in `ai_engine/models/` before the backend can process faces.

## Architecture

### Request flow
Browser → React SPA (`:5173`) → Axios (with JWT header) → Django REST API (`:3000`) → Django app views → AI Engine (in-process) → ONNX Runtime

Vite proxies API calls from `:5173` to `:3000` in development (`vite.config.js`).

### Frontend (`src/`)
- **`App.jsx`** — route definitions; all routes except `/` are wrapped in `ProtectedRoute`
- **`pages/`** — five views: `SignIn`, `Dashboard` (nav hub), `AttendanceView`, `EnrollmentHub`, `ManualOverride`
- **`services/api.js`** — single Axios instance with all endpoint definitions; attaches JWT from localStorage via request interceptor
- **`services/auth.js`** — thin wrapper around localStorage for session state

### Backend Django apps (`config/urls.py` routes into each)
| App | Responsibility |
|-----|---------------|
| `admins` | JWT login/logout, password change, account lockout after N failed attempts |
| `students` | Student CRUD and stored facial embeddings (512-float vectors) |
| `classes` | Class management |
| `enrollments` | Enrollment workflow with status transitions |
| `attendance` | Attendance records with confidence scores |
| `ai_engine` | Face detection (SCRFD-10GF) + embedding (ArcFace ResNet50); exposes `face_pipeline.py` and `services/embedding_service.py` |

`config/settings.py` configures SQLite for development; switch to PostgreSQL for production via `DATABASE_URL`.

### AI Engine (`ai_engine/`)
- `face_pipeline.py` — thread-safe ONNX sessions; detects faces with SCRFD-10GF (640×640 input), aligns landmarks, generates 512-dim L2-normalized embeddings with ArcFace ResNet50
- `services/embedding_service.py` — higher-level service consumed by Django views
- Models live in `ai_engine/models/` (not committed to git due to size)

### Authentication
JWT tokens issued by `admins/views.py` using PyJWT + bcrypt. Tokens carry role (`teacher`/`admin`) and authorization level (1–3). All protected endpoints validate the token and check role/level. An audit log is written for every auth event.

### Database schema highlights
- `Student` — UUID PK, tenant-aware
- `StudentEmbedding` — stores the 512-float embedding with a version field
- `StudentAttendance` — confidence score, timestamp, class FK
- `AdminAuditLog` — compliance-focused event log

## Key conventions
- API base URL is configured via `VITE_API_BASE_URL` (defaults to `http://localhost:3000/api`)
- Frontend uses Tailwind utility classes; color palette is defined in `tailwind.config.js`
- Django apps follow the standard `models.py / serializers.py / views.py / urls.py` layout
- Face matching uses cosine similarity against stored embeddings; threshold is configurable
