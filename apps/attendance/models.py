#apps/attendance/models.py:

from django.db import models

class Asistencia(models.Model):
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    fecha = models.DateField()
    asistio = models.BooleanField()  # True = presente, False = ausente
    observacion = models.CharField(max_length=200, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'asistencia'
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        unique_together = ('codigo_curso', 'codigo_materia', 'ci_estudiante', 'fecha')
        
    def __str__(self):
        estado = "Presente" if self.asistio else "Ausente"
        return f"{self.ci_estudiante.nombre_completo} - {self.fecha} ({estado})"
    
    @classmethod
    def calcular_porcentaje_asistencia(cls, estudiante, materia, curso, fecha_inicio=None, fecha_fin=None):
        """Calcula el porcentaje de asistencia de un estudiante en una materia"""
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
            
        total_clases = queryset.count()
        if total_clases == 0:
            return 0
            
        asistencias = queryset.filter(asistio=True).count()
        return (asistencias / total_clases) * 100