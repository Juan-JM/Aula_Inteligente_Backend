#apps/grades/views.py:

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Avg, Count, Q
from .models import ActaNota, Nota
from .serializers import (
    ActaNotaSerializer, NotaSerializer, NotaCreateSerializer, 
    NotaDetailSerializer, RendimientoEstudianteSerializer
)
from apps.authentication.permissions import IsAdministradorOrReadOnly, IsDocenteOrAdministrador

class ActaNotaViewSet(viewsets.ModelViewSet):
    queryset = ActaNota.objects.filter(is_active=True)
    serializer_class = ActaNotaSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'codigo_curso', 'codigo_materia', 'ci_estudiante']
    search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido', 'codigo_materia__nombre']
    ordering = ['codigo_curso', 'codigo_materia', 'ci_estudiante']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Si es docente, solo puede ver actas de sus materias
        if user.groups.filter(name='Docente').exists():
            from apps.teachers.models import Docente, AsignacionCurso
            try:
                docente = Docente.objects.get(usuario=user)
                asignaciones = AsignacionCurso.objects.filter(
                    ci_docente=docente,
                    is_active=True
                ).values('codigo_curso', 'codigo_materia')
                
                # Filtrar por asignaciones del docente
                filters = Q()
                for asignacion in asignaciones:
                    filters |= Q(
                        codigo_curso=asignacion['codigo_curso'],
                        codigo_materia=asignacion['codigo_materia']
                    )
                queryset = queryset.filter(filters)
            except Docente.DoesNotExist:
                queryset = queryset.none()
        
        # Si es estudiante, solo puede ver sus propias actas
        elif user.groups.filter(name='Estudiante').exists():
            from apps.students.models import Estudiante
            try:
                estudiante = Estudiante.objects.get(usuario=user)
                queryset = queryset.filter(ci_estudiante=estudiante)
            except Estudiante.DoesNotExist:
                queryset = queryset.none()
        
        return queryset

