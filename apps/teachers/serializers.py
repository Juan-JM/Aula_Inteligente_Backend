from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Docente, AsignacionCurso

class DocenteSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    materias_asignadas = serializers.SerializerMethodField()
    
    class Meta:
        model = Docente
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'usuario']
    
    def get_materias_asignadas(self, obj):
        """Obtiene las materias asignadas al docente"""
        asignaciones = AsignacionCurso.objects.filter(
            ci_docente=obj, 
            is_active=True
        ).select_related('codigo_materia', 'codigo_curso')
        
        return [
            {
                'materia': asignacion.codigo_materia.nombre,
                'curso': asignacion.codigo_curso.nombre,
                'nivel': asignacion.codigo_curso.nivel,
                'paralelo': asignacion.codigo_curso.paralelo
            } for asignacion in asignaciones
        ]

class DocenteCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Docente
        fields = ['ci', 'nombre', 'apellido', 'email', 'telefono', 'fecha_ingreso']
    
    def validate_ci(self, value):
        if Docente.objects.filter(ci=value).exists():
            raise serializers.ValidationError("Ya existe un docente con este CI")
        return value
    
    def validate_email(self, value):
        if Docente.objects.filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un docente con este email")
        return value
    
    def create(self, validated_data):
        # Crear docente sin usuario (se asigna después)
        docente = Docente.objects.create(**validated_data)
        return docente

class DocenteUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar docente existente"""
    
    class Meta:
        model = Docente
        fields = ['nombre', 'apellido', 'email', 'telefono', 'fecha_ingreso', 'is_active']
    
    def validate_email(self, value):
        # Verificar que no exista otro docente con el mismo email
        docente = self.instance
        if Docente.objects.exclude(ci=docente.ci).filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un docente con este email")
        return value

class AsignarUsuarioDocenteSerializer(serializers.Serializer):
    """Serializer para asignar usuario existente a docente"""
    usuario_id = serializers.IntegerField()
    
    def validate_usuario_id(self, value):
        try:
            user = User.objects.get(id=value)
            # Verificar que el usuario no esté ya asignado a otro docente
            if Docente.objects.filter(usuario=user).exists():
                raise serializers.ValidationError("Este usuario ya está asignado a otro docente")
            # Verificar que el usuario tenga el grupo Docente
            if not user.groups.filter(name='Docente').exists():
                raise serializers.ValidationError("El usuario debe tener el grupo 'Docente'")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado")

class AsignacionCursoSerializer(serializers.ModelSerializer):
    materia_nombre = serializers.CharField(source='codigo_materia.nombre', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    docente_nombre = serializers.CharField(source='ci_docente.nombre_completo', read_only=True)
    
    class Meta:
        model = AsignacionCurso
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class AsignacionCursoCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AsignacionCurso
        fields = ['codigo_curso', 'codigo_materia', 'ci_docente']
    
    def validate(self, attrs):
        # Verificar que no exista una asignación activa para esta materia-curso
        existing = AsignacionCurso.objects.filter(
            codigo_curso=attrs['codigo_curso'],
            codigo_materia=attrs['codigo_materia'],
            is_active=True
        ).exists()
        
        if existing:
            raise serializers.ValidationError(
                "Ya existe una asignación activa para esta materia en este curso"
            )
        
        return attrs

class AsignacionCursoDetailSerializer(serializers.ModelSerializer):
    codigo_materia = serializers.StringRelatedField()
    codigo_curso = serializers.StringRelatedField()
    ci_docente = DocenteSerializer(read_only=True)
    total_estudiantes = serializers.SerializerMethodField()
    
    class Meta:
        model = AsignacionCurso
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_total_estudiantes(self, obj):
        """Obtiene el total de estudiantes en esta asignación"""
        from apps.students.models import Inscripcion
        return Inscripcion.objects.filter(
            codigo_curso=obj.codigo_curso,
            estado='ACTIVO'
        ).count()