# ── Stage 1: build the React frontend ────────────────────────────────────────
FROM node:20-slim AS frontend

WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html vite.config.js tailwind.config.js postcss.config.js ./
COPY src/ ./src/
RUN npm run build


# ── Stage 2: Django app ──────────────────────────────────────────────────────
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# libglib2.0-0 and libgomp1 are required by opencv-headless / onnxruntime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# React production build from stage 1
COPY --from=frontend /build/dist ./dist

EXPOSE 8000

CMD python manage.py collectstatic --noinput && \
    python manage.py migrate --noinput && \
    gunicorn config.wsgi:application \
        --bind 0.0.0.0:${PORT:-8000} \
        --workers 1 \
        --threads 4 \
        --timeout 180 \
        --access-logfile - \
        --error-logfile -
