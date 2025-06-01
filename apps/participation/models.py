#apps/participation/models.py:

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class Participacion(models.Model):
    TIPOS_PARTICIPACION = [
        ('PREGUNTA', 'Pregunta'),
        ('RESPUESTA', 'Respuesta'),
        ('DEBATE', 'Debate'),
        ('EXPOSICION', 'Exposición'),
        ('EJERCICIO', 'Ejercicio en Pizarra'),
        ('TRABAJO_GRUPO', 'Trabajo en Grupo'),
        ('OTRO', 'Otro'),
    ]
    
    id = models.AutoField(primary_key=True)
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    fecha = models.DateField()
    tipo_participacion = models.CharField(max_length=50, choices=TIPOS_PARTICIPACION)
    calificacion = models.DecimalField(
        max_digits=3, 
        decimal_places=1,
        validators=[MinValueValidator(1.0), MaxValueValidator(5.0)]
    )
    observacion = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'participacion'
        verbose_name = 'Participación'
        verbose_name_plural = 'Participaciones'
        
    def __str__(self):
        return f"{self.ci_estudiante.nombre_completo} - {self.tipo_participacion} ({self.calificacion})"
    
    @classmethod
    def calcular_promedio_participacion(cls, estudiante, materia, curso, fecha_inicio=None, fecha_fin=None):
        """Calcula el promedio de participación de un estudiante en una materia"""
        queryset = cls.objects.filter(
            ci_estudiante=estudiante,
            codigo_materia=materia,
            codigo_curso=curso,
            is_active=True
        )
        
        if fecha_inicio:
            queryset = queryset.filter(fecha__gte=fecha_inicio)
        if fecha_fin:
            queryset = queryset.filter(fecha__lte=fecha_fin)
            
        from django.db.models import Avg
        resultado = queryset.aggregate(promedio=Avg('calificacion'))
        return resultado['promedio'] or 0