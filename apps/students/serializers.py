from rest_framework import serializers
from django.contrib.auth.models import User
from django.db import transaction
from .models import Estudiante, Inscripcion, TutorEstudiante

class EstudianteSerializer(serializers.ModelSerializer):
    usuario_username = serializers.CharField(source='usuario.username', read_only=True)
    curso_actual = serializers.SerializerMethodField()
    tutores = serializers.SerializerMethodField()
    
    class Meta:
        model = Estudiante
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'usuario']
    
    def get_curso_actual(self, obj):
        """Obtiene el curso actual del estudiante"""
        try:
            inscripcion_activa = Inscripcion.objects.get(
                ci_estudiante=obj,
                estado='ACTIVO'
            )
            return {
                'codigo': inscripcion_activa.codigo_curso.codigo,
                'nombre': inscripcion_activa.codigo_curso.nombre,
                'nivel': inscripcion_activa.codigo_curso.nivel,
                'paralelo': inscripcion_activa.codigo_curso.paralelo,
                'gestion': inscripcion_activa.codigo_curso.gestion
            }
        except Inscripcion.DoesNotExist:
            return None
    
    def get_tutores(self, obj):
        """Obtiene los tutores del estudiante"""
        relaciones = TutorEstudiante.objects.filter(
            ci_estudiante=obj,
            is_active=True
        ).select_related('ci_tutor')
        
        return [
            {
                'ci': relacion.ci_tutor.ci,
                'nombre_completo': relacion.ci_tutor.nombre_completo,
                'parentesco': relacion.parentesco,
                'telefono': relacion.ci_tutor.telefono,
                'email': relacion.ci_tutor.email
            } for relacion in relaciones
        ]

class EstudianteCreateSerializer(serializers.ModelSerializer):
    # Datos del curso (opcional en creación)
    codigo_curso = serializers.CharField(write_only=True, required=False)
    
    class Meta:
        model = Estudiante
        fields = ['ci', 'nombre', 'apellido', 'email', 'fecha_nacimiento', 'codigo_curso']
    
    def validate_ci(self, value):
        if Estudiante.objects.filter(ci=value).exists():
            raise serializers.ValidationError("Ya existe un estudiante con este CI")
        return value
    
    @transaction.atomic
    def create(self, validated_data):
        # Extraer curso
        codigo_curso = validated_data.pop('codigo_curso', None)
        
        # Crear estudiante sin usuario (se asigna después)
        estudiante = Estudiante.objects.create(**validated_data)
        
        # Inscribir en curso si se proporciona
        if codigo_curso:
            from apps.courses.models import Curso
            from datetime import date
            try:
                curso = Curso.objects.get(codigo=codigo_curso)
                Inscripcion.objects.create(
                    ci_estudiante=estudiante,
                    codigo_curso=curso,
                    fecha_inscripcion=date.today(),
                    estado='ACTIVO'
                )
            except Curso.DoesNotExist:
                pass  # Silently ignore if course doesn't exist
        
        return estudiante

class EstudianteUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar estudiante existente"""
    
    class Meta:
        model = Estudiante
        fields = ['nombre', 'apellido', 'email', 'fecha_nacimiento', 'is_active']
    
    def validate_email(self, value):
        # Verificar que no exista otro estudiante con el mismo email
        estudiante = self.instance
        if Estudiante.objects.exclude(ci=estudiante.ci).filter(email=value).exists():
            raise serializers.ValidationError("Ya existe un estudiante con este email")
        return value

class AsignarUsuarioSerializer(serializers.Serializer):
    """Serializer para asignar usuario existente a estudiante"""
    usuario_id = serializers.IntegerField()
    
    def validate_usuario_id(self, value):
        try:
            user = User.objects.get(id=value)
            # Verificar que el usuario no esté ya asignado a otro estudiante
            if Estudiante.objects.filter(usuario=user).exists():
                raise serializers.ValidationError("Este usuario ya está asignado a otro estudiante")
            # Verificar que el usuario tenga el grupo Estudiante
            if not user.groups.filter(name='Estudiante').exists():
                raise serializers.ValidationError("El usuario debe tener el grupo 'Estudiante'")
            return value
        except User.DoesNotExist:
            raise serializers.ValidationError("Usuario no encontrado")

class InscripcionSerializer(serializers.ModelSerializer):
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    curso_nombre = serializers.CharField(source='codigo_curso.nombre', read_only=True)
    
    class Meta:
        model = Inscripcion
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class InscripcionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inscripcion
        fields = ['ci_estudiante', 'codigo_curso', 'fecha_inscripcion']
    
    def validate(self, attrs):
        # Verificar que el estudiante no esté ya inscrito activamente en otro curso
        inscripcion_activa = Inscripcion.objects.filter(
            ci_estudiante=attrs['ci_estudiante'],
            estado='ACTIVO'
        ).exists()
        
        if inscripcion_activa:
            raise serializers.ValidationError(
                "El estudiante ya tiene una inscripción activa en otro curso"
            )
        
        return attrs

class TutorEstudianteSerializer(serializers.ModelSerializer):
    tutor_nombre = serializers.CharField(source='ci_tutor.nombre_completo', read_only=True)
    estudiante_nombre = serializers.CharField(source='ci_estudiante.nombre_completo', read_only=True)
    tutor_telefono = serializers.CharField(source='ci_tutor.telefono', read_only=True)
    tutor_email = serializers.CharField(source='ci_tutor.email', read_only=True)
    
    class Meta:
        model = TutorEstudiante
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']

class EstudianteDetailSerializer(serializers.ModelSerializer):
    usuario_info = serializers.SerializerMethodField()
    inscripciones = serializers.SerializerMethodField()
    tutores = TutorEstudianteSerializer(source='tutoresponse_estudiante_set', many=True, read_only=True)
    rendimiento_resumen = serializers.SerializerMethodField()
    
    class Meta:
        model = Estudiante
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']
    
    def get_usuario_info(self, obj):
        if obj.usuario:
            return {
                'id': obj.usuario.id,
                'username': obj.usuario.username,
                'is_active': obj.usuario.is_active,
                'last_login': obj.usuario.last_login
            }
        return None
    
    def get_inscripciones(self, obj):
        inscripciones = Inscripcion.objects.filter(ci_estudiante=obj).order_by('-fecha_inscripcion')
        return InscripcionSerializer(inscripciones, many=True).data
    
    def get_rendimiento_resumen(self, obj):
        """Obtiene un resumen del rendimiento del estudiante"""
        from apps.grades.models import Nota
        from apps.attendance.models import Asistencia
        from django.db.models import Avg, Count, Q
        
        # Promedio general de notas
        promedio_notas = Nota.objects.filter(
            ci_estudiante=obj,
            is_active=True
        ).aggregate(promedio=Avg('nota'))['promedio']
        
        # Porcentaje de asistencia
        asistencia_stats = Asistencia.objects.filter(
            ci_estudiante=obj,
            is_active=True
        ).aggregate(
            total=Count('id'),
            presentes=Count('id', filter=Q(asistio=True))
        )
        
        porcentaje_asistencia = 0
        if asistencia_stats['total'] > 0:
            porcentaje_asistencia = (asistencia_stats['presentes'] / asistencia_stats['total']) * 100
        
        return {
            'promedio_general': round(promedio_notas or 0, 2),
            'porcentaje_asistencia': round(porcentaje_asistencia, 2),
            'total_notas': Nota.objects.filter(ci_estudiante=obj, is_active=True).count(),
            'total_clases': asistencia_stats['total']
        }