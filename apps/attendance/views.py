# apps/attendance/views.py

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count, Q
from django.db import transaction
from datetime import date, timedelta
from .models import Asistencia
from .serializers import (
    AsistenciaSerializer, AsistenciaCreateSerializer, 
    AsistenciaMasivaSerializer, EstadisticasAsistenciaSerializer,
    EstadisticasDetalladasSerializer
)
from apps.authentication.permissions import IsDocenteOrAdministrador

class AsistenciaViewSet(viewsets.ModelViewSet):
    queryset = Asistencia.objects.filter(is_active=True)
    serializer_class = AsistenciaSerializer
    permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['codigo_curso', 'codigo_materia', 'ci_estudiante', 'fecha', 'estado']
    search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido']
    ordering = ['-fecha', 'codigo_curso', 'ci_estudiante']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AsistenciaCreateSerializer
        elif self.action == 'registro_masivo':
            return AsistenciaMasivaSerializer
        return AsistenciaSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Si es docente, solo puede ver asistencia de sus materias
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
        
        # Si es estudiante, solo puede ver su propia asistencia
        elif user.groups.filter(name='Estudiante').exists():
            from apps.students.models import Estudiante
            try:
                estudiante = Estudiante.objects.get(usuario=user)
                queryset = queryset.filter(ci_estudiante=estudiante)
            except Estudiante.DoesNotExist:
                queryset = queryset.none()
        
        return queryset
    
    def get_permissions(self):
        """Solo docentes y administradores pueden crear/modificar asistencia"""
        if self.action in ['create', 'update', 'partial_update', 'destroy', 'registro_masivo']:
            permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['post'])
    def registro_masivo(self, request):
        """Registrar asistencia de múltiples estudiantes"""
        serializer = AsistenciaMasivaSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        data = serializer.validated_data
        
        # Verificar que el docente puede registrar en esta materia-curso
        user = request.user
        if user.groups.filter(name='Docente').exists():
            from apps.teachers.models import Docente, AsignacionCurso
            try:
                docente = Docente.objects.get(usuario=user)
                asignacion = AsignacionCurso.objects.get(
                    ci_docente=docente,
                    codigo_curso__codigo=data['codigo_curso'],
                    codigo_materia__codigo=data['codigo_materia'],
                    is_active=True
                )
            except (Docente.DoesNotExist, AsignacionCurso.DoesNotExist):
                return Response(
                    {'error': 'No tiene permisos para registrar asistencia en esta materia-curso'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Procesar estudiantes
        resultados = []
        errores = []
        
        with transaction.atomic():
            for estudiante_data in data['estudiantes']:
                try:
                    from apps.students.models import Estudiante
                    from apps.courses.models import Curso
                    from apps.subjects.models import Materia
                    
                    # ✅ CORREGIR: usar 'ci_estudiante' en lugar de 'ci'
                    estudiante = Estudiante.objects.get(ci=estudiante_data['ci_estudiante'])
                    curso = Curso.objects.get(codigo=data['codigo_curso'])
                    materia = Materia.objects.get(codigo=data['codigo_materia'])
                    
                    estado = estudiante_data['estado']
                    # ✅ MANEJAR CORRECTAMENTE LAS OBSERVACIONES NULAS/VACÍAS
                    observacion = estudiante_data.get('observacion', '')
                    if observacion == 'null' or observacion is None:
                        observacion = ''
                
                    # Crear o actualizar asistencia
                    asistencia, created = Asistencia.objects.update_or_create(
                        codigo_curso=curso,
                        codigo_materia=materia,
                        ci_estudiante=estudiante,
                        fecha=data['fecha'],
                        defaults={
                            'estado': estado,
                            'observacion': observacion  
                        }
                    )
                    
                    resultados.append({
                        'ci': estudiante_data['ci_estudiante'],  # ✅ CORREGIR: usar 'ci_estudiante'
                        'nombre': estudiante.nombre_completo,
                        'estado': estado,
                        'estado_display': asistencia.get_estado_display(),
                        'accion': 'creado' if created else 'actualizado'
                    })
                    
                except Exception as e:
                    errores.append({
                        'ci': estudiante_data['ci_estudiante'],  # ✅ CORREGIR: usar 'ci_estudiante'
                        'error': str(e)
                    })
        
        return Response({
            'fecha': data['fecha'],
            'curso': data['codigo_curso'],
            'materia': data['codigo_materia'],
            'total_procesados': len(data['estudiantes']),
            'exitosos': len(resultados),
            'fallidos': len(errores),
            'resultados': resultados,
            'errores': errores
        })
    
    @action(detail=False, methods=['get'])
    def por_estudiante(self, request):
        """Obtener asistencia de un estudiante específico"""
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
        
        # Calcular estadísticas detalladas
        total_clases = queryset.count()
        stats = {
            'total_clases': total_clases,
            'presente': queryset.filter(estado='presente').count(),
            'ausente': queryset.filter(estado='ausente').count(),
            'tardanza': queryset.filter(estado='tardanza').count(),
            'justificado': queryset.filter(estado='justificado').count(),
        }
        
        # Calcular porcentaje de asistencia efectiva (presente + tardanza)
        asistencias_efectivas = stats['presente'] + stats['tardanza']
        porcentaje = (asistencias_efectivas / total_clases * 100) if total_clases > 0 else 0
        stats['porcentaje_asistencia'] = round(porcentaje, 2)
        
        # Agrupar por materia
        materias_data = {}
        for asistencia in queryset.select_related('codigo_materia'):
            materia_nombre = asistencia.codigo_materia.nombre
            if materia_nombre not in materias_data:
                materias_data[materia_nombre] = {
                    'materia': materia_nombre,
                    'registros': [],
                    'estadisticas': {
                        'presente': 0,
                        'ausente': 0,
                        'tardanza': 0,
                        'justificado': 0
                    }
                }
            
            materias_data[materia_nombre]['registros'].append({
                'fecha': asistencia.fecha,
                'estado': asistencia.estado,
                'estado_display': asistencia.get_estado_display(),
                'observacion': asistencia.observacion
            })
            
            # Incrementar contador de estadísticas por materia
            materias_data[materia_nombre]['estadisticas'][asistencia.estado] += 1
        
        # Calcular porcentaje por materia
        for materia_data in materias_data.values():
            stats_materia = materia_data['estadisticas']
            total_materia = sum(stats_materia.values())
            if total_materia > 0:
                asistencias_materia = stats_materia['presente'] + stats_materia['tardanza']
                stats_materia['porcentaje_asistencia'] = round((asistencias_materia / total_materia) * 100, 2)
            else:
                stats_materia['porcentaje_asistencia'] = 0
        
        return Response({
            'estudiante': ci_estudiante,
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'resumen_general': stats,
            'por_materia': list(materias_data.values())
        })
    
    @action(detail=False, methods=['get'])
    def reporte_diario(self, request):
        """Obtener reporte de asistencia de un día específico"""
        fecha = request.query_params.get('fecha', date.today())
        codigo_curso = request.query_params.get('codigo_curso')
        codigo_materia = request.query_params.get('codigo_materia')
        
        queryset = self.get_queryset().filter(fecha=fecha)
        
        if codigo_curso:
            queryset = queryset.filter(codigo_curso=codigo_curso)
        if codigo_materia:
            queryset = queryset.filter(codigo_materia=codigo_materia)
        
        # Estadísticas del día por estado
        stats = queryset.aggregate(
            total_registros=Count('id'),
            presente=Count('id', filter=Q(estado='presente')),
            ausente=Count('id', filter=Q(estado='ausente')),
            tardanza=Count('id', filter=Q(estado='tardanza')),
            justificado=Count('id', filter=Q(estado='justificado'))
        )
        
        # Calcular porcentajes
        if stats['total_registros'] > 0:
            asistencias_efectivas = stats['presente'] + stats['tardanza']
            stats['porcentaje_asistencia'] = round((asistencias_efectivas / stats['total_registros']) * 100, 2)
            stats['porcentaje_presente'] = round((stats['presente'] / stats['total_registros']) * 100, 2)
            stats['porcentaje_ausente'] = round((stats['ausente'] / stats['total_registros']) * 100, 2)
            stats['porcentaje_tardanza'] = round((stats['tardanza'] / stats['total_registros']) * 100, 2)
            stats['porcentaje_justificado'] = round((stats['justificado'] / stats['total_registros']) * 100, 2)
        else:
            stats.update({
                'porcentaje_asistencia': 0,
                'porcentaje_presente': 0,
                'porcentaje_ausente': 0,
                'porcentaje_tardanza': 0,
                'porcentaje_justificado': 0
            })
        
        return Response({
            'fecha': fecha,
            'filtros': {
                'codigo_curso': codigo_curso,
                'codigo_materia': codigo_materia
            },
            'estadisticas': stats,
            'registros': AsistenciaSerializer(queryset, many=True).data
        })
    
    @action(detail=False, methods=['get'])
    def estadisticas_curso(self, request):
        """Obtener estadísticas de asistencia por curso"""
        codigo_curso = request.query_params.get('codigo_curso')
        codigo_materia = request.query_params.get('codigo_materia')
        fecha_inicio = request.query_params.get('fecha_inicio')
        fecha_fin = request.query_params.get('fecha_fin')
        
        if not codigo_curso:
            return Response(
                {'error': 'codigo_curso es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(codigo_curso=codigo_curso)
        
        if codigo_materia:
            queryset = queryset.filter(codigo_materia=codigo_materia)
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
        
        # Estadísticas generales del curso
        stats_generales = queryset.aggregate(
            total_registros=Count('id'),
            presente=Count('id', filter=Q(estado='presente')),
            ausente=Count('id', filter=Q(estado='ausente')),
            tardanza=Count('id', filter=Q(estado='tardanza')),
            justificado=Count('id', filter=Q(estado='justificado'))
        )
        
        # Calcular porcentajes
        if stats_generales['total_registros'] > 0:
            total = stats_generales['total_registros']
            asistencias_efectivas = stats_generales['presente'] + stats_generales['tardanza']
            stats_generales['porcentaje_asistencia'] = round((asistencias_efectivas / total) * 100, 2)
        else:
            stats_generales['porcentaje_asistencia'] = 0
        
        # Estadísticas por estudiante
        estudiantes_stats = []
        estudiantes_ids = queryset.values_list('ci_estudiante', flat=True).distinct()
        
        for estudiante_id in estudiantes_ids:
            estudiante_queryset = queryset.filter(ci_estudiante=estudiante_id)
            estudiante_obj = estudiante_queryset.first().ci_estudiante
            
            estudiante_stats = estudiante_queryset.aggregate(
                total_clases=Count('id'),
                presente=Count('id', filter=Q(estado='presente')),
                ausente=Count('id', filter=Q(estado='ausente')),
                tardanza=Count('id', filter=Q(estado='tardanza')),
                justificado=Count('id', filter=Q(estado='justificado'))
            )
            
            if estudiante_stats['total_clases'] > 0:
                asistencias_efectivas = estudiante_stats['presente'] + estudiante_stats['tardanza']
                porcentaje = (asistencias_efectivas / estudiante_stats['total_clases']) * 100
                estudiante_stats['porcentaje_asistencia'] = round(porcentaje, 2)
            else:
                estudiante_stats['porcentaje_asistencia'] = 0
            
            estudiantes_stats.append({
                'estudiante': {
                    'ci': estudiante_obj.ci,
                    'nombre': estudiante_obj.nombre_completo
                },
                'estadisticas': estudiante_stats
            })
        
        return Response({
            'curso': codigo_curso,
            'materia': codigo_materia,
            'periodo': {
                'fecha_inicio': fecha_inicio,
                'fecha_fin': fecha_fin
            },
            'estadisticas_generales': stats_generales,
            'estudiantes': estudiantes_stats
        })
    
    @action(detail=False, methods=['get'])
    def estados_disponibles(self, request):
        """Obtener lista de estados disponibles para asistencia"""
        return Response({
            'estados': [
                {'valor': choice[0], 'etiqueta': choice[1]} 
                for choice in Asistencia.ESTADO_CHOICES
            ]
        })