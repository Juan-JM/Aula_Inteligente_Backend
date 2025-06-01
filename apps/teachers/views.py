#apps/teachers/views.py:

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Q
from .models import Docente, AsignacionCurso
from django.contrib.auth.models import User

from .serializers import (
    DocenteSerializer, DocenteCreateSerializer, AsignacionCursoSerializer,
    AsignacionCursoCreateSerializer, AsignacionCursoDetailSerializer,
    DocenteUpdateSerializer, AsignarUsuarioDocenteSerializer
)
from apps.authentication.permissions import IsAdministradorOrReadOnly, IsAdministrador

class DocenteViewSet(viewsets.ModelViewSet):
    queryset = Docente.objects.filter(is_active=True)
    serializer_class = DocenteSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'apellido', 'ci', 'email']
    ordering = ['apellido', 'nombre']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DocenteCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return DocenteUpdateSerializer
        elif self.action == 'asignar_usuario':
            return AsignarUsuarioDocenteSerializer
        return DocenteSerializer
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Si es docente, solo puede ver su propia información
        if self.request.user.groups.filter(name='Docente').exists():
            try:
                docente = Docente.objects.get(usuario=self.request.user)
                queryset = queryset.filter(ci=docente.ci)
            except Docente.DoesNotExist:
                queryset = queryset.none()
        
        return queryset
    @action(detail=True, methods=['post'])

    def asignar_usuario(self, request, pk=None):
        """Asignar usuario existente a docente"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden asignar usuarios'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        docente = self.get_object()
        
        if docente.usuario:
            return Response(
                {'error': 'El docente ya tiene un usuario asignado'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AsignarUsuarioDocenteSerializer(data=request.data)
        if serializer.is_valid():
            usuario_id = serializer.validated_data['usuario_id']
            user = User.objects.get(id=usuario_id)
            
            docente.usuario = user
            docente.save()
            
            return Response({
                'message': f'Usuario {user.username} asignado al docente {docente.nombre_completo}',
                'docente': DocenteSerializer(docente).data
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def desasignar_usuario(self, request, pk=None):
        """Desasignar usuario de docente"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden desasignar usuarios'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        docente = self.get_object()
        
        if not docente.usuario:
            return Response(
                {'error': 'El docente no tiene usuario asignado'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = docente.usuario.username
        docente.usuario = None
        docente.save()
        
        return Response({
            'message': f'Usuario {username} desasignado del docente {docente.nombre_completo}'
        })
    
    @action(detail=True, methods=['get'])
    def asignaciones(self, request, pk=None):
        """Obtener asignaciones del docente"""
        docente = self.get_object()
        asignaciones = AsignacionCurso.objects.filter(
            ci_docente=docente,
            is_active=True
        ).select_related('codigo_materia', 'codigo_curso')
        
        serializer = AsignacionCursoDetailSerializer(asignaciones, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def estudiantes(self, request, pk=None):
        """Obtener todos los estudiantes del docente"""
        docente = self.get_object()
        from apps.students.models import Inscripcion
        
        # Obtener asignaciones del docente
        asignaciones = AsignacionCurso.objects.filter(
            ci_docente=docente,
            is_active=True
        ).select_related('codigo_curso', 'codigo_materia')
        
        estudiantes_data = []
        for asignacion in asignaciones:
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
                    'edad': estudiante.edad,
                    'curso': asignacion.codigo_curso.nombre,
                    'materia': asignacion.codigo_materia.nombre
                })
        
        return Response(estudiantes_data)

class AsignacionCursoViewSet(viewsets.ModelViewSet):
    queryset = AsignacionCurso.objects.filter(is_active=True)
    serializer_class = AsignacionCursoSerializer
    permission_classes = [IsAuthenticated, IsAdministrador]  # Solo administradores
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['codigo_curso', 'codigo_materia', 'ci_docente']
    search_fields = ['codigo_materia__nombre', 'codigo_curso__nombre', 'ci_docente__nombre']
    ordering = ['codigo_curso', 'codigo_materia']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return AsignacionCursoCreateSerializer
        elif self.action == 'retrieve':
            return AsignacionCursoDetailSerializer
        return AsignacionCursoSerializer
    
    @action(detail=False, methods=['get'])
    def por_docente(self, request):
        """Obtener asignaciones agrupadas por docente"""
        asignaciones = self.get_queryset().select_related(
            'ci_docente', 'codigo_materia', 'codigo_curso'
        )
        
        docentes_data = {}
        for asignacion in asignaciones:
            docente_ci = asignacion.ci_docente.ci
            if docente_ci not in docentes_data:
                docentes_data[docente_ci] = {
                    'docente': DocenteSerializer(asignacion.ci_docente).data,
                    'asignaciones': []
                }
            
            docentes_data[docente_ci]['asignaciones'].append({
                'id': asignacion.id,
                'materia': asignacion.codigo_materia.nombre,
                'curso': asignacion.codigo_curso.nombre,
                'nivel': asignacion.codigo_curso.nivel,
                'paralelo': asignacion.codigo_curso.paralelo
            })
        
        return Response(list(docentes_data.values()))