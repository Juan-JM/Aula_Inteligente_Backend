import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from django.db.models import Avg, Count, Q
from decimal import Decimal
import logging

from apps.grades.models import Nota
from apps.courses.models import Campo, Periodo, Criterio
from .models import CalculoNotaPeriodo, NotaFinalPeriodo, PrediccionNota, ModeloEntrenamiento

logger = logging.getLogger(__name__)

class CalculadoraNotas:
    """Servicio para calcular notas finales por período y campo"""
    
    @staticmethod
    def calcular_notas_periodo(estudiante, curso, materia, periodo):
        """Calcula las notas de un estudiante por campo en un período específico"""
        campos = Campo.objects.filter(is_active=True)
        resultados = []
        
        for campo in campos:
            # Obtener criterios de este campo y período
            criterios = Criterio.objects.filter(
                codigo_campo=campo,
                codigo_periodo=periodo,
                is_active=True
            )
            
            if not criterios.exists():
                continue
            
            # Obtener notas de estos criterios
            notas = Nota.objects.filter(
                ci_estudiante=estudiante,
                codigo_curso=curso,
                codigo_materia=materia,
                codigo_criterio__in=criterios,
                is_active=True
            )
            
            if notas.exists():
                # Calcular promedio del campo
                promedio_campo = notas.aggregate(promedio=Avg('nota'))['promedio']
                promedio_campo = float(promedio_campo) if promedio_campo else 0
                
                # Calcular nota ponderada según el porcentaje del campo
                nota_ponderada = (promedio_campo * campo.valor) / 100
                
                # Guardar o actualizar cálculo
                calculo, created = CalculoNotaPeriodo.objects.update_or_create(
                    ci_estudiante=estudiante,
                    codigo_curso=curso,
                    codigo_materia=materia,
                    codigo_periodo=periodo,
                    codigo_campo=campo,
                    defaults={
                        'promedio_campo': Decimal(str(round(promedio_campo, 2))),
                        'nota_ponderada': Decimal(str(round(nota_ponderada, 2))),
                        'total_notas_campo': notas.count()
                    }
                )
                
                resultados.append({
                    'campo': campo.nombre,
                    'campo_codigo': campo.codigo,
                    'porcentaje_campo': campo.valor,
                    'promedio_campo': round(promedio_campo, 2),
                    'nota_ponderada': round(nota_ponderada, 2),
                    'total_notas': notas.count()
                })
        
        return resultados
    
    @staticmethod
    def calcular_nota_final_periodo(estudiante, curso, materia, periodo):
        """Calcula la nota final de un período sumando notas ponderadas"""
        calculos = CalculoNotaPeriodo.objects.filter(
            ci_estudiante=estudiante,
            codigo_curso=curso,
            codigo_materia=materia,
            codigo_periodo=periodo,
            is_active=True
        )
        
        if not calculos.exists():
            # Calcular primero las notas por campo
            CalculadoraNotas.calcular_notas_periodo(estudiante, curso, materia, periodo)
            calculos = CalculoNotaPeriodo.objects.filter(
                ci_estudiante=estudiante,
                codigo_curso=curso,
                codigo_materia=materia,
                codigo_periodo=periodo,
                is_active=True
            )
        
        # Sumar todas las notas ponderadas
        nota_final = sum(float(calculo.nota_ponderada) for calculo in calculos)
        
        # Guardar o actualizar nota final
        nota_final_obj, created = NotaFinalPeriodo.objects.update_or_create(
            ci_estudiante=estudiante,
            codigo_curso=curso,
            codigo_materia=materia,
            codigo_periodo=periodo,
            defaults={
                'nota_final': Decimal(str(round(nota_final, 2)))
            }
        )
        
        return round(nota_final, 2)

