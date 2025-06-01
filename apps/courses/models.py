#apps/courses/models.py:
from django.db import models

class Curso(models.Model):
    codigo = models.CharField(max_length=10, primary_key=True)
    nombre = models.CharField(max_length=50)
    nivel = models.CharField(max_length=50)
    paralelo = models.CharField(max_length=1)
    gestion = models.SmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'curso'
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        
    def __str__(self):
        return f"{self.nivel} {self.paralelo} - {self.gestion}"

class Periodo(models.Model):
    codigo = models.CharField(max_length=10, primary_key=True)
    nombre = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'periodo'
        verbose_name = 'Período'
        verbose_name_plural = 'Períodos'
        
    def __str__(self):
        return self.nombre

class Campo(models.Model):
    codigo = models.CharField(max_length=10, primary_key=True)
    nombre = models.CharField(max_length=50)
    valor = models.SmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'campo'
        verbose_name = 'Campo'
        verbose_name_plural = 'Campos'
        
    def __str__(self):
        return self.nombre

class Criterio(models.Model):
    codigo = models.CharField(max_length=100, primary_key=True)
    descripcion = models.CharField(max_length=100)
    codigo_campo = models.ForeignKey(Campo, on_delete=models.CASCADE, db_column='codigo_campo')
    codigo_periodo = models.ForeignKey(Periodo, on_delete=models.CASCADE, db_column='codigo_periodo')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'criterio'
        verbose_name = 'Criterio'
        verbose_name_plural = 'Criterios'
        
    def __str__(self):
        return self.descripcion