from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url
import os
import sys

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = os.getenv('DEBUG', 'False') == 'True'

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-build-placeholder')
if not DEBUG and SECRET_KEY == 'django-insecure-build-placeholder':
    import warnings
    warnings.warn('SECRET_KEY is not set — using insecure placeholder. Set SECRET_KEY in production.')

ALLOWED_HOSTS = [h.strip() for h in os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',') if h.strip()]

# Railway injects its own domains; healthcheck probes hit the service on an
# internal host, so trust the platform-provided names as well.
for _var in ('RAILWAY_PUBLIC_DOMAIN', 'RAILWAY_PRIVATE_DOMAIN', 'RAILWAY_STATIC_URL'):
    _domain = os.getenv(_var, '').replace('https://', '').replace('http://', '').strip('/')
    if _domain and _domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(_domain)

# Match any RAILWAY_* var — the specific names differ across platform versions
# (RAILWAY_ENVIRONMENT vs RAILWAY_ENVIRONMENT_NAME), so don't depend on one.
ON_RAILWAY = any(k.startswith('RAILWAY_') for k in os.environ)

if ON_RAILWAY:
    # Railway terminates TLS and probes the container on an internal hostname
    # that is not knowable ahead of time; the platform only routes this
    # project's own traffic here, so host validation adds nothing.
    ALLOWED_HOSTS = ['*']
    CSRF_TRUSTED_ORIGINS = [
        f'https://{d}' for d in (os.getenv('RAILWAY_PUBLIC_DOMAIN', ''),) if d
    ]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# ─── TRANSPORT SECURITY ───────────────────────────────────────────────────────
# Production only: enabling these under DEBUG would redirect local http traffic
# to https and set Secure cookies the dev server cannot deliver.
if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = 'same-origin'

    # Camera access requires a secure context anyway, so plain http is useless
    # to this app. The health endpoint is exempt: the platform probe may arrive
    # without X-Forwarded-Proto, and a 301 there fails the deployment rather
    # than securing anything.
    SECURE_SSL_REDIRECT = os.getenv('SECURE_SSL_REDIRECT', 'True') == 'True'
    SECURE_REDIRECT_EXEMPT = [r'^health/$']

    # HSTS tells browsers to refuse http for this host for the given period,
    # and cannot be revoked early — a browser that cached it will not go back.
    # One hour by default: enough to satisfy the check and to be useful, short
    # enough that a mistake ages out the same day. Raise it deliberately once
    # the deployment is settled. Deliberately no includeSubDomains: on a shared
    # *.up.railway.app domain that would speak for hosts that are not ours.
    SECURE_HSTS_SECONDS = int(os.getenv('SECURE_HSTS_SECONDS', '3600'))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = False
    SECURE_HSTS_PRELOAD = False

    # Both silenced checks concern HSTS scope, and both are refusals rather
    # than omissions. A deployment check that always prints warnings stops
    # being read, so the reasoning lives here instead:
    #
    #   W005 includeSubDomains — the app is on a shared *.up.railway.app
    #     domain. Asserting a policy for every sibling subdomain would speak
    #     for hosts that are not ours. Revisit on a dedicated domain.
    #   W021 preload — submission to the browser preload list is effectively
    #     permanent and needs a long max-age plus includeSubDomains. Not a
    #     commitment to make for a pilot.
    SILENCED_SYSTEM_CHECKS = ['security.W005', 'security.W021']

INSTALLED_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.staticfiles',
    # Third-party
    'corsheaders',
    'rest_framework',
    'django_filters',
    # Local apps
    'admins',
    'students',
    'classes',
    'enrollments',
    'attendance',
    'ai_engine',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    # DRF views are csrf_exempt, so this does not affect the JWT API; it covers
    # the Django-rendered routes and satisfies the deployment check.
    'django.middleware.csrf.CsrfViewMiddleware',
    # Refuse to be framed — the app has a camera permission prompt, and a
    # framed login page is the standard clickjacking setup.
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

