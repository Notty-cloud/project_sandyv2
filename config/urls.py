from django.urls import path, include, re_path
from django.http import JsonResponse, FileResponse
from django.conf import settings
from pathlib import Path


def spa_index(request):
    """Serve the React SPA for any non-API route (handles client-side routing)."""
    index = Path(settings.BASE_DIR) / 'dist' / 'index.html'
    if index.exists():
        return FileResponse(open(index, 'rb'), content_type='text/html')
    return JsonResponse({'detail': 'Frontend not built. Run: npm run build'}, status=404)


def health(request):
    """Unauthenticated liveness probe for the platform healthcheck."""
    return JsonResponse({'status': 'ok'})


urlpatterns = [
    path('health/', health),
    path('favicon.ico', lambda r: JsonResponse({}, status=204)),
    path('api/', include('admins.urls')),
    path('api/', include('students.urls')),
    path('api/', include('classes.urls')),
    path('api/', include('enrollments.urls')),
    path('api/', include('attendance.urls')),
    path('api/v1/', include('admins.urls')),
    path('api/v1/', include('students.urls')),
    path('api/v1/', include('classes.urls')),
    path('api/v1/', include('enrollments.urls')),
    path('api/v1/', include('attendance.urls')),
    # Catch-all: serve React SPA for any non-API path
    re_path(r'^(?!api/).*$', spa_index),
]
