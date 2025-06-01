#apps/tutors/serializers.py:

from rest_framework import serializers
from .models import Tutor

class TutorSerializer(serializers.ModelSerializer):
    estudiantes_asignados = serializers.SerializerMethodField()
    
    class Meta:
        model = Tutor
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_estudiantes_asignados(self, obj):
        """Obtiene los estudiantes asignados al tutor"""
        from apps.students.models import TutorEstudiante
        relaciones = TutorEstudiante.objects.filter(
            ci_tutor=obj,
            is_active=True
        ).select_related('ci_estudiante')
        
        return [
            {
                'ci': relacion.ci_estudiante.ci,
                'nombre_completo': relacion.ci_estudiante.nombre_completo,
                'parentesco': relacion.parentesco,
                'email': relacion.ci_estudiante.email,
                'edad': relacion.ci_estudiante.edad
            } for relacion in relaciones
        ]

class TutorCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tutor
        fields = ['ci', 'nombre', 'apellido', 'email', 'telefono']
    
    def validate_ci(self, value):
        if Tutor.objects.filter(ci=value).exists():
            raise serializers.ValidationError("Ya existe un tutor con este CI")
        return value
    
    def validate_email(self, value):
        if Tutor.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un tutor con este email")
        return value

class TutorDetailSerializer(serializers.ModelSerializer):
    estudiantes_detalle = serializers.SerializerMethodField()
    total_estudiantes = serializers.SerializerMethodField()
    
    class Meta:
        model = Tutor
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_estudiantes_detalle(self, obj):
        """Información detallada de los estudiantes del tutor"""
        from apps.students.models import TutorEstudiante, Inscripcion
        relaciones = TutorEstudiante.objects.filter(
            ci_tutor=obj,
            is_active=True
        ).select_related('ci_estudiante')
        
        estudiantes_data = []
        for relacion in relaciones:
            estudiante = relacion.ci_estudiante
            
            # Obtener curso actual
            try:
                inscripcion = Inscripcion.objects.get(
                    ci_estudiante=estudiante,
                    estado='ACTIVO'
                )
                curso_info = {
                    'codigo': inscripcion.codigo_curso.codigo,
                    'nombre': inscripcion.codigo_curso.nombre,
                    'nivel': inscripcion.codigo_curso.nivel,
                    'paralelo': inscripcion.codigo_curso.paralelo
                }
            except Inscripcion.DoesNotExist:
                curso_info = None
            
            estudiantes_data.append({
                'ci': estudiante.ci,
                'nombre_completo': estudiante.nombre_completo,
                'email': estudiante.email,
                'fecha_nacimiento': estudiante.fecha_nacimiento,
                'edad': estudiante.edad,
                'parentesco': relacion.parentesco,
                'curso_actual': curso_info,
                'fecha_relacion': relacion.created_at.date()
            })
        
        return estudiantes_data
    
    def get_total_estudiantes(self, obj):
        from apps.students.models import TutorEstudiante
        return TutorEstudiante.objects.filter(ci_tutor=obj, is_active=True).count()