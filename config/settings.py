from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv
import dj_database_url
import os

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

if os.getenv('RAILWAY_ENVIRONMENT'):
    ALLOWED_HOSTS.extend(['.railway.app', '.railway.internal', 'healthcheck.railway.app'])
    CSRF_TRUSTED_ORIGINS = [
        f"https://{h.lstrip('.')}" for h in ALLOWED_HOSTS if not h.startswith('.')
    ]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

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
]

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

# ─── CACHE (Redis) ────────────────────────────────────────────────────────────
REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
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

FACE_MATCHING_THRESHOLD = float(os.getenv('FACE_MATCHING_THRESHOLD', '0.65'))
FACE_QUALITY_THRESHOLD = float(os.getenv('FACE_QUALITY_THRESHOLD', '0.6'))
ATTENDANCE_CUTOFF_HOUR = int(os.getenv('ATTENDANCE_CUTOFF_HOUR', '7'))
ATTENDANCE_CUTOFF_MINUTE = int(os.getenv('ATTENDANCE_CUTOFF_MINUTE', '10'))
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ─── INTERNATIONALISATION ─────────────────────────────────────────────────────
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Manila'
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
