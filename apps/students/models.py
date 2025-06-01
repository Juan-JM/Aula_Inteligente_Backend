#apps/students/models.py:

from django.db import models
from django.contrib.auth.models import User

class Estudiante(models.Model):
    ci = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    fecha_nacimiento = models.DateField()
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'estudiante'
        verbose_name = 'Estudiante'
        verbose_name_plural = 'Estudiantes'
        
    def __str__(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def edad(self):
        from datetime import date
        today = date.today()
        return today.year - self.fecha_nacimiento.year - ((today.month, today.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day))

class Inscripcion(models.Model):
    ESTADOS_CHOICES = [
        ('ACTIVO', 'Activo'),
        ('RETIRADO', 'Retirado'),
        ('TRASLADADO', 'Trasladado'),
        ('SUSPENDIDO', 'Suspendido'),
    ]
    
    id = models.AutoField(primary_key=True)
    ci_estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, db_column='ci_estudiante')
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    fecha_inscripcion = models.DateField()
    fecha_baja = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='ACTIVO')
    motivo_baja = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'inscripcion'
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        unique_together = ('ci_estudiante', 'codigo_curso', 'estado')
        
    def __str__(self):
        return f"{self.ci_estudiante.nombre_completo} - {self.codigo_curso.nombre} ({self.estado})"

class TutorEstudiante(models.Model):
    PARENTESCO_CHOICES = [
        ('PADRE', 'Padre'),
        ('MADRE', 'Madre'),
        ('ABUELO', 'Abuelo'),
        ('ABUELA', 'Abuela'),
        ('TIO', 'Tío'),
        ('TIA', 'Tía'),
        ('HERMANO', 'Hermano'),
        ('HERMANA', 'Hermana'),
        ('TUTOR_LEGAL', 'Tutor Legal'),
        ('OTRO', 'Otro'),
    ]
    
    ci_tutor = models.ForeignKey('tutors.Tutor', on_delete=models.CASCADE, db_column='ci_tutor')
    ci_estudiante = models.ForeignKey(Estudiante, on_delete=models.CASCADE, db_column='ci_estudiante')
    parentesco = models.CharField(max_length=100, choices=PARENTESCO_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'tutor_estudiante'
        verbose_name = 'Relación Tutor-Estudiante'
        verbose_name_plural = 'Relaciones Tutor-Estudiante'
        unique_together = ('ci_tutor', 'ci_estudiante')
        
    def __str__(self):
        return f"{self.ci_tutor.nombre_completo} ({self.parentesco}) - {self.ci_estudiante.nombre_completo}"