from rest_framework import serializers
from .models import CalculoNotaPeriodo, NotaFinalPeriodo, PrediccionNota, ModeloEntrenamiento

class CalculoNotaPeriodoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    periodo_nombre = serializers.CharField(source='codigo_periodo.nombre', read_only=True)
    campo_nombre = serializers.CharField(source='codigo_campo.nombre', read_only=True)
    campo_porcentaje = serializers.IntegerField(source='codigo_campo.valor', read_only=True)
    
    class Meta:
        model = CalculoNotaPeriodo
        fields = '__all__'
        read_only_fields = ['fecha_calculo', 'created_at', 'updated_at']

class NotaFinalPeriodoSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    periodo_nombre = serializers.CharField(source='codigo_periodo.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    
    class Meta:
        model = NotaFinalPeriodo
        fields = '__all__'
        read_only_fields = ['fecha_calculo', 'created_at', 'updated_at']

class PrediccionNotaSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    periodo_objetivo_nombre = serializers.CharField(source='codigo_periodo_objetivo.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    
    class Meta:
        model = PrediccionNota
        fields = '__all__'
        read_only_fields = ['fecha_prediccion', 'created_at', 'updated_at']

class ModeloEntrenamientoSerializer(serializers.ModelSerializer):
    precision_porcentaje = serializers.SerializerMethodField()
    
    class Meta:
        model = ModeloEntrenamiento
        fields = '__all__'
        read_only_fields = ['fecha_entrenamiento']
    
    def get_precision_porcentaje(self, obj):
        return round(float(obj.r2_score) * 100, 2)

class ReporteEstudianteSerializer(serializers.Serializer):
    """Serializer para reportes detallados de estudiante"""
    estudiante = serializers.DictField()
    curso = serializers.DictField()
    materia = serializers.DictField()
    trimestres = serializers.ListField()
    prediccion = serializers.DictField(required=False)
    tendencia = serializers.CharField()
    promedio_historico = serializers.DecimalField(max_digits=5, decimal_places=2)

class ReporteCursoSerializer(serializers.Serializer):
    """Serializer para reportes de curso"""
    curso = serializers.DictField()
    periodo_objetivo = serializers.DictField()
    total_estudiantes = serializers.IntegerField()
    total_materias = serializers.IntegerField()
    estudiantes = serializers.ListField()
    estadisticas_generales = serializers.DictField()

class CalculoDetalladoSerializer(serializers.Serializer):
    """Serializer para cálculos detallados por campo"""
    periodo = serializers.DictField()
    campos = serializers.ListField()
    nota_final = serializers.DecimalField(max_digits=5, decimal_places=2)
    total_campos = serializers.IntegerField()

class ComparativoEstudianteSerializer(serializers.Serializer):
    """Serializer para comparativo histórico"""
    estudiante = serializers.DictField()
    materia = serializers.DictField()
    periodos = serializers.ListField()
    tendencia = serializers.CharField()
    mejora_promedio = serializers.DecimalField(max_digits=5, decimal_places=2)
    prediccion_siguiente = serializers.DictField(required=False)

class EstadisticasModeloSerializer(serializers.Serializer):
    """Serializer para estadísticas del modelo ML"""
    total_predicciones = serializers.IntegerField()
    precision_promedio = serializers.DecimalField(max_digits=5, decimal_places=2)
    confianza_promedio = serializers.DecimalField(max_digits=5, decimal_places=2)
    ultimo_entrenamiento = serializers.DateTimeField()
    algoritmos_usados = serializers.ListField()

class GenerarPrediccionesSerializer(serializers.Serializer):
    """Serializer para generar predicciones masivas"""
    codigo_curso = serializers.CharField()
    codigo_periodo_objetivo = serializers.CharField()
    regenerar_existentes = serializers.BooleanField(default=False)
    
    def validate_codigo_curso(self, value):
        from apps.courses.models import Curso
        try:
            Curso.objects.get(codigo=value, is_active=True)
            return value
        except Curso.DoesNotExist:
            raise serializers.ValidationError("Curso no encontrado")
    
    def validate_codigo_periodo_objetivo(self, value):
        from apps.courses.models import Periodo
        try:
            Periodo.objects.get(codigo=value, is_active=True)
            return value
        except Periodo.DoesNotExist:
            raise serializers.ValidationError("Período no encontrado")