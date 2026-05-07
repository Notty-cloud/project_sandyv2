# Facial Recognition Attendance System

A full-stack school attendance system that uses facial recognition to automate student check-ins. Teachers mark attendance by submitting a photo; the AI engine matches it against enrolled embeddings and records the result.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS 3.4, Axios, React Router 6 |
| Backend | Django 6, Django REST Framework 3.17 |
| AI / Face | DeepFace (Facenet512), ONNX Runtime (SCRFD + ArcFace R50) |
| Database | SQLite (development) → PostgreSQL (production) |
| Auth | JWT (PyJWT), bcrypt |

---

## Quick Start

### 1. Create the virtual environment and install Python dependencies
```bash
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Mac / Linux
pip install -r requirements.txt
```

### 2. Configure environment
```bash
cp .env.example .env
```
Edit `.env` — at minimum set `SECRET_KEY` and `JWT_SECRET_KEY` for production. Defaults work for local development.

### 3. Run database migrations
```bash
python manage.py migrate
```

### 4. Create the first Level-3 Admin account
```bash
python create_admin.py
```
Follow the prompts. This account can log in and manage all other accounts via the Admin Management page.

### 5. Install frontend dependencies and start both servers
```bash
# Terminal 1 — Django API (port 3000)
python manage.py runserver 3000

# Terminal 2 — Vite frontend (port 5173)
npm install
npm run dev
```

Open **http://localhost:5173** — you will land on the login page.

---

## Authentication

Login uses a **username** (`admin_name`) and password — not an email address.

Accounts have two access-control fields:

| Field | Values | Meaning |
|---|---|---|
| `role` | `teacher`, `admin` | Category of user |
| `authorization_level` | `1`, `2`, `3` | Power within that role |

Permission tiers used across the system:

| Level | Access |
|---|---|
| 1 (any role) | View students, classes, attendance; mark attendance by face |
| 2+ | Override attendance records |
| 3 (admin only) | Create / edit / delete accounts, unlock locked accounts |

### Admin Management page
Only visible in the sidebar when logged in as a **role=admin, level 3** account. From there you can:
- Create new teacher or admin accounts
- Change a user's role and authorization level
- Activate / deactivate accounts
- Unlock accounts locked after too many failed login attempts

---

## Pages

| Route | Description | Access |
|---|---|---|
| `/signin` | Login page | Public |
| `/dashboard` | Overview and navigation hub | Any authenticated user |
| `/attendance` | View and mark class attendance | Any authenticated user |
| `/enrollment` | Enroll students with face photos | Any authenticated user |
| `/override` | Manually adjust failed AI records | Any authenticated user |
| `/admin-management` | Manage user accounts | Level-3 admin only |

---

## Environment Variables

All variables are in `.env.example`. Key ones:

```
# Backend
SECRET_KEY                  Django secret key (required in production)
JWT_SECRET_KEY              JWT signing key (required in production)
DEBUG                       True (dev) / False (prod)
ALLOWED_HOSTS               Comma-separated hostnames
FRONTEND_ORIGIN             CORS allowed origin (default: http://localhost:5173)

# Auth behaviour
ACCESS_TOKEN_LIFETIME_HOURS Token TTL in hours (default: 8)
LOGIN_LOCKOUT_THRESHOLD     Failed attempts before lockout (default: 5)

# Face recognition
FACE_MATCHING_THRESHOLD     Cosine similarity threshold (default: 0.65)
FACE_QUALITY_THRESHOLD      Minimum detection confidence (default: 0.6)

# Attendance
ATTENDANCE_CUTOFF_HOUR      Late cutoff hour, 24h (default: 7)
ATTENDANCE_CUTOFF_MINUTE    Late cutoff minute (default: 10)

# Frontend
VITE_API_BASE_URL           Backend API base URL (default: http://localhost:3000/api)
```

---

## API Endpoints

All endpoints are available under both `/api/` and `/api/v1/`.

### Authentication
```
POST  /api/auth/login/            { admin_name, password }
POST  /api/auth/logout/
POST  /api/auth/change-password/  { current_password, new_password }
```

### Account Management (level-3 admin only)
```
GET    /api/admins/
POST   /api/admins/               { admin_name, email, password, role, authorization_level, tenant_id }
PATCH  /api/admins/{id}/          { role, authorization_level, is_active }
DELETE /api/admins/{id}/
POST   /api/admin/{id}/unlock/
```

### Students
```
GET    /api/students/
POST   /api/students/
GET    /api/students/{id}/
PUT    /api/students/{id}/
POST   /api/students/{id}/enroll/    multipart: image, academic_year, enrolled_by
POST   /api/students/identify/       multipart: image, tenant_id, threshold
```

### Attendance
```
GET    /api/attendance/
POST   /api/attendance/mark-by-face/ multipart: image, tenant_id, class_id, date, threshold
PATCH  /api/attendance/{id}/override/
POST   /api/attendance/override/
```

### Classes
```
GET  /api/classes/
GET  /api/classes/{id}/
```

### Enrollments
```
GET    /api/enrollments/
GET    /api/enrollments/{id}/
POST   /api/enrollment/
```

---

## Maintenance

### Prune expired token blacklist entries
Run daily via cron or task scheduler:
```bash
python manage.py prune_token_blacklist
```

### Production checklist
- Set `DEBUG=False` in `.env`
- Set strong `SECRET_KEY` and `JWT_SECRET_KEY`
- Set `ALLOWED_HOSTS` to your domain
- Set `FRONTEND_ORIGIN` to your frontend URL
- Switch `DATABASES` in `config/settings.py` to PostgreSQL
- Place ONNX model files in `ai_engine/models/` (`det_10g.onnx`, `w600k_r50.onnx`)

---

© 2026 Cybernations Project
