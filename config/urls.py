from django.urls import path, include
from django.http import JsonResponse


def api_root(request):
    return JsonResponse({'detail': 'API server. Frontend is at http://localhost:5173.'})


urlpatterns = [
    path('', api_root),
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
]
