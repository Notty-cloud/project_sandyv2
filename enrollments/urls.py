from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import EnrollmentCreateView, EnrollmentViewSet

router = DefaultRouter()
router.register(r'enrollments', EnrollmentViewSet, basename='enrollment')

urlpatterns = [
	path('enrollment', EnrollmentCreateView.as_view(), name='enrollment-create'),
] + router.urls
