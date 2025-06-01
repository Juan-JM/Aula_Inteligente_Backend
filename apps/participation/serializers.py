#apps/participation/serializers.py:

from rest_framework import serializers
from .models import Participacion

class ParticipacionSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    
    class Meta:
        model = Participacion
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class ParticipacionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Participacion
        fields = ['codigo_curso', 'codigo_materia', 'ci_estudiante', 'fecha', 
                 'tipo_participacion', 'calificacion', 'observacion']
    
    def validate_calificacion(self, value):
        if value < 1.0 or value > 5.0:
            raise serializers.ValidationError("La calificación debe estar entre 1.0 y 5.0")
        return value
    
    def validate(self, attrs):
        # Verificar que la fecha no sea futura
        from datetime import date
        if attrs['fecha'] > date.today():
            raise serializers.ValidationError("No se puede registrar participación para fechas futuras")
        
        return attrs

class EstadisticasParticipacionSerializer(serializers.Serializer):
    estudiante = serializers.DictField()
    periodo = serializers.DictField()
    materias = serializers.ListField()
    promedio_general = serializers.DecimalField(max_digits=3, decimal_places=1)
    total_participaciones = serializers.IntegerField()