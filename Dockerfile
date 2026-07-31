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
    PIP_NO_CACHE_DIR=1 \
    # Quieten TensorFlow's informational startup logging so deploy logs stay
    # readable. Also set in students/face.py for local runs. oneDNN is left
    # enabled deliberately — disabling it would silence two more lines at the
    # cost of CPU inference speed.
    TF_CPP_MIN_LOG_LEVEL=2 \
    GLOG_minloglevel=2 \
    AUTOGRAPH_VERBOSITY=0 \
    KMP_WARNINGS=0

# libglib2.0-0 is required by opencv-headless; libgomp1 by TensorFlow's OpenMP runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
        libglib2.0-0 \
        libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt constraints.txt ./
# deepface depends on opencv-python (the GUI build), so pip installs it even
# though requirements.txt asks for opencv-python-headless. That build links
# against X11 (libxcb, libSM, libXext…), which a slim image does not carry, and
# it fails at `import cv2`. Both wheels provide the same cv2 module, so drop the
# GUI one and keep headless — no X11 libraries needed and a smaller image.
# constraints.txt caps both distributions below 5.x; see that file for why.
# --retries/--timeout: the TensorFlow wheel is ~600 MB and a dropped connection
# mid-download fails the whole build; pip's defaults give up too easily.
RUN pip install --retries 10 --timeout 120 -r requirements.txt -c constraints.txt \
    && pip uninstall -y opencv-python opencv-contrib-python \
    && pip install --no-cache-dir --force-reinstall -c constraints.txt opencv-python-headless \
    && python -c "import cv2; \
print('cv2', cv2.__version__); \
assert cv2.__version__.startswith('4.'), 'expected opencv 4.x'; \
assert hasattr(cv2, 'CascadeClassifier'), 'cv2.CascadeClassifier missing — deepface opencv detector would fail'; \
print('cv2 headless + CascadeClassifier OK')"

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
