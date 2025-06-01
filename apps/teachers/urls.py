#apps/teachers/urls.py:

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'docentes', views.DocenteViewSet)
router.register(r'asignaciones', views.AsignacionCursoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]