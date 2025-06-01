#apps/courses/views.py:

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Curso, Periodo, Campo, Criterio
from .serializers import (
    CursoSerializer, CursoCreateSerializer, PeriodoSerializer, 
    CampoSerializer, CriterioSerializer, CriterioDetailSerializer
)
from apps.authentication.permissions import IsAdministradorOrReadOnly

class CursoViewSet(viewsets.ModelViewSet):
    queryset = Curso.objects.filter(is_active=True)
    serializer_class = CursoSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['nivel', 'gestion', 'paralelo']
    search_fields = ['nombre', 'codigo']
    ordering_fields = ['gestion', 'nivel', 'nombre']
    ordering = ['-gestion', 'nivel', 'paralelo']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return CursoCreateSerializer
        return CursoSerializer
    
    @action(detail=True, methods=['get'])
    def estudiantes(self, request, pk=None):
        """Obtener estudiantes inscritos en un curso"""
        curso = self.get_object()
        from apps.students.models import Inscripcion
        inscripciones = Inscripcion.objects.filter(
            codigo_curso=curso, 
            estado='ACTIVO'
        ).select_related('ci_estudiante')
        
        estudiantes_data = []
        for inscripcion in inscripciones:
            estudiante = inscripcion.ci_estudiante
            estudiantes_data.append({
                'ci': estudiante.ci,
                'nombre_completo': estudiante.nombre_completo,
                'email': estudiante.email,
                'fecha_inscripcion': inscripcion.fecha_inscripcion
            })
        
        return Response(estudiantes_data)

class PeriodoViewSet(viewsets.ModelViewSet):
    queryset = Periodo.objects.filter(is_active=True)
    serializer_class = PeriodoSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'codigo']
    ordering = ['nombre']

class CampoViewSet(viewsets.ModelViewSet):
    queryset = Campo.objects.filter(is_active=True)
    serializer_class = CampoSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'codigo']
    ordering = ['nombre']

class CriterioViewSet(viewsets.ModelViewSet):
    queryset = Criterio.objects.filter(is_active=True)
    serializer_class = CriterioSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['codigo_campo', 'codigo_periodo']
    search_fields = ['descripcion', 'codigo']
    ordering = ['codigo_periodo', 'codigo_campo']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return CriterioDetailSerializer
        return CriterioSerializer