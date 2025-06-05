from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()

# ViewSets principales
router.register(r'reportes', views.ReportesViewSet, basename='reportes')
router.register(r'predicciones', views.PrediccionesViewSet, basename='predicciones')
router.register(r'calculos', views.CalculosViewSet, basename='calculos')
router.register(r'estadisticas', views.EstadisticasViewSet, basename='estadisticas')

# ViewSets de datos (solo lectura)
router.register(r'datos/calculos-periodo', views.CalculoNotaPeriodoViewSet)
router.register(r'datos/notas-finales', views.NotaFinalPeriodoViewSet)
router.register(r'datos/predicciones-notas', views.PrediccionNotaViewSet)
router.register(r'datos/modelos-entrenamiento', views.ModeloEntrenamientoViewSet)

urlpatterns = [
    path('', include(router.urls)),
]