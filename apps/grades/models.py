#apps/grades/models.py:

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator

class ActaNota(models.Model):
    ESTADOS_CHOICES = [
        ('EN_CURSO', 'En Curso'),
        ('APROBADO', 'Aprobado'),
        ('REPROBADO', 'Reprobado'),
        ('ABANDONADO', 'Abandonado'),
    ]
    
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    estado = models.CharField(max_length=20, choices=ESTADOS_CHOICES, default='EN_CURSO')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'acta_nota'
        verbose_name = 'Acta de Nota'
        verbose_name_plural = 'Actas de Notas'
        unique_together = ('codigo_curso', 'codigo_materia', 'ci_estudiante')
        
    def __str__(self):
        return f"{self.ci_estudiante.nombre_completo} - {self.codigo_materia.nombre} ({self.estado})"

class Nota(models.Model):
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    codigo_criterio = models.ForeignKey('courses.Criterio', on_delete=models.CASCADE, db_column='codigo_criterio')
    nota = models.DecimalField(
        max_digits=5, 
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    observaciones = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'nota'
        verbose_name = 'Nota'
        verbose_name_plural = 'Notas'
        unique_together = ('codigo_curso', 'codigo_materia', 'ci_estudiante', 'codigo_criterio')
        
    def __str__(self):
        return f"{self.ci_estudiante.nombre_completo} - {self.codigo_materia.nombre}: {self.nota}"
    
    @property
    def acta_nota(self):
        """Obtiene el acta correspondiente a esta nota"""
        try:
            return ActaNota.objects.get(
                codigo_curso=self.codigo_curso,
                codigo_materia=self.codigo_materia,
                ci_estudiante=self.ci_estudiante
            )
        except ActaNota.DoesNotExist:
            return None