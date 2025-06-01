#apps/subjects/serializers.py:

from rest_framework import serializers
from .models import Materia

class MateriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class MateriaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Materia
        fields = ['codigo', 'nombre']
    
    def validate_codigo(self, value):
        if Materia.objects.filter(codigo=value).exists():
            raise serializers.ValidationError("Ya existe una materia con este código")
        return value

class MateriaDetailSerializer(serializers.ModelSerializer):
    docentes_asignados = serializers.SerializerMethodField()
    cursos_asignados = serializers.SerializerMethodField()
    
    class Meta:
        model = Materia
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_docentes_asignados(self, obj):
        """Obtiene los docentes asignados a esta materia"""
        from apps.teachers.models import AsignacionCurso
        asignaciones = AsignacionCurso.objects.filter(
            codigo_materia=obj, 
            is_active=True
        ).select_related('ci_docente')
        
        return [
            {
                'ci': asignacion.ci_docente.ci,
                'nombre_completo': asignacion.ci_docente.nombre_completo,
                'curso': asignacion.codigo_curso.nombre
            } for asignacion in asignaciones
        ]
    
    def get_cursos_asignados(self, obj):
        """Obtiene los cursos donde se dicta esta materia"""
        from apps.teachers.models import AsignacionCurso
        asignaciones = AsignacionCurso.objects.filter(
            codigo_materia=obj, 
            is_active=True
        ).select_related('codigo_curso')
        
        return [
            {
                'codigo': asignacion.codigo_curso.codigo,
                'nombre': asignacion.codigo_curso.nombre,
                'nivel': asignacion.codigo_curso.nivel,
                'paralelo': asignacion.codigo_curso.paralelo,
                'gestion': asignacion.codigo_curso.gestion
            } for asignacion in asignaciones
        ]