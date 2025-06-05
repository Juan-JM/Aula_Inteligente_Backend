#apps/participation/serializers.py:

from rest_framework import serializers
from datetime import date
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
        if attrs['fecha'] > date.today():
            raise serializers.ValidationError("No se puede registrar participación para fechas futuras")
        
        return attrs

class ParticipacionBulkItemSerializer(serializers.Serializer):
    """Serializer para cada item individual en el registro masivo"""
    ci_estudiante = serializers.CharField(max_length=20)
    tipo_participacion = serializers.ChoiceField(choices=Participacion.TIPOS_PARTICIPACION)
    calificacion = serializers.DecimalField(max_digits=3, decimal_places=1, min_value=1.0, max_value=5.0)
    observacion = serializers.CharField(required=False, allow_blank=True)

class ParticipacionBulkCreateSerializer(serializers.Serializer):
    """Serializer para registro masivo de participaciones"""
    codigo_curso = serializers.CharField(max_length=20)
    codigo_materia = serializers.CharField(max_length=20)
    fecha = serializers.DateField()
    participaciones = ParticipacionBulkItemSerializer(many=True)
    
    def validate_fecha(self, value):
        if value > date.today():
            raise serializers.ValidationError("No se puede registrar participación para fechas futuras")
        return value
    
    def validate_participaciones(self, value):
        if not value:
            raise serializers.ValidationError("Debe incluir al menos una participación")
        
        if len(value) > 100:  # Límite razonable
            raise serializers.ValidationError("No se pueden registrar más de 100 participaciones a la vez")
        
        # Verificar que no haya estudiantes duplicados
        estudiantes = [p['ci_estudiante'] for p in value]
        if len(estudiantes) != len(set(estudiantes)):
            raise serializers.ValidationError("No se pueden registrar múltiples participaciones para el mismo estudiante")
        
        return value
    
    def validate(self, attrs):
        from apps.courses.models import Curso
        from apps.subjects.models import Materia
        from apps.students.models import Estudiante
        
        # Validar que el curso existe
        try:
            curso = Curso.objects.get(codigo=attrs['codigo_curso'], is_active=True)
        except Curso.DoesNotExist:
            raise serializers.ValidationError("El curso especificado no existe o no está activo")
        
        # Validar que la materia existe
        try:
            materia = Materia.objects.get(codigo=attrs['codigo_materia'], is_active=True)
        except Materia.DoesNotExist:
            raise serializers.ValidationError("La materia especificada no existe o no está activa")
        
        # Validar que todos los estudiantes existen y están inscritos en el curso
        participaciones_validadas = []
        for participacion_data in attrs['participaciones']:
            ci_estudiante = participacion_data['ci_estudiante']
            
            try:
                estudiante = Estudiante.objects.get(ci=ci_estudiante, is_active=True)
            except Estudiante.DoesNotExist:
                raise serializers.ValidationError(f"El estudiante con CI {ci_estudiante} no existe o no está activo")
            
            # Verificar que el estudiante está inscrito en el curso
            from apps.students.models import Inscripcion
            inscripcion_exists = Inscripcion.objects.filter(
                ci_estudiante=estudiante,
                codigo_curso=curso,
                estado='ACTIVO'
            ).exists()
            
            if not inscripcion_exists:
                raise serializers.ValidationError(
                    f"El estudiante {estudiante.nombre_completo} (CI: {ci_estudiante}) no está inscrito en el curso {curso.nombre}"
                )
            
            # Verificar que no existe ya una participación para este estudiante en la misma fecha, materia y tipo
            participacion_existente = Participacion.objects.filter(
                ci_estudiante=estudiante,
                codigo_curso=curso,
                codigo_materia=materia,
                fecha=attrs['fecha'],
                tipo_participacion=participacion_data['tipo_participacion'],
                is_active=True
            ).exists()
            
            if participacion_existente:
                raise serializers.ValidationError(
                    f"Ya existe una participación del tipo '{participacion_data['tipo_participacion']}' "
                    f"para el estudiante {estudiante.nombre_completo} en la fecha {attrs['fecha']}"
                )
            
            # Agregar los objetos validados para crear las participaciones
            participaciones_validadas.append({
                'codigo_curso': curso,
                'codigo_materia': materia,
                'ci_estudiante': estudiante,
                'fecha': attrs['fecha'],
                'tipo_participacion': participacion_data['tipo_participacion'],
                'calificacion': participacion_data['calificacion'],
                'observacion': participacion_data.get('observacion', '')
            })
        
        # Reemplazar los datos validados
        attrs['participaciones'] = participaciones_validadas
        
        return attrs

class EstadisticasParticipacionSerializer(serializers.Serializer):
    estudiante = serializers.DictField()
    periodo = serializers.DictField()
    materias = serializers.ListField()
    promedio_general = serializers.DecimalField(max_digits=3, decimal_places=1)
    total_participaciones = serializers.IntegerField()