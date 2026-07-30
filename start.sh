#!/usr/bin/env bash
# Container entrypoint.
#
# collectstatic and migrate are deliberately non-fatal: if either fails the
# process must still bind $PORT, otherwise the platform healthcheck reports a
# bare "service unavailable" and the underlying error is never surfaced in the
# deploy logs. Failures are printed loudly instead.

echo "=== Project Sandy — container start ==="
echo "PORT=${PORT:-8000}"
echo "DEBUG=${DEBUG:-unset}"
echo "DATABASE_URL is $([ -n "$DATABASE_URL" ] && echo SET || echo 'NOT SET — using ephemeral SQLite')"
echo "SECRET_KEY is $([ -n "$SECRET_KEY" ] && echo SET || echo 'NOT SET')"

echo "--- collectstatic ---"
python manage.py collectstatic --noinput || echo "!! collectstatic FAILED (continuing)"

echo "--- migrate ---"
python manage.py migrate --noinput || echo "!! migrate FAILED (continuing)"

echo "--- starting gunicorn on 0.0.0.0:${PORT:-8000} ---"
exec gunicorn config.wsgi:application \
    --bind "0.0.0.0:${PORT:-8000}" \
    --workers 1 \
    --threads 4 \
    --timeout 180 \
    --access-logfile - \
    --error-logfile - \
    --log-level info
