# apps/attendance/models.py

from django.db import models

class Asistencia(models.Model):
    ESTADO_CHOICES = [
        ('presente', 'Presente'),
        ('ausente', 'Ausente'),
        ('tardanza', 'Tardanza'),
        ('justificado', 'Justificado'),
    ]
    
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    fecha = models.DateField()
    estado = models.CharField(max_length=12, choices=ESTADO_CHOICES, default='ausente')
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
        return f"{self.ci_estudiante.nombre_completo} - {self.fecha} ({self.get_estado_display()})"
    
    @property
    def asistio_efectivamente(self):
        """Devuelve True si el estudiante asistió (presente o tardanza)"""
        return self.estado in ['presente', 'tardanza']
    
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
            
        # Considerar como asistencia efectiva: presente y tardanza
        asistencias_efectivas = queryset.filter(estado__in=['presente', 'tardanza']).count()
        return (asistencias_efectivas / total_clases) * 100
    
    @classmethod
    def obtener_estadisticas_detalladas(cls, estudiante, materia, curso, fecha_inicio=None, fecha_fin=None):
        """Obtiene estadísticas detalladas de asistencia por estado"""
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
        
        total = queryset.count()
        if total == 0:
            return {
                'total_clases': 0,
                'presente': 0,
                'ausente': 0,
                'tardanza': 0,
                'justificado': 0,
                'porcentaje_asistencia': 0
            }
        
        stats = {
            'total_clases': total,
            'presente': queryset.filter(estado='presente').count(),
            'ausente': queryset.filter(estado='ausente').count(),
            'tardanza': queryset.filter(estado='tardanza').count(),
            'justificado': queryset.filter(estado='justificado').count(),
        }
        
        # Calcular porcentaje considerando presente y tardanza como asistencia
        asistencias_efectivas = stats['presente'] + stats['tardanza']
        stats['porcentaje_asistencia'] = (asistencias_efectivas / total) * 100
        
        return stats