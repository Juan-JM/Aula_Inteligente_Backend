#apps/grades/serializers.py:

from rest_framework import serializers
from django.db.models import Avg
from .models import ActaNota, Nota

class ActaNotaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    promedio_notas = serializers.SerializerMethodField()
    
    class Meta:
        model = ActaNota
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_promedio_notas(self, obj):
        """Calcula el promedio de notas del acta"""
        promedio = Nota.objects.filter(
            codigo_curso=obj.codigo_curso,
            codigo_materia=obj.codigo_materia,
            ci_estudiante=obj.ci_estudiante,
            is_active=True
        ).aggregate(promedio=Avg('nota'))['promedio']
        return round(promedio, 2) if promedio else 0

class NotaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    criterio_descripcion = serializers.CharField(source='id_criterio.descripcion', read_only=True)
    periodo_nombre = serializers.CharField(source='id_criterio.codigo_periodo.nombre', read_only=True)
    
    class Meta:
        model = Nota
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class NotaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Nota
        fields = ['codigo_curso', 'codigo_materia', 'ci_estudiante', 'id_criterio', 'nota', 'observaciones']
    
    def validate(self, attrs):
        # Verificar que existe el acta correspondiente
        try:
            ActaNota.objects.get(
                codigo_curso=attrs['codigo_curso'],
                codigo_materia=attrs['codigo_materia'],
                ci_estudiante=attrs['ci_estudiante'],
                is_active=True
            )
        except ActaNota.DoesNotExist:
            # Crear acta automáticamente si no existe
            ActaNota.objects.create(
                codigo_curso=attrs['codigo_curso'],
                codigo_materia=attrs['codigo_materia'],
                ci_estudiante=attrs['ci_estudiante'],
                estado='EN_CURSO'
            )
        
        return attrs
    
    def validate_nota(self, value):
        if value < 0 or value > 100:
            raise serializers.ValidationError("La nota debe estar entre 0 y 100")
        return value

class NotaDetailSerializer(serializers.ModelSerializer):
    codigo_curso = serializers.StringRelatedField()
    codigo_materia = serializers.StringRelatedField()
    ci_estudiante = serializers.StringRelatedField()
    id_criterio = serializers.StringRelatedField()
    acta_info = serializers.SerializerMethodField()
    
    class Meta:
        model = Nota
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_acta_info(self, obj):
        acta = obj.acta_nota
        if acta:
            return {
                'estado': acta.estado,
                'fecha_creacion': acta.created_at.date()
            }
        return None

class RendimientoEstudianteSerializer(serializers.Serializer):
    """Serializer para mostrar rendimiento completo de un estudiante"""
    estudiante = serializers.DictField()
    curso = serializers.DictField()
    materias = serializers.ListField()
    promedio_general = serializers.DecimalField(max_digits=5, decimal_places=2)
    estado_general = serializers.CharField()