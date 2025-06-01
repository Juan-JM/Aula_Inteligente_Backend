#apps/tutors/views.py:

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .models import Tutor
from .serializers import TutorSerializer, TutorCreateSerializer, TutorDetailSerializer
from apps.authentication.permissions import IsAdministradorOrReadOnly

class TutorViewSet(viewsets.ModelViewSet):
    queryset = Tutor.objects.filter(is_active=True)
    serializer_class = TutorSerializer
    permission_classes = [IsAuthenticated, IsAdministradorOrReadOnly]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    search_fields = ['nombre', 'apellido', 'ci', 'email', 'telefono']
    ordering = ['apellido', 'nombre']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return TutorCreateSerializer
        elif self.action == 'retrieve':
            return TutorDetailSerializer
        return TutorSerializer
    
    @action(detail=True, methods=['post'])
    def asignar_estudiante(self, request, pk=None):
        """Asignar un estudiante al tutor"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden asignar estudiantes a tutores'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        tutor = self.get_object()
        ci_estudiante = request.data.get('ci_estudiante')
        parentesco = request.data.get('parentesco')
        
        if not ci_estudiante or not parentesco:
            return Response(
                {'error': 'ci_estudiante y parentesco son requeridos'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.students.models import Estudiante, TutorEstudiante
        
        try:
            estudiante = Estudiante.objects.get(ci=ci_estudiante)
        except Estudiante.DoesNotExist:
            return Response(
                {'error': 'Estudiante no encontrado'}, 
                status=status.HTTP_404
            )
        
        # Verificar si ya existe la relación activa
        relacion_activa = TutorEstudiante.objects.filter(
            ci_tutor=tutor,
            ci_estudiante=estudiante,
            is_active=True
        ).first()

        if relacion_activa:
            return Response(
                {'error': 'El tutor ya está asignado a este estudiante'}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # Verificar si existe una relación inactiva
        relacion_inactiva = TutorEstudiante.objects.filter(
            ci_tutor=tutor,
            ci_estudiante=estudiante,
            is_active=False
        ).first()

        if relacion_inactiva:
            # Reactivar relación existente y actualizar parentesco
            relacion_inactiva.is_active = True
            relacion_inactiva.parentesco = parentesco
            relacion_inactiva.save()
            relacion = relacion_inactiva
        else:
            # Crear nueva relación
            relacion = TutorEstudiante.objects.create(
                ci_tutor=tutor,
                ci_estudiante=estudiante,
                parentesco=parentesco
            )
            
        from apps.students.serializers import TutorEstudianteSerializer
        return Response(
            TutorEstudianteSerializer(relacion).data, 
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['delete'])
    def desasignar_estudiante(self, request, pk=None):
        """Desasignar un estudiante del tutor"""
        if not request.user.groups.filter(name='Administrador').exists():
            return Response(
                {'error': 'Solo administradores pueden desasignar estudiantes de tutores'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        tutor = self.get_object()
        ci_estudiante = request.data.get('ci_estudiante')
        
        if not ci_estudiante:
            return Response(
                {'error': 'ci_estudiante es requerido'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        from apps.students.models import TutorEstudiante
        
        try:
            relacion = TutorEstudiante.objects.get(
                ci_tutor=tutor,
                ci_estudiante__ci=ci_estudiante,
                is_active=True
            )
            relacion.is_active = False
            relacion.save()
            
            return Response({'message': 'Relación tutor-estudiante desactivada'},
                        status=status.HTTP_200_OK)
        except TutorEstudiante.DoesNotExist:
            return Response(
                {'error': 'Relación tutor-estudiante no encontrada'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['get'])
    def sin_estudiantes(self, request):
        """Obtener tutores que no tienen estudiantes asignados"""
        from apps.students.models import TutorEstudiante
        tutores_con_estudiantes = TutorEstudiante.objects.filter(
            is_active=True
        ).values_list('ci_tutor', flat=True)
        
        tutores_sin_estudiantes = self.get_queryset().exclude(
            ci__in=tutores_con_estudiantes
        )
        
        serializer = self.get_serializer(tutores_sin_estudiantes, many=True)
        return Response(serializer.data)