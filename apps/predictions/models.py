from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal

class CalculoNotaPeriodo(models.Model):
    """Almacena cálculos de notas finales por período y campo"""
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    codigo_periodo = models.ForeignKey('courses.Periodo', on_delete=models.CASCADE, db_column='codigo_periodo')
    codigo_campo = models.ForeignKey('courses.Campo', on_delete=models.CASCADE, db_column='codigo_campo')
    
    # Notas calculadas - CORREGIDO: usar Decimal en validators
    promedio_campo = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    nota_ponderada = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    total_notas_campo = models.IntegerField(default=0)
    
    # Metadatos
    fecha_calculo = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'calculo_nota_periodo'
        verbose_name = 'Cálculo de Nota por Período'
        verbose_name_plural = 'Cálculos de Notas por Período'
        unique_together = ('ci_estudiante', 'codigo_curso', 'codigo_materia', 'codigo_periodo', 'codigo_campo')
        
    def __str__(self):
        return f"{self.ci_estudiante.nombre_completo} - {self.codigo_materia.nombre} - {self.codigo_periodo.nombre} - {self.codigo_campo.nombre}"

class NotaFinalPeriodo(models.Model):
    """Almacena la nota final calculada por período"""
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    codigo_periodo = models.ForeignKey('courses.Periodo', on_delete=models.CASCADE, db_column='codigo_periodo')
    
    nota_final = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    
    # Metadatos
    fecha_calculo = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'nota_final_periodo'
        verbose_name = 'Nota Final por Período'
        verbose_name_plural = 'Notas Finales por Período'
        unique_together = ('ci_estudiante', 'codigo_curso', 'codigo_materia', 'codigo_periodo')
        
    def __str__(self):
        return f"{self.ci_estudiante.nombre_completo} - {self.codigo_materia.nombre} - {self.codigo_periodo.nombre}: {self.nota_final}"

class PrediccionNota(models.Model):
    """Almacena predicciones de notas usando ML"""
    ci_estudiante = models.ForeignKey('students.Estudiante', on_delete=models.CASCADE, db_column='ci_estudiante')
    codigo_curso = models.ForeignKey('courses.Curso', on_delete=models.CASCADE, db_column='codigo_curso')
    codigo_materia = models.ForeignKey('subjects.Materia', on_delete=models.CASCADE, db_column='codigo_materia')
    codigo_periodo_objetivo = models.ForeignKey('courses.Periodo', on_delete=models.CASCADE, db_column='codigo_periodo_objetivo')
    
    # Predicciones - CORREGIDO: usar Decimal en validators
    nota_predicha = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))]
    )
    confianza = models.DecimalField(
        max_digits=5, decimal_places=2,
        validators=[MinValueValidator(Decimal('0')), MaxValueValidator(Decimal('100'))],
        help_text="Porcentaje de confianza del modelo"
    )
    
    # Datos del modelo
    algoritmo_usado = models.CharField(max_length=50, default='LinearRegression')
    r2_score = models.DecimalField(max_digits=5, decimal_places=4, null=True, blank=True)
    mse = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    periodos_entrenamiento = models.JSONField(default=list, help_text="Períodos usados para entrenar")
    
    # Metadatos
    fecha_prediccion = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'prediccion_nota'
        verbose_name = 'Predicción de Nota'
        verbose_name_plural = 'Predicciones de Notas'
        unique_together = ('ci_estudiante', 'codigo_curso', 'codigo_materia', 'codigo_periodo_objetivo')
        
    def __str__(self):
        return f"Predicción: {self.ci_estudiante.nombre_completo} - {self.codigo_materia.nombre} - {self.codigo_periodo_objetivo.nombre}: {self.nota_predicha}"

class ModeloEntrenamiento(models.Model):
    """Registro de entrenamientos del modelo ML"""
    nombre_modelo = models.CharField(max_length=100)
    algoritmo = models.CharField(max_length=50)
    parametros = models.JSONField(default=dict)
    
    # Métricas del modelo
    r2_score = models.DecimalField(max_digits=5, decimal_places=4)
    mse = models.DecimalField(max_digits=10, decimal_places=4)
    mae = models.DecimalField(max_digits=10, decimal_places=4)
    
    # Datos de entrenamiento
    total_registros = models.IntegerField()
    registros_entrenamiento = models.IntegerField()
    registros_prueba = models.IntegerField()
    
    # Metadatos
    fecha_entrenamiento = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'modelo_entrenamiento'
        verbose_name = 'Modelo de Entrenamiento'
        verbose_name_plural = 'Modelos de Entrenamiento'
        
    def __str__(self):
        return f"{self.nombre_modelo} - {self.algoritmo} (R²: {self.r2_score})"