#apps/participation/urls.py:

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'', views.ParticipacionViewSet)

urlpatterns = [
    path('', include(router.urls)),
]