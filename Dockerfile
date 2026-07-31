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

# libglib2.0-0 is required by opencv-headless; libgomp1 by TensorFlow's OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

# Bake DeepFace weights into the image. Without this the first enrolment after
# every deploy downloads ~95 MB inside a request — see the script's docstring.
# Its own layer, so it is not re-fetched when application code changes.
COPY scripts/warm_face_models.py scripts/
RUN python scripts/warm_face_models.py

COPY . .

# React production build from stage 1
COPY --from=frontend /build/dist ./dist

# Normalise CRLF (the repo is developed on Windows) and make executable
RUN sed -i 's/\r$//' start.sh && chmod +x start.sh

EXPOSE 8000

CMD ["./start.sh"]
