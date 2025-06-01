#apps/courses/serializers.py:

from rest_framework import serializers
from .models import Curso, Periodo, Campo, Criterio

class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class CursoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ['codigo', 'nombre', 'nivel', 'paralelo', 'gestion']
    
    def validate_codigo(self, value):
        if Curso.objects.filter(codigo=value).exists():
            raise serializers.ValidationError("Ya existe un curso con este código")
        return value

class PeriodoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Periodo
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class CampoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Campo
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class CriterioSerializer(serializers.ModelSerializer):
    campo_nombre = serializers.CharField(source='codigo_campo.nombre', read_only=True)
    periodo_nombre = serializers.CharField(source='codigo_periodo.nombre', read_only=True)
    
    class Meta:
        model = Criterio
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class CriterioDetailSerializer(serializers.ModelSerializer):
    codigo_campo = CampoSerializer(read_only=True)
    codigo_periodo = PeriodoSerializer(read_only=True)
    
    class Meta:
        model = Criterio
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']