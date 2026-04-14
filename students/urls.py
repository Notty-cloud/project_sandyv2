from rest_framework.routers import DefaultRouter
from .views import StudentViewSet, StudentEmbeddingViewSet

router = DefaultRouter()
router.register(r'students', StudentViewSet, basename='student')
router.register(r'embeddings', StudentEmbeddingViewSet, basename='embedding')

urlpatterns = router.urls
