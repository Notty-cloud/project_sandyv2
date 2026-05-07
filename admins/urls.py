from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AdminManagementView, AdminUnlockView, AdminViewSet, AuthLoginView, AuthLogoutView, ChangePasswordView

router = DefaultRouter()
router.register(r'admins', AdminViewSet, basename='admin')

urlpatterns = [
	path('auth/login/', AuthLoginView.as_view(), name='auth-login'),
	path('auth/logout/', AuthLogoutView.as_view(), name='auth-logout'),
	path('auth/change-password/', ChangePasswordView.as_view(), name='auth-change-password'),
	path('admin/', AdminManagementView.as_view(), name='admin-management'),
	path('admin/<uuid:admin_id>/unlock/', AdminUnlockView.as_view(), name='admin-unlock'),
] + router.urls