class NotaViewSet(viewsets.ModelViewSet):
    queryset = Nota.objects.filter(is_active=True)
    serializer_class = NotaSerializer
    permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = [
        'codigo_curso', 
        'codigo_materia', 
        'ci_estudiante', 
        'id_criterio',
        'id_criterio__codigo_campo',  # Filtro por campo
        'id_criterio__codigo_periodo'  # Filtro por periodo
    ]
    search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido', 'codigo_materia__nombre']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return NotaCreateSerializer
        elif self.action == 'retrieve':
            return NotaDetailSerializer
        return NotaSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Si es docente, solo puede ver notas de sus materias
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
        
        # Si es estudiante, solo puede ver sus propias notas
        elif user.groups.filter(name='Estudiante').exists():
            from apps.students.models import Estudiante
            try:
                estudiante = Estudiante.objects.get(usuario=user)
                queryset = queryset.filter(ci_estudiante=estudiante)
            except Estudiante.DoesNotExist:
                queryset = queryset.none()
        
        return queryset
    
    def get_permissions(self):
        """Solo docentes y administradores pueden crear/modificar notas"""
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
        else:
            permission_classes = [IsAuthenticated]
        return [permission() for permission in permission_classes]
    
    @action(detail=False, methods=['get'])
    def por_estudiante(self, request):
        """Obtener notas agrupadas por estudiante"""
        ci_estudiante = request.query_params.get('ci_estudiante')
        codigo_curso = request.query_params.get('codigo_curso')
        
        if not ci_estudiante:
            return Response(
                {'error': 'ci_estudiante es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(ci_estudiante=ci_estudiante)
        if codigo_curso:
            queryset = queryset.filter(codigo_curso=codigo_curso)
        
        # Agrupar por materia
        materias_data = {}
        for nota in queryset.select_related('codigo_materia', 'id_criterio'):
            materia_nombre = nota.id_criterio.descripcion
            if materia_nombre not in materias_data:
                materias_data[materia_nombre] = {
                    'materia': materia_nombre,
                    'notas': []
                }
            
            materias_data[materia_nombre]['notas'].append({
                'criterio': nota.id_criterio.descripcion,
                'nota': float(nota.nota),
                'fecha': nota.created_at.date(),
                'observaciones': nota.observaciones
            })
        
        # Calcular promedios por materia
        for materia_nombre, data in materias_data.items():
            notas_valores = [nota['nota'] for nota in data['notas']]
            data['promedio'] = sum(notas_valores) / len(notas_valores) if notas_valores else 0
            data['total_notas'] = len(notas_valores)
        
        return Response(list(materias_data.values()))
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Obtener estadísticas generales de notas"""
        queryset = self.get_queryset()
        
        # Filtros opcionales
        codigo_curso = request.query_params.get('codigo_curso')
        codigo_materia = request.query_params.get('codigo_materia')
        
        if codigo_curso:
            queryset = queryset.filter(codigo_curso=codigo_curso)
        if codigo_materia:
            queryset = queryset.filter(codigo_materia=codigo_materia)
        
        stats = queryset.aggregate(
            promedio_general=Avg('nota'),
            total_notas=Count('nota'),
            notas_aprobadas=Count('nota', filter=Q(nota__gte=51)),
            notas_reprobadas=Count('nota', filter=Q(nota__lt=51))
        )
        
        porcentaje_aprobacion = 0
        if stats['total_notas'] > 0:
            porcentaje_aprobacion = (stats['notas_aprobadas'] / stats['total_notas']) * 100
        
        return Response({
            'promedio_general': round(stats['promedio_general'] or 0, 2),
            'total_notas': stats['total_notas'],
            'notas_aprobadas': stats['notas_aprobadas'],
            'notas_reprobadas': stats['notas_reprobadas'],
            'porcentaje_aprobacion': round(porcentaje_aprobacion, 2)
        })
    
    @action(detail=False, methods=['post'])
    def registro_masivo(self, request):
        """Registrar notas en lote"""
        if not request.user.groups.filter(name__in=['Docente', 'Administrador']).exists():
            return Response(
                {'error': 'No tiene permisos para registrar notas'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        notas_data = request.data.get('notas', [])
        if not notas_data:
            return Response(
                {'error': 'Debe proporcionar al menos una nota'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        resultados = []
        errores = []
        for i, nota_data in enumerate(notas_data):
            try:
                # Validar datos requeridos
                if not all(key in nota_data for key in ['ci_estudiante', 'codigo_curso', 'codigo_materia', 'id_criterio', 'nota']):
                    errores.append({
                        'indice': i,
                        'error': 'Faltan campos requeridos: ci_estudiante, codigo_curso, codigo_materia, id_criterio, nota'
                    })
                    continue
                
                # Crear serializer con los datos
                serializer = NotaCreateSerializer(data=nota_data)
                if serializer.is_valid():
                    # Verificar permisos del docente para esta materia/curso
                    if request.user.groups.filter(name='Docente').exists():
                        from apps.teachers.models import Docente, AsignacionCurso
                        try:
                            docente = Docente.objects.get(usuario=request.user)
                            asignacion = AsignacionCurso.objects.filter(
                                ci_docente=docente,
                                codigo_curso=nota_data['codigo_curso'],
                                codigo_materia=nota_data['codigo_materia'],
                                is_active=True
                            ).exists()
                            
                            if not asignacion:
                                errores.append({
                                    'indice': i,
                                    'error': 'No tiene permisos para registrar notas en esta materia/curso'
                                })
                                continue
                        except Docente.DoesNotExist:
                            errores.append({
                                'indice': i,
                                'error': 'Docente no encontrado'
                            })
                            continue
                    
                    # Guardar la nota
                    nota = serializer.save()
                    resultados.append({
                        'indice': i,
                        'id': nota.id,
                        'mensaje': 'Nota registrada exitosamente'
                    })
                else:
                    errores.append({
                        'indice': i,
                        'error': serializer.errors
                    })
                    
            except Exception as e:
                errores.append({
                    'indice': i,
                    'error': str(e)
                })
        
        return Response({
            'mensaje': f'Procesadas {len(notas_data)} notas',
            'exitosas': len(resultados),
            'errores': len(errores),
            'resultados': resultados,
            'errores_detalle': errores
        }, status=status.HTTP_200_OK if resultados else status.HTTP_400_BAD_REQUEST)