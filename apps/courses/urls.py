#apps/courses/urls.py:

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'cursos', views.CursoViewSet)
router.register(r'periodos', views.PeriodoViewSet)
router.register(r'campos', views.CampoViewSet)
router.register(r'criterios', views.CriterioViewSet)

urlpatterns = [
    path('', include(router.urls)),
]