#apps/students/urls.py:

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'estudiantes', views.EstudianteViewSet)
router.register(r'inscripciones', views.InscripcionViewSet)
router.register(r'tutor-estudiante', views.TutorEstudianteViewSet)

urlpatterns = [
    path('', include(router.urls)),
]