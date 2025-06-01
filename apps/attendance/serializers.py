#apps/attendance/serializers.py:

from rest_framework import serializers
from .models import Asistencia

class AsistenciaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    estado_asistencia = serializers.SerializerMethodField()
    
    class Meta:
        model = Asistencia
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_estado_asistencia(self, obj):
        return "Presente" if obj.asistio else "Ausente"

class AsistenciaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asistencia
        fields = ['codigo_curso', 'codigo_materia', 'ci_estudiante', 'fecha', 'asistio', 'observacion']
    
    def validate(self, attrs):
        # Verificar que la fecha no sea futura
        from datetime import date
        if attrs['fecha'] > date.today():
            raise serializers.ValidationError("No se puede registrar asistencia para fechas futuras")
        
        return attrs

class AsistenciaMasivaSerializer(serializers.Serializer):
    codigo_curso = serializers.CharField()
    codigo_materia = serializers.CharField()
    fecha = serializers.DateField()
    estudiantes = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    
    def validate_estudiantes(self, value):
        """Validar formato de estudiantes"""
        for estudiante in value:
            if 'ci' not in estudiante or 'asistio' not in estudiante:
                raise serializers.ValidationError(
                    "Cada estudiante debe tener 'ci' y 'asistio'"
                )
            if estudiante['asistio'] not in ['true', 'false', True, False]:
                raise serializers.ValidationError(
                    "El campo 'asistio' debe ser true o false"
                )
        return value

class EstadisticasAsistenciaSerializer(serializers.Serializer):
    estudiante = serializers.DictField()
    periodo = serializers.DictField()
    materias = serializers.ListField()
    porcentaje_general = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_clases = serializers.IntegerField()
    total_asistencias = serializers.IntegerField()