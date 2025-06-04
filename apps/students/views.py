#apps/students/views.py:

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from django.db import transaction
from .models import Estudiante, Inscripcion, TutorEstudiante
from django.contrib.auth.models import User
from .serializers import (
    EstudianteSerializer, EstudianteCreateSerializer, EstudianteDetailSerializer,
    InscripcionSerializer, InscripcionCreateSerializer, TutorEstudianteSerializer, 
    EstudianteUpdateSerializer, AsignarUsuarioSerializer
)
from apps.authentication.permissions import IsAdministradorOrReadOnly, IsAdministrador, IsOwnerOrAdministrador

class EstudianteViewSet(viewsets.ModelViewSet):
    queryset = Estudiante.objects.filter(is_active=True)
    serializer_class = EstudianteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'apellido', 'ci', 'email']
    ordering = ['apellido', 'nombre']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return EstudianteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return EstudianteUpdateSerializer
        elif self.action == 'retrieve':
            return EstudianteDetailSerializer
        elif self.action == 'asignar_usuario':
            return AsignarUsuarioSerializer
        return EstudianteSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        user = self.request.user
        
        # Si es estudiante, solo puede ver su propia información
        if user.groups.filter(name='Estudiante').exists():
            try:
                estudiante = Estudiante.objects.get(usuario=user)
                queryset = queryset.filter(ci=estudiante.ci)
            except Estudiante.DoesNotExist:
                queryset = queryset.none()
        
        # Si es docente, puede ver estudiantes de sus cursos
        elif user.groups.filter(name='Docente').exists():
            from apps.teachers.models import Docente, AsignacionCurso
            try:
                docente = Docente.objects.get(usuario=user)
                # Obtener cursos asignados al docente
                asignaciones = AsignacionCurso.objects.filter(
                    ci_docente=docente,
                    is_active=True
                ).values_list('codigo_curso', flat=True)
                
                # Obtener estudiantes inscritos en esos cursos
                inscripciones = Inscripcion.objects.filter(
                    codigo_curso__in=asignaciones,
                    estado='ACTIVO'
                ).values_list('ci_estudiante', flat=True)
                
                queryset = queryset.filter(ci__in=inscripciones)
            except Docente.DoesNotExist:
                queryset = queryset.none()
        
        # Administradores pueden ver todo (no se modifica queryset)
        
        return queryset
    
    def get_permissions(self):
        """Permisos específicos por acción"""
        if self.action == 'create':
            permission_classes = [IsAuthenticated, IsAdministrador]
        elif self.action in ['update', 'partial_update', 'destroy']:
            permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
        else:
            permission_classes = [IsAuthenticated]
        
        return [permission() for permission in permission_classes]
    
    @action(detail=True, methods=['post'])
    def asignar_usuario(self, request, pk=None):
        """Asignar usuario existente a estudiante"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden asignar usuarios'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        estudiante = self.get_object()
        
        if estudiante.usuario:
            return Response(
                {'error': 'El estudiante ya tiene un usuario asignado'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AsignarUsuarioSerializer(data=request.data)
        if serializer.is_valid():
            usuario_id = serializer.validated_data['usuario_id']
            user = User.objects.get(id=usuario_id)
            
            estudiante.usuario = user
            estudiante.save()
            
            return Response({
                'message': f'Usuario {user.username} asignado al estudiante {estudiante.nombre_completo}',
                'estudiante': EstudianteSerializer(estudiante).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def desasignar_usuario(self, request, pk=None):
        """Desasignar usuario de estudiante"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden desasignar usuarios'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        estudiante = self.get_object()
        
        if not estudiante.usuario:
            return Response(
                {'error': 'El estudiante no tiene usuario asignado'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = estudiante.usuario.username
        estudiante.usuario = None
        estudiante.save()
        
        return Response({
            'message': f'Usuario {username} desasignado del estudiante {estudiante.nombre_completo}'
        })
        
    @action(detail=True, methods=['post'])
    def inscribir_curso(self, request, pk=None):
        """Inscribir estudiante en un curso"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden inscribir estudiantes'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        estudiante = self.get_object()
        serializer = InscripcionCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            # Verificar que el estudiante coincida
            if serializer.validated_data['ci_estudiante'] != estudiante:
                return Response(
                    {'error': 'CI de estudiante no coincide'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Cerrar inscripción activa anterior si existe
            Inscripcion.objects.filter(
                ci_estudiante=estudiante,
                estado='ACTIVO'
            ).update(estado='TRASLADADO', fecha_baja=serializer.validated_data['fecha_inscripcion'])
            
            # Crear nueva inscripción
            inscripcion = serializer.save()
            return Response(InscripcionSerializer(inscripcion).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def dar_baja(self, request, pk=None):
        """Dar de baja a un estudiante de su curso actual"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden dar de baja estudiantes'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        estudiante = self.get_object()
        motivo = request.data.get('motivo', '')
        fecha_baja = request.data.get('fecha_baja')
        
        if not fecha_baja:
            from datetime import date
            fecha_baja = date.today()
        
        # Actualizar inscripción activa
        inscripciones_activas = Inscripcion.objects.filter(
            ci_estudiante=estudiante,
            estado='ACTIVO'
        )
        
        if not inscripciones_activas.exists():
            return Response(
                {'error': 'El estudiante no tiene inscripciones activas'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        inscripciones_activas.update(
            estado='RETIRADO',
            fecha_baja=fecha_baja,
            motivo_baja=motivo
        )
        
        return Response({'message': 'Estudiante dado de baja exitosamente'})
    
    @action(detail=True, methods=['get'])
    def rendimiento(self, request, pk=None):
        """Obtener rendimiento académico del estudiante"""
        estudiante = self.get_object()
        
        # Verificar permisos: estudiante solo puede ver su propio rendimiento
        user = request.user
        if user.groups.filter(name='Estudiante').exists():
            if estudiante.usuario != user:
                return Response(
                    {'error': 'No puede ver rendimiento de otros estudiantes'}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        
        from apps.grades.models import Nota
        from apps.attendance.models import Asistencia
        from apps.participation.models import Participacion
        
        # Obtener datos por materia
        rendimiento_por_materia = {}
        
        # Inscripción actual
        try:
            inscripcion_activa = Inscripcion.objects.get(
                ci_estudiante=estudiante,
                estado='ACTIVO'
            )
            curso = inscripcion_activa.codigo_curso
            
            # Obtener materias del curso
            from apps.teachers.models import AsignacionCurso
            asignaciones = AsignacionCurso.objects.filter(
                codigo_curso=curso,
                is_active=True
            ).select_related('codigo_materia')
            
            for asignacion in asignaciones:
                materia = asignacion.codigo_materia
                
                # Notas
                notas = Nota.objects.filter(
                    ci_estudiante=estudiante,
                    codigo_materia=materia,
                    codigo_curso=curso,
                    is_active=True
                ).order_by('created_at')
                
                # Asistencia
                porcentaje_asistencia = Asistencia.calcular_porcentaje_asistencia(
                    estudiante, materia, curso
                )
                
                # Participación
                promedio_participacion = Participacion.calcular_promedio_participacion(
                    estudiante, materia, curso
                )
                
                rendimiento_por_materia[materia.nombre] = {
                    'materia_codigo': materia.codigo,
                    'docente': asignacion.ci_docente.nombre_completo,
                    'notas': [
                        {
                            'criterio': nota.id_criterio.descripcion,
                            'nota': float(nota.nota),
                            'fecha': nota.created_at.date()
                        } for nota in notas
                    ],
                    'promedio_notas': sum(float(nota.nota) for nota in notas) / len(notas) if notas else 0,
                    'porcentaje_asistencia': porcentaje_asistencia,
                    'promedio_participacion': float(promedio_participacion)
                }
            
        except Inscripcion.DoesNotExist:
            return Response({'error': 'Estudiante no tiene inscripción activa'}, status=status.HTTP_404)
        
        return Response({
            'estudiante': EstudianteSerializer(estudiante).data,
            'curso_actual': {
                'codigo': curso.codigo,
                'nombre': curso.nombre,
                'nivel': curso.nivel,
                'paralelo': curso.paralelo,
                'gestion': curso.gestion
            },
            'rendimiento_por_materia': rendimiento_por_materia
        })

class InscripcionViewSet(viewsets.ModelViewSet):
    queryset = Inscripcion.objects.all()
    serializer_class = InscripcionSerializer
    permission_classes = [IsAuthenticated, IsAdministrador]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['estado', 'codigo_curso', 'ci_estudiante']
    search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido', 'codigo_curso__nombre']
    ordering = ['-fecha_inscripcion']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InscripcionCreateSerializer
        return InscripcionSerializer

class TutorEstudianteViewSet(viewsets.ModelViewSet):
    queryset = TutorEstudiante.objects.filter(is_active=True)
    serializer_class = TutorEstudianteSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['parentesco', 'ci_estudiante', 'ci_tutor']
    search_fields = ['ci_estudiante__nombre', 'ci_tutor__nombre']
    ordering = ['ci_estudiante', 'parentesco']

