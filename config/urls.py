from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from admins.jwt import AdminTokenObtainPairView

urlpatterns = [
    path('api/v1/', include('admins.urls')),
    path('api/v1/', include('students.urls')),
    path('api/v1/', include('classes.urls')),
    path('api/v1/', include('enrollments.urls')),
    path('api/v1/', include('attendance.urls')),

    # JWT auth — uses custom serializer to include tenant_id, role, admin_id
    path('api/v1/auth/token/', AdminTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]