X_FRAME_OPTIONS = 'DENY'

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv('FRONTEND_ORIGIN', 'http://localhost:5173').split(',')
    if origin.strip()
]

if DEBUG:
    CORS_ALLOWED_ORIGIN_REGEXES = [r'^http://localhost:\d+$']

ROOT_URLCONF = 'config.urls'

WSGI_APPLICATION = 'config.wsgi.application'

# ─── DATABASE ────────────────────────────────────────────────────────────────
_db_url = os.getenv('DATABASE_URL', '')
DATABASES = {
    'default': (
        dj_database_url.parse(_db_url, conn_max_age=600, conn_health_checks=True)
        if _db_url else
        {'ENGINE': 'django.db.backends.sqlite3', 'NAME': BASE_DIR / 'db.sqlite3'}
    )
}

# HnswIndex (students.StudentEmbedding) requires django.contrib.postgres.
# Added only on PostgreSQL — Django's own docs warn against installing it
# against other backends, and the SQLite path uses a JSONField instead.
if DATABASES['default']['ENGINE'] == 'django.db.backends.postgresql':
    INSTALLED_APPS.append('django.contrib.postgres')

# ─── CACHE (Redis) ────────────────────────────────────────────────────────────
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

# Under `manage.py test`, use an in-process cache instead of Redis.
#
# IGNORE_EXCEPTIONS makes a missing Redis non-fatal, but not free: every cache
# call still opens a socket, and on a machine with nothing listening the
# refusal takes ~2 seconds. The login throttle and token blacklist touch the
# cache on most requests, which put the API suite at roughly 19 seconds per
# test — slow enough that nobody would run it.
_TESTING = 'test' in sys.argv

if _TESTING:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'sandy-tests',
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': REDIS_URL,
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'IGNORE_EXCEPTIONS': True,
            },
            'KEY_PREFIX': 'sandy',
        }
    }

# ─── REST FRAMEWORK ──────────────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'admins.authentication.AdminJWTAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_FILTER_BACKENDS': [
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_THROTTLE_RATES': {
        'login': '5/min',
    },
}

JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', SECRET_KEY)
ACCESS_TOKEN_LIFETIME = timedelta(hours=int(os.getenv('ACCESS_TOKEN_LIFETIME_HOURS', '8')))
LOGIN_LOCKOUT_THRESHOLD = int(os.getenv('LOGIN_LOCKOUT_THRESHOLD', '5'))

# 'deepface' (production baseline) or 'onnx' (experimental — see
# students/backends.py). Embeddings from the two are NOT comparable; changing
# this requires re-enrolling every student.
FACE_BACKEND = os.getenv('FACE_BACKEND', 'deepface')

FACE_MATCHING_THRESHOLD = float(os.getenv('FACE_MATCHING_THRESHOLD', '0.65'))
FACE_QUALITY_THRESHOLD = float(os.getenv('FACE_QUALITY_THRESHOLD', '0.6'))
ATTENDANCE_CUTOFF_HOUR = int(os.getenv('ATTENDANCE_CUTOFF_HOUR', '7'))
ATTENDANCE_CUTOFF_MINUTE = int(os.getenv('ATTENDANCE_CUTOFF_MINUTE', '10'))
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ─── INTERNATIONALISATION ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'

# Attendance status is decided from *local* time: a check-in past
# ATTENDANCE_CUTOFF_HOUR:MINUTE counts as late (see attendance/views.py). That
# makes this setting part of the core feature, not a display preference — with
# the wrong zone every arrival is misclassified. It was 'Asia/Manila', 12 hours
# from Barbados, which marked every on-time student late.
# Override per deployment for schools in another zone.
TIME_ZONE = os.getenv('TIME_ZONE', 'America/Barbados')
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# STATICFILES_STORAGE was removed in Django 5.1 — configure via STORAGES.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

# Serve the React production build at the root URL via WhiteNoise
WHITENOISE_ROOT = BASE_DIR / 'dist'
WHITENOISE_INDEX_FILE = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
            ],
        },
    },
]
