#apps/teachers/models.py:

from django.db import models
from django.contrib.auth.models import User

class Docente(models.Model):
    ci = models.CharField(max_length=20, primary_key=True)
    nombre = models.CharField(max_length=50)
    apellido = models.CharField(max_length=50)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20)
    fecha_ingreso = models.DateField()
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'docente'
        verbose_name = 'Docente'
        verbose_name_plural = 'Docentes'
        
    def __str__(self):
        return f"{self.nombre} {self.apellido}"
    
    @property
    def nombre_completo(self):
        return f"{self.nombre} {self.apellido}"

class AsignacionCurso(models.Model):
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    ci_docente = models.ForeignKey(Docente, on_delete=models.CASCADE, db_column='ci_docente')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'asignacion_curso'
        verbose_name = 'Asignación de Curso'
        verbose_name_plural = 'Asignaciones de Curso'
        unique_together = ('codigo_curso', 'codigo_materia')
        
    def __str__(self):
        return f"{self.codigo_materia.nombre} - {self.codigo_curso.nombre} ({self.ci_docente.nombre_completo})"