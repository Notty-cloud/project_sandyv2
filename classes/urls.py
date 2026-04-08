from rest_framework.routers import DefaultRouter
from .views import ClassViewSet

router = DefaultRouter()
router.register(r'classes', ClassViewSet, basename='class')

urlpatterns = router.urls