class PredictorML:
    """Servicio de Machine Learning para predicción de notas"""
    
    def __init__(self):
        self.modelo = LinearRegression()
        self.is_trained = False
        self.metricas = {}
    
    def preparar_datos(self, estudiante, curso, materia):
        """Prepara datos históricos para entrenamiento"""
        # Obtener notas finales históricas
        notas_historicas = NotaFinalPeriodo.objects.filter(
            ci_estudiante=estudiante,
            codigo_curso=curso,
            codigo_materia=materia,
            is_active=True
        ).order_by('codigo_periodo__nombre')
        
        if notas_historicas.count() < 2:
            return None, None, []
        
        # Convertir a arrays para ML
        periodos = []
        notas = []
        periodos_info = []
        
        for i, nota_obj in enumerate(notas_historicas):
            periodos.append([i + 1])  # Secuencia temporal
            notas.append(float(nota_obj.nota_final))
            periodos_info.append(nota_obj.codigo_periodo.nombre)
        
        return np.array(periodos), np.array(notas), periodos_info
    
    def entrenar_modelo(self, X, y):
        """Entrena el modelo de regresión lineal"""
        if len(X) < 2:
            raise ValueError("Se necesitan al menos 2 períodos para entrenar")
        
        # Si tenemos pocos datos, usar todos para entrenamiento
        if len(X) <= 3:
            X_train, X_test = X, X
            y_train, y_test = y, y
        else:
            X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=0.2, random_state=42
            )
        
        # Entrenar modelo
        self.modelo.fit(X_train, y_train)
        self.is_trained = True
        
        # Calcular métricas
        y_pred = self.modelo.predict(X_test)
        self.metricas = {
            'r2_score': r2_score(y_test, y_pred),
            'mse': mean_squared_error(y_test, y_pred),
            'mae': mean_absolute_error(y_test, y_pred),
            'total_registros': len(X),
            'registros_entrenamiento': len(X_train),
            'registros_prueba': len(X_test)
        }
        
        return self.metricas
    
    def predecir_siguiente_periodo(self, X, y, estudiante, curso, materia, periodo_objetivo):
        """Predice la nota del siguiente período"""
        if not self.is_trained:
            metricas = self.entrenar_modelo(X, y)
        
        # Predecir siguiente período
        siguiente_periodo_num = len(X) + 1
        prediccion = self.modelo.predict([[siguiente_periodo_num]])[0]
        
        # Calcular confianza basada en R²
        confianza = max(0, min(100, self.metricas['r2_score'] * 100))
        
        # Asegurar que la predicción esté en rango válido
        prediccion = max(0, min(100, prediccion))
        
        # Guardar predicción
        prediccion_obj, created = PrediccionNota.objects.update_or_create(
            ci_estudiante=estudiante,
            codigo_curso=curso,
            codigo_materia=materia,
            codigo_periodo_objetivo=periodo_objetivo,
            defaults={
                'nota_predicha': Decimal(str(round(prediccion, 2))),
                'confianza': Decimal(str(round(confianza, 2))),
                'algoritmo_usado': 'LinearRegression',
                'r2_score': Decimal(str(round(self.metricas['r2_score'], 4))),
                'mse': Decimal(str(round(self.metricas['mse'], 4))),
                'periodos_entrenamiento': [f"Período {i+1}" for i in range(len(X))]
            }
        )
        
        return {
            'prediccion': round(prediccion, 2),
            'confianza': round(confianza, 2),
            'metricas': self.metricas
        }

class ServicioPrediciones:
    """Servicio principal para gestionar predicciones"""
    
    @staticmethod
    def generar_prediccion_estudiante(estudiante, curso, materia, periodo_objetivo):
        """Genera predicción para un estudiante específico"""
        try:
            # Calcular notas históricas primero
            periodos_historicos = Periodo.objects.filter(is_active=True).exclude(
                codigo=periodo_objetivo.codigo
            ).order_by('nombre')
            
            for periodo in periodos_historicos:
                CalculadoraNotas.calcular_nota_final_periodo(
                    estudiante, curso, materia, periodo
                )
            
            # Preparar datos para ML
            predictor = PredictorML()
            X, y, periodos_info = predictor.preparar_datos(estudiante, curso, materia)
            
            if X is None:
                return {
                    'error': 'No hay suficientes datos históricos',
                    'datos_necesarios': 'Se necesitan al menos 2 períodos con notas'
                }
            
            # Generar predicción
            resultado = predictor.predecir_siguiente_periodo(
                X, y, estudiante, curso, materia, periodo_objetivo
            )
            
            return {
                'estudiante': estudiante.nombre_completo,
                'materia': materia.nombre,
                'periodo_objetivo': periodo_objetivo.nombre,
                'periodos_utilizados': periodos_info,
                'prediccion': resultado['prediccion'],
                'confianza': resultado['confianza'],
                'metricas_modelo': resultado['metricas']
            }
            
        except Exception as e:
            logger.error(f"Error generando predicción: {str(e)}")
            return {'error': str(e)}
    
    @staticmethod
    def generar_predicciones_curso(curso, periodo_objetivo):
        """Genera predicciones para todos los estudiantes de un curso"""
        from apps.students.models import Inscripcion
        from apps.teachers.models import AsignacionCurso
        
        # Obtener estudiantes del curso
        inscripciones = Inscripcion.objects.filter(
            codigo_curso=curso,
            estado='ACTIVO'
        ).select_related('ci_estudiante')
        
        # Obtener materias del curso
        asignaciones = AsignacionCurso.objects.filter(
            codigo_curso=curso,
            is_active=True
        ).select_related('codigo_materia')
        
        resultados = []
        
        for inscripcion in inscripciones:
            estudiante = inscripcion.ci_estudiante
            estudiante_resultado = {
                'estudiante': estudiante.nombre_completo,
                'ci': estudiante.ci,
                'materias': []
            }
            
            for asignacion in asignaciones:
                materia = asignacion.codigo_materia
                prediccion = ServicioPrediciones.generar_prediccion_estudiante(
                    estudiante, curso, materia, periodo_objetivo
                )
                
                estudiante_resultado['materias'].append({
                    'materia': materia.nombre,
                    'prediccion': prediccion
                })
            
            resultados.append(estudiante_resultado)
        
        return resultados