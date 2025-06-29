# Generated by Django 5.2.1 on 2025-06-05 09:41

import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('courses', '__first__'),
        ('students', '__first__'),
        ('subjects', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='ModeloEntrenamiento',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nombre_modelo', models.CharField(max_length=100)),
                ('algoritmo', models.CharField(max_length=50)),
                ('parametros', models.JSONField(default=dict)),
                ('r2_score', models.DecimalField(decimal_places=4, max_digits=5)),
                ('mse', models.DecimalField(decimal_places=4, max_digits=10)),
                ('mae', models.DecimalField(decimal_places=4, max_digits=10)),
                ('total_registros', models.IntegerField()),
                ('registros_entrenamiento', models.IntegerField()),
                ('registros_prueba', models.IntegerField()),
                ('fecha_entrenamiento', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Modelo de Entrenamiento',
                'verbose_name_plural': 'Modelos de Entrenamiento',
                'db_table': 'modelo_entrenamiento',
            },
        ),
        migrations.CreateModel(
            name='CalculoNotaPeriodo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('promedio_campo', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('nota_ponderada', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('total_notas_campo', models.IntegerField(default=0)),
                ('fecha_calculo', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('ci_estudiante', models.ForeignKey(db_column='ci_estudiante', on_delete=django.db.models.deletion.CASCADE, to='students.estudiante')),
                ('codigo_campo', models.ForeignKey(db_column='codigo_campo', on_delete=django.db.models.deletion.CASCADE, to='courses.campo')),
                ('codigo_curso', models.ForeignKey(db_column='codigo_curso', on_delete=django.db.models.deletion.CASCADE, to='courses.curso')),
                ('codigo_materia', models.ForeignKey(db_column='codigo_materia', on_delete=django.db.models.deletion.CASCADE, to='subjects.materia')),
                ('codigo_periodo', models.ForeignKey(db_column='codigo_periodo', on_delete=django.db.models.deletion.CASCADE, to='courses.periodo')),
            ],
            options={
                'verbose_name': 'Cálculo de Nota por Período',
                'verbose_name_plural': 'Cálculos de Notas por Período',
                'db_table': 'calculo_nota_periodo',
                'unique_together': {('ci_estudiante', 'codigo_curso', 'codigo_materia', 'codigo_periodo', 'codigo_campo')},
            },
        ),
        migrations.CreateModel(
            name='NotaFinalPeriodo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota_final', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('fecha_calculo', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('ci_estudiante', models.ForeignKey(db_column='ci_estudiante', on_delete=django.db.models.deletion.CASCADE, to='students.estudiante')),
                ('codigo_curso', models.ForeignKey(db_column='codigo_curso', on_delete=django.db.models.deletion.CASCADE, to='courses.curso')),
                ('codigo_materia', models.ForeignKey(db_column='codigo_materia', on_delete=django.db.models.deletion.CASCADE, to='subjects.materia')),
                ('codigo_periodo', models.ForeignKey(db_column='codigo_periodo', on_delete=django.db.models.deletion.CASCADE, to='courses.periodo')),
            ],
            options={
                'verbose_name': 'Nota Final por Período',
                'verbose_name_plural': 'Notas Finales por Período',
                'db_table': 'nota_final_periodo',
                'unique_together': {('ci_estudiante', 'codigo_curso', 'codigo_materia', 'codigo_periodo')},
            },
        ),
        migrations.CreateModel(
            name='PrediccionNota',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota_predicha', models.DecimalField(decimal_places=2, max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('confianza', models.DecimalField(decimal_places=2, help_text='Porcentaje de confianza del modelo', max_digits=5, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ('algoritmo_usado', models.CharField(default='LinearRegression', max_length=50)),
                ('r2_score', models.DecimalField(blank=True, decimal_places=4, max_digits=5, null=True)),
                ('mse', models.DecimalField(blank=True, decimal_places=4, max_digits=10, null=True)),
                ('periodos_entrenamiento', models.JSONField(default=list, help_text='Períodos usados para entrenar')),
                ('fecha_prediccion', models.DateTimeField(auto_now=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_active', models.BooleanField(default=True)),
                ('ci_estudiante', models.ForeignKey(db_column='ci_estudiante', on_delete=django.db.models.deletion.CASCADE, to='students.estudiante')),
                ('codigo_curso', models.ForeignKey(db_column='codigo_curso', on_delete=django.db.models.deletion.CASCADE, to='courses.curso')),
                ('codigo_materia', models.ForeignKey(db_column='codigo_materia', on_delete=django.db.models.deletion.CASCADE, to='subjects.materia')),
                ('codigo_periodo_objetivo', models.ForeignKey(db_column='codigo_periodo_objetivo', on_delete=django.db.models.deletion.CASCADE, to='courses.periodo')),
            ],
            options={
                'verbose_name': 'Predicción de Nota',
                'verbose_name_plural': 'Predicciones de Notas',
                'db_table': 'prediccion_nota',
                'unique_together': {('ci_estudiante', 'codigo_curso', 'codigo_materia', 'codigo_periodo_objetivo')},
            },
        ),
    ]
