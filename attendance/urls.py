from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import AttendanceListView, AttendanceOverrideView, AttendanceViewSet

router = DefaultRouter()
router.register(r'attendance', AttendanceViewSet, basename='attendance')

urlpatterns = [
	path('attendance', AttendanceListView.as_view(), name='attendance-list'),
	path('attendance/override', AttendanceOverrideView.as_view(), name='attendance-override'),
] + router.urls
