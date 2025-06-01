#apps/subjects/views.py:

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Materia
from .serializers import MateriaSerializer, MateriaCreateSerializer, MateriaDetailSerializer
from apps.authentication.permissions import IsAdministradorOrReadOnly

class MateriaViewSet(viewsets.ModelViewSet):
    queryset = Materia.objects.filter(is_active=True)
    serializer_class = MateriaSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'codigo']
    ordering = ['nombre']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return MateriaCreateSerializer
        elif self.action == 'retrieve':
            return MateriaDetailSerializer
        return MateriaSerializer
    
    @action(detail=True, methods=['get'])
    def estudiantes(self, request, pk=None):
        """Obtener estudiantes que cursan esta materia"""
        materia = self.get_object()
        from apps.teachers.models import AsignacionCurso
        from apps.students.models import Inscripcion
        
        # Obtener cursos donde se dicta esta materia
        asignaciones = AsignacionCurso.objects.filter(
            codigo_materia=materia, 
            is_active=True
        ).select_related('codigo_curso')
        
        estudiantes_data = []
        for asignacion in asignaciones:
            # Obtener estudiantes inscritos en cada curso
            inscripciones = Inscripcion.objects.filter(
                codigo_curso=asignacion.codigo_curso,
                estado='ACTIVO'
            ).select_related('ci_estudiante')
            
            for inscripcion in inscripciones:
                estudiante = inscripcion.ci_estudiante
                estudiantes_data.append({
                    'ci': estudiante.ci,
                    'nombre_completo': estudiante.nombre_completo,
                    'email': estudiante.email,
                    'curso': asignacion.codigo_curso.nombre,
                    'docente': asignacion.ci_docente.nombre_completo
                })
        
        return Response(estudiantes_data)
    
    @action(detail=True, methods=['get'])
    def estadisticas(self, request, pk=None):
        """Obtener estadísticas de la materia"""
        materia = self.get_object()
        from apps.grades.models import Nota
        from apps.attendance.models import Asistencia
        from django.db.models import Avg, Count
        
        # Estadísticas de notas
        notas_stats = Nota.objects.filter(
            codigo_materia=materia,
            is_active=True
        ).aggregate(
            promedio_general=Avg('nota'),
            total_notas=Count('nota')
        )
        
        # Estadísticas de asistencia
        asistencia_stats = Asistencia.objects.filter(
            codigo_materia=materia,
            is_active=True
        ).aggregate(
            total_clases=Count('id'),
            asistencias=Count('id', filter=models.Q(asistio=True))
        )
        
        porcentaje_asistencia = 0
        if asistencia_stats['total_clases'] > 0:
            porcentaje_asistencia = (asistencia_stats['asistencias'] / asistencia_stats['total_clases']) * 100
        
        return Response({
            'notas': {
                'promedio_general': round(notas_stats['promedio_general'] or 0, 2),
                'total_notas_registradas': notas_stats['total_notas']
            },
            'asistencia': {
                'porcentaje_asistencia': round(porcentaje_asistencia, 2),
                'total_clases': asistencia_stats['total_clases'],
                'total_asistencias': asistencia_stats['asistencias']
            }
        })