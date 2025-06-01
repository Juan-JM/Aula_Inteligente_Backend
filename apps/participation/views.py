#apps/participation/views.py:

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Avg, Count, Q
from .models import Participacion
from .serializers import (
    ParticipacionSerializer, ParticipacionCreateSerializer, 
    EstadisticasParticipacionSerializer
)
from apps.authentication.permissions import IsDocenteOrAdministrador

class ParticipacionViewSet(viewsets.ModelViewSet):
    queryset = Participacion.objects.filter(is_active=True)
    serializer_class = ParticipacionSerializer
    permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['codigo_curso', 'codigo_materia', 'ci_estudiante', 'tipo_participacion', 'fecha']
    search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido', 'tipo_participacion']
    ordering = ['-fecha', 'ci_estudiante']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ParticipacionCreateSerializer
        return ParticipacionSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Si es docente, solo puede ver participación de sus materias
        if user.groups.filter(name='Docente').exists():
            from apps.teachers.models import Docente, AsignacionCurso
            try:
                docente = Docente.objects.get(usuario=user)
                asignaciones = AsignacionCurso.objects.filter(
                    ci_docente=docente,
                    is_active=True
                ).values('codigo_curso', 'codigo_materia')
                
                filters = Q()
                for asignacion in asignaciones:
                    filters |= Q(
                        codigo_curso=asignacion['codigo_curso'],
                        codigo_materia=asignacion['codigo_materia']
                    )
                queryset = queryset.filter(filters)
            except Docente.DoesNotExist:
                queryset = queryset.none()
        
        # Si es estudiante, solo puede ver su propia participación
        elif user.groups.filter(name='Estudiante').exists():
            from apps.students.models import Estudiante
            try:
                estudiante = Estudiante.objects.get(usuario=user)
                queryset = queryset.filter(ci_estudiante=estudiante)
            except Estudiante.DoesNotExist:
                queryset = queryset.none()
        
        return queryset
    
    def get_permissions(self):
        """Solo docentes y administradores pueden crear/modificar participación"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def por_estudiante(self, request):
        """Obtener participación de un estudiante específico"""
        ci_estudiante = request.query_params.get('ci_estudiante')
        codigo_materia = request.query_params.get('codigo_materia')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        
        if not ci_estudiante:
            return Response(
                {'error': 'ci_estudiante es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(ci_estudiante=ci_estudiante)
        
        if codigo_materia:
            queryset = queryset.filter(codigo_materia=codigo_materia)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        # Calcular estadísticas
        stats = queryset.aggregate(
            promedio_general=Avg('calificacion'),
            total_participaciones=Count('id')
        )
        
        # Estadísticas por tipo de participación
        tipos_stats = queryset.values('tipo_participacion').annotate(
            promedio=Avg('calificacion'),
            total=Count('id')
        ).order_by('-promedio')
        
        # Agrupar por materia
        materias_data = {}
        for participacion in queryset.select_related('codigo_materia'):
            materia_nombre = participacion.codigo_materia.nombre
            if materia_nombre not in materias_data:
                materias_data[materia_nombre] = {
                    'materia': materia_nombre,
                    'participaciones': []
                }
            
            materias_data[materia_nombre]['participaciones'].append({
                'fecha': participacion.fecha,
                'tipo': participacion.tipo_participacion,
                'calificacion': float(participacion.calificacion),
                'observacion': participacion.observacion
            })
        
        # Calcular promedios por materia
        for materia_nombre, data in materias_data.items():
            calificaciones = [p['calificacion'] for p in data['participaciones']]
            data['promedio'] = sum(calificaciones) / len(calificaciones) if calificaciones else 0
            data['total_participaciones'] = len(calificaciones)
        
        return Response({
            'estudiante': ci_estudiante,
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'resumen': {
                'promedio_general': round(stats['promedio_general'] or 0, 1),
                'total_participaciones': stats['total_participaciones'],
                'por_tipo': tipos_stats
            },
            'por_materia': list(materias_data.values())
        })
    
    @action(detail=False, methods=['get'])
    def ranking(self, request):
        """Obtener ranking de estudiantes por participación"""
        codigo_curso = request.query_params.get('codigo_curso')
        codigo_materia = request.query_params.get('codigo_materia')
        
        queryset = self.get_queryset()
        
        if codigo_curso:
            queryset = queryset.filter(codigo_curso=codigo_curso)
        if codigo_materia:
            queryset = queryset.filter(codigo_materia=codigo_materia)
        
        # Agrupar por estudiante y calcular promedios
        ranking = queryset.values(
            'ci_estudiante__ci',
            'ci_estudiante__nombre',
            'ci_estudiante__apellido'
        ).annotate(
            promedio_participacion=Avg('calificacion'),
            total_participaciones=Count('id')
        ).order_by('-promedio_participacion', '-total_participaciones')
        
        # Formatear respuesta
        ranking_data = []
        for i, estudiante in enumerate(ranking, 1):
            ranking_data.append({
                'posicion': i,
                'ci': estudiante['ci_estudiante__ci'],
                'nombre_completo': f"{estudiante['ci_estudiante__nombre']} {estudiante['ci_estudiante__apellido']}",
                'promedio_participacion': round(estudiante['promedio_participacion'], 1),
                'total_participaciones': estudiante['total_participaciones']
            })
        
        return Response({
            'filtros': {
                'codigo_curso': codigo_curso,
                'codigo_materia': codigo_materia
            },
            'total_estudiantes': len(ranking_data),
            'ranking': ranking_data
        })
    
    @action(detail=False, methods=['get'])
    def estadisticas_generales(self, request):
        """Obtener estadísticas generales de participación"""
        queryset = self.get_queryset()
        
        # Filtros opcionales
        codigo_curso = request.query_params.get('codigo_curso')
        codigo_materia = request.query_params.get('codigo_materia')
        
        if codigo_curso:
            queryset = queryset.filter(codigo_curso=codigo_curso)
        if codigo_materia:
            queryset = queryset.filter(codigo_materia=codigo_materia)
        
        # Estadísticas generales
        stats = queryset.aggregate(
            promedio_general=Avg('calificacion'),
            total_participaciones=Count('id'),
            participaciones_excelentes=Count('id', filter=Q(calificacion__gte=4.5)),
            participaciones_buenas=Count('id', filter=Q(calificacion__gte=3.5, calificacion__lt=4.5)),
            participaciones_regulares=Count('id', filter=Q(calificacion__lt=3.5))
        )
        
        # Estadísticas por tipo
        por_tipo = queryset.values('tipo_participacion').annotate(
            promedio=Avg('calificacion'),
            total=Count('id')
        ).order_by('-total')
        
        return Response({
            'estadisticas_generales': {
                'promedio_general': round(stats['promedio_general'] or 0, 1),
                'total_participaciones': stats['total_participaciones'],
                'excelentes': stats['participaciones_excelentes'],
                'buenas': stats['participaciones_buenas'],
                'regulares': stats['participaciones_regulares']
            },
            'por_tipo_participacion': list(por_tipo)
        })