from django.urls import path, include

urlpatterns = [
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
