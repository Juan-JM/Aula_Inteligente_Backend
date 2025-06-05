# apps/attendance/serializers.py

from rest_framework import serializers
from .models import Asistencia

class AsistenciaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    asistio_efectivamente = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Asistencia
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class AsistenciaCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Asistencia
        fields = ['codigo_curso', 'codigo_materia', 'ci_estudiante', 'fecha', 'estado', 'observacion']
    
    def validate(self, attrs):
        # Verificar que la fecha no sea futura
        from datetime import date
        if attrs['fecha'] > date.today():
            raise serializers.ValidationError("No se puede registrar asistencia para fechas futuras")
        
        return attrs
    
    def validate_estado(self, value):
        """Validar que el estado sea uno de los valores permitidos"""
        estados_validos = [choice[0] for choice in Asistencia.ESTADO_CHOICES]
        if value not in estados_validos:
            raise serializers.ValidationError(
                f"Estado inválido. Debe ser uno de: {', '.join(estados_validos)}"
            )
        return value

class AsistenciaMasivaSerializer(serializers.Serializer):
    codigo_curso = serializers.CharField()
    codigo_materia = serializers.CharField()
    fecha = serializers.DateField()
    estudiantes = serializers.ListField(
        child=serializers.DictField(child=serializers.CharField())
    )
    
    def validate_estudiantes(self, value):
        """Validar formato de estudiantes"""
        estados_validos = [choice[0] for choice in Asistencia.ESTADO_CHOICES]
        
        for estudiante in value:
            # ✅ CAMBIAR 'ci' POR 'ci_estudiante' para coincidir con el frontend
            if 'ci_estudiante' not in estudiante or 'estado' not in estudiante:
                raise serializers.ValidationError("Cada estudiante debe tener 'ci_estudiante' y 'estado'")
            
            # Validar que el estado sea válido
            if estudiante['estado'] not in ['presente', 'ausente', 'tardanza', 'justificado']:
                raise serializers.ValidationError(f"Estado inválido: {estudiante['estado']}")
        
        return value

class EstadisticasAsistenciaSerializer(serializers.Serializer):
    estudiante = serializers.DictField()
    periodo = serializers.DictField()
    materias = serializers.ListField()
    estadisticas_generales = serializers.DictField()
    porcentaje_asistencia = serializers.DecimalField(max_digits=5, decimal_places=2)

class EstadisticasDetalladasSerializer(serializers.Serializer):
    """Serializer para estadísticas detalladas por estado"""
    total_clases = serializers.IntegerField()
    presente = serializers.IntegerField()
    ausente = serializers.IntegerField()
    tardanza = serializers.IntegerField()
    justificado = serializers.IntegerField()
    porcentaje_asistencia = serializers.DecimalField(max_digits=5, decimal_places=2)