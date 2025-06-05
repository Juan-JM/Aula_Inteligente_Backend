from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Avg, Count, Q, Max
from django.db import transaction
from django.utils import timezone  # ✅ AGREGAR ESTE IMPORT
from datetime import timedelta      # ✅ AGREGAR ESTE IMPORT
from .models import CalculoNotaPeriodo, NotaFinalPeriodo, PrediccionNota, ModeloEntrenamiento
from .serializers import (
   CalculoNotaPeriodoSerializer, NotaFinalPeriodoSerializer, PrediccionNotaSerializer,
   ModeloEntrenamientoSerializer, ReporteEstudianteSerializer, ReporteCursoSerializer,
   CalculoDetalladoSerializer, ComparativoEstudianteSerializer, EstadisticasModeloSerializer,
   GenerarPrediccionesSerializer
)
from .services import CalculadoraNotas, ServicioPrediciones
from apps.authentication.permissions import IsDocenteOrAdministrador

class ReportesViewSet(viewsets.GenericViewSet):
   """ViewSet para reportes de rendimiento académico"""
   permission_classes = [IsAuthenticated]
   
   @action(detail=False, methods=['get'], url_path='estudiante/(?P<ci>[^/.]+)')
   def estudiante(self, request, ci=None):
       """Reporte completo de un estudiante"""
       from apps.students.models import Estudiante, Inscripcion
       from apps.teachers.models import AsignacionCurso
       
       try:
           estudiante = Estudiante.objects.get(ci=ci, is_active=True)
       except Estudiante.DoesNotExist:
           return Response({'error': 'Estudiante no encontrado'}, status=status.HTTP_404_NOT_FOUND)
       
       # Verificar permisos
       if not self._tiene_permiso_estudiante(request.user, estudiante):
           return Response({'error': 'Sin permisos para ver este estudiante'}, status=status.HTTP_403_FORBIDDEN)
       
       # Obtener curso actual
       try:
           inscripcion = Inscripcion.objects.get(ci_estudiante=estudiante, estado='ACTIVO')
           curso = inscripcion.codigo_curso
       except Inscripcion.DoesNotExist:
           return Response({'error': 'Estudiante no tiene inscripción activa'}, status=status.HTTP_404_NOT_FOUND)
       
       # Obtener materias del curso
       asignaciones = AsignacionCurso.objects.filter(
           codigo_curso=curso,
           is_active=True
       ).select_related('codigo_materia')
       
       materias_data = []
       for asignacion in asignaciones:
           materia = asignacion.codigo_materia
           
           # Obtener notas finales por trimestre
           notas_finales = NotaFinalPeriodo.objects.filter(
               ci_estudiante=estudiante,
               codigo_curso=curso,
               codigo_materia=materia,
               is_active=True
           ).order_by('codigo_periodo__nombre')
           
           trimestres = []
           for nota_final in notas_finales:
               # Obtener detalles por campo
               calculos = CalculoNotaPeriodo.objects.filter(
                   ci_estudiante=estudiante,
                   codigo_curso=curso,
                   codigo_materia=materia,
                   codigo_periodo=nota_final.codigo_periodo,
                   is_active=True
               ).select_related('codigo_campo')
               
               campos_detalle = []
               for calculo in calculos:
                   campos_detalle.append({
                       'campo': calculo.codigo_campo.nombre,
                       'porcentaje': calculo.codigo_campo.valor,
                       'promedio_campo': float(calculo.promedio_campo),
                       'nota_ponderada': float(calculo.nota_ponderada),
                       'total_notas': calculo.total_notas_campo
                   })
               
               trimestres.append({
                   'periodo': nota_final.codigo_periodo.nombre,
                   'nota_final': float(nota_final.nota_final),
                   'campos': campos_detalle,
                   'fecha_calculo': nota_final.fecha_calculo
               })
           
           # Obtener predicción si existe
           try:
               prediccion = PrediccionNota.objects.filter(
                   ci_estudiante=estudiante,
                   codigo_curso=curso,
                   codigo_materia=materia,
                   is_active=True
               ).latest('fecha_prediccion')
               
               prediccion_data = {
                   'nota_predicha': float(prediccion.nota_predicha),
                   'confianza': float(prediccion.confianza),
                   'periodo_objetivo': prediccion.codigo_periodo_objetivo.nombre,
                   'fecha_prediccion': prediccion.fecha_prediccion
               }
           except PrediccionNota.DoesNotExist:
               prediccion_data = None
           
           # Calcular tendencia
           if len(trimestres) >= 2:
               primera_nota = trimestres[0]['nota_final']
               ultima_nota = trimestres[-1]['nota_final']
               if ultima_nota > primera_nota + 5:
                   tendencia = 'MEJORANDO'
               elif ultima_nota < primera_nota - 5:
                   tendencia = 'EMPEORANDO'
               else:
                   tendencia = 'ESTABLE'
           else:
               tendencia = 'INSUFICIENTES_DATOS'
           
           promedio_historico = sum(t['nota_final'] for t in trimestres) / len(trimestres) if trimestres else 0
           
           materias_data.append({
               'materia': {
                   'codigo': materia.codigo,
                   'nombre': materia.nombre
               },
               'trimestres': trimestres,
               'prediccion': prediccion_data,
               'tendencia': tendencia,
               'promedio_historico': round(promedio_historico, 2)
           })
       
       resultado = {
           'estudiante': {
               'ci': estudiante.ci,
               'nombre_completo': estudiante.nombre_completo,
               'email': estudiante.email
           },
           'curso': {
               'codigo': curso.codigo,
               'nombre': curso.nombre,
               'nivel': curso.nivel,
               'paralelo': curso.paralelo
           },
           'materias': materias_data,
           'resumen': {
               'total_materias': len(materias_data),
               'materias_con_prediccion': sum(1 for m in materias_data if m['prediccion']),
               'tendencia_general': self._calcular_tendencia_general(materias_data)
           }
       }
       
       return Response(resultado)
   
   @action(detail=False, methods=['get'], url_path='curso/(?P<codigo>[^/.]+)')
   def curso(self, request, codigo=None):
       """Reporte de rendimiento de un curso completo"""
       from apps.courses.models import Curso
       from apps.students.models import Inscripcion
       from apps.teachers.models import AsignacionCurso
       
       try:
           curso = Curso.objects.get(codigo=codigo, is_active=True)
       except Curso.DoesNotExist:
           return Response({'error': 'Curso no encontrado'}, status=status.HTTP_404_NOT_FOUND)
       
       # Verificar permisos
       if not self._tiene_permiso_curso(request.user, curso):
           return Response({'error': 'Sin permisos para ver este curso'}, status=status.HTTP_403_FORBIDDEN)
       
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
       
       estudiantes_data = []
       for inscripcion in inscripciones:
           estudiante = inscripcion.ci_estudiante
           estudiante_info = {
               'ci': estudiante.ci,
               'nombre_completo': estudiante.nombre_completo,
               'materias': []
           }
           
           for asignacion in asignaciones:
               materia = asignacion.codigo_materia
               
               # Obtener última nota final
               try:
                   ultima_nota = NotaFinalPeriodo.objects.filter(
                       ci_estudiante=estudiante,
                       codigo_curso=curso,
                       codigo_materia=materia,
                       is_active=True
                   ).latest('codigo_periodo__nombre')
                   
                   nota_actual = float(ultima_nota.nota_final)
               except NotaFinalPeriodo.DoesNotExist:
                   nota_actual = None
               
               # Obtener predicción
               try:
                   prediccion = PrediccionNota.objects.filter(
                       ci_estudiante=estudiante,
                       codigo_curso=curso,
                       codigo_materia=materia,
                       is_active=True
                   ).latest('fecha_prediccion')
                   
                   prediccion_data = {
                       'nota_predicha': float(prediccion.nota_predicha),
                       'confianza': float(prediccion.confianza)
                   }
               except PrediccionNota.DoesNotExist:
                   prediccion_data = None
               
               estudiante_info['materias'].append({
                   'materia': materia.nombre,
                   'nota_actual': nota_actual,
                   'prediccion': prediccion_data
               })
           
           estudiantes_data.append(estudiante_info)
       
       # Calcular estadísticas generales
       estadisticas = self._calcular_estadisticas_curso(curso, asignaciones.values_list('codigo_materia', flat=True))
       
       resultado = {
           'curso': {
               'codigo': curso.codigo,
               'nombre': curso.nombre,
               'nivel': curso.nivel,
               'paralelo': curso.paralelo,
               'gestion': curso.gestion
           },
           'estudiantes': estudiantes_data,
           'estadisticas': estadisticas,
           'resumen': {
               'total_estudiantes': len(estudiantes_data),
               'total_materias': len(asignaciones)
           }
       }
       
       return Response(resultado)
   
   @action(detail=False, methods=['get'], url_path='materia/(?P<codigo>[^/.]+)')
   def materia(self, request, codigo=None):
       """Reporte de rendimiento por materia"""
       from apps.subjects.models import Materia
       from apps.teachers.models import AsignacionCurso
       
       try:
           materia = Materia.objects.get(codigo=codigo, is_active=True)
       except Materia.DoesNotExist:
           return Response({'error': 'Materia no encontrada'}, status=status.HTTP_404_NOT_FOUND)
       
       # Obtener asignaciones de esta materia
       asignaciones = AsignacionCurso.objects.filter(
           codigo_materia=materia,
           is_active=True
       ).select_related('codigo_curso', 'ci_docente')
       
       cursos_data = []
       for asignacion in asignaciones:
           # Verificar permisos para este curso
           if not self._tiene_permiso_curso(request.user, asignacion.codigo_curso):
               continue
           
           # Obtener estadísticas del curso para esta materia
           notas_curso = NotaFinalPeriodo.objects.filter(
               codigo_curso=asignacion.codigo_curso,
               codigo_materia=materia,
               is_active=True
           )
           
           estadisticas_curso = {
               'promedio_general': notas_curso.aggregate(promedio=Avg('nota_final'))['promedio'] or 0,
               'total_estudiantes': notas_curso.values('ci_estudiante').distinct().count(),
               'notas_registradas': notas_curso.count()
           }
           
           cursos_data.append({
               'curso': {
                   'codigo': asignacion.codigo_curso.codigo,
                   'nombre': asignacion.codigo_curso.nombre,
                   'nivel': asignacion.codigo_curso.nivel
               },
               'docente': asignacion.ci_docente.nombre_completo,
               'estadisticas': estadisticas_curso
           })
       
       resultado = {
           'materia': {
               'codigo': materia.codigo,
               'nombre': materia.nombre
           },
           'cursos': cursos_data,
           'resumen': {
               'total_cursos': len(cursos_data),
               'promedio_global': sum(c['estadisticas']['promedio_general'] for c in cursos_data) / len(cursos_data) if cursos_data else 0
           }
       }
       
       return Response(resultado)
   
   def _tiene_permiso_estudiante(self, user, estudiante):
       """Verifica si el usuario tiene permisos para ver al estudiante"""
       if user.groups.filter(name='Administrador').exists():
           return True
       
       if user.groups.filter(name='Estudiante').exists():
           return estudiante.usuario == user
       
       if user.groups.filter(name='Docente').exists():
           from apps.teachers.models import Docente, AsignacionCurso
           from apps.students.models import Inscripcion
           try:
               docente = Docente.objects.get(usuario=user)
               inscripcion = Inscripcion.objects.get(ci_estudiante=estudiante, estado='ACTIVO')
               return AsignacionCurso.objects.filter(
                   ci_docente=docente,
                   codigo_curso=inscripcion.codigo_curso,
                   is_active=True
               ).exists()
           except:
               return False
       
       return False
   
   def _tiene_permiso_curso(self, user, curso):
       """Verifica si el usuario tiene permisos para ver el curso"""
       if user.groups.filter(name='Administrador').exists():
           return True
       
       if user.groups.filter(name='Docente').exists():
           from apps.teachers.models import Docente, AsignacionCurso
           try:
               docente = Docente.objects.get(usuario=user)
               return AsignacionCurso.objects.filter(
                   ci_docente=docente,
                   codigo_curso=curso,
                   is_active=True
               ).exists()
           except:
               return False
       
       return False
   
   def _calcular_tendencia_general(self, materias_data):
       """Calcula la tendencia general del estudiante"""
       tendencias = [m['tendencia'] for m in materias_data if m['tendencia'] != 'INSUFICIENTES_DATOS']
       if not tendencias:
           return 'INSUFICIENTES_DATOS'
       
       mejorando = tendencias.count('MEJORANDO')
       empeorando = tendencias.count('EMPEORANDO')
       
       if mejorando > empeorando:
           return 'MEJORANDO'
       elif empeorando > mejorando:
           return 'EMPEORANDO'
       else:
           return 'ESTABLE'
   
   def _calcular_estadisticas_curso(self, curso, materias):
       """Calcula estadísticas generales del curso"""
       from apps.students.models import Inscripcion
       
       # Obtener estudiantes del curso
       estudiantes = Inscripcion.objects.filter(
           codigo_curso=curso,
           estado='ACTIVO'
       ).values_list('ci_estudiante', flat=True)
       
       # Estadísticas por materia
       estadisticas_materias = []
       for materia_codigo in materias:
           notas = NotaFinalPeriodo.objects.filter(
               codigo_curso=curso,
               codigo_materia_id=materia_codigo,
               ci_estudiante__in=estudiantes,
               is_active=True
           )
           
           if notas.exists():
               estadisticas_materias.append({
                   'materia': materia_codigo,
                   'promedio': notas.aggregate(promedio=Avg('nota_final'))['promedio'],
                   'estudiantes_con_notas': notas.values('ci_estudiante').distinct().count()
               })
       
       return {
           'promedio_general_curso': sum(e['promedio'] for e in estadisticas_materias) / len(estadisticas_materias) if estadisticas_materias else 0,
           'materias': estadisticas_materias
       }

class PrediccionesViewSet(viewsets.GenericViewSet):
   """ViewSet para gestión de predicciones ML"""
   permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
   
   @action(detail=False, methods=['get'], url_path='estudiante/(?P<ci>[^/.]+)')
   def estudiante(self, request, ci=None):
       """Predicciones de un estudiante específico"""
       from apps.students.models import Estudiante
       
       try:
           estudiante = Estudiante.objects.get(ci=ci, is_active=True)
       except Estudiante.DoesNotExist:
           return Response({'error': 'Estudiante no encontrado'}, status=status.HTTP_404_NOT_FOUND)
       
       # Obtener todas las predicciones del estudiante
       predicciones = PrediccionNota.objects.filter(
           ci_estudiante=estudiante,
           is_active=True
       ).select_related('codigo_materia', 'codigo_periodo_objetivo')
       
       predicciones_data = []
       for prediccion in predicciones:
           predicciones_data.append({
               'materia': prediccion.codigo_materia.nombre,
               'periodo_objetivo': prediccion.codigo_periodo_objetivo.nombre,
               'nota_predicha': float(prediccion.nota_predicha),
               'confianza': float(prediccion.confianza),
               'algoritmo': prediccion.algoritmo_usado,
               'fecha_prediccion': prediccion.fecha_prediccion,
               'metricas': {
                   'r2_score': float(prediccion.r2_score) if prediccion.r2_score else None,
                   'mse': float(prediccion.mse) if prediccion.mse else None
               }
           })
       
       return Response({
           'estudiante': estudiante.nombre_completo,
           'total_predicciones': len(predicciones_data),
           'predicciones': predicciones_data
       })
   
   @action(detail=False, methods=['get'], url_path='curso/(?P<codigo>[^/.]+)')
   def curso(self, request, codigo=None):
       """Predicciones de todos los estudiantes de un curso"""
       from apps.courses.models import Curso
       
       try:
           curso = Curso.objects.get(codigo=codigo, is_active=True)
       except Curso.DoesNotExist:
           return Response({'error': 'Curso no encontrado'}, status=status.HTTP_404_NOT_FOUND)
       
       predicciones = PrediccionNota.objects.filter(
           codigo_curso=curso,
           is_active=True
       ).select_related('ci_estudiante', 'codigo_materia', 'codigo_periodo_objetivo')
       
       # Agrupar por estudiante
       estudiantes_predicciones = {}
       for prediccion in predicciones:
           ci = prediccion.ci_estudiante.ci
           if ci not in estudiantes_predicciones:
               estudiantes_predicciones[ci] = {
                   'estudiante': prediccion.ci_estudiante.nombre_completo,
                   'predicciones': []
               }
           
           estudiantes_predicciones[ci]['predicciones'].append({
               'materia': prediccion.codigo_materia.nombre,
               'nota_predicha': float(prediccion.nota_predicha),
               'confianza': float(prediccion.confianza),
               'periodo_objetivo': prediccion.codigo_periodo_objetivo.nombre
           })
       
       return Response({
           'curso': curso.nombre,
           'estudiantes': list(estudiantes_predicciones.values()),
           'total_estudiantes': len(estudiantes_predicciones)
       })
   
   @action(detail=False, methods=['post'])
   def generar(self, request):
       """Generar predicciones masivas para un curso"""
       serializer = GenerarPrediccionesSerializer(data=request.data)
       if not serializer.is_valid():
           return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
       
       data = serializer.validated_data
       from apps.courses.models import Curso, Periodo
       
       curso = Curso.objects.get(codigo=data['codigo_curso'])
       periodo_objetivo = Periodo.objects.get(codigo=data['codigo_periodo_objetivo'])
       
       try:
           with transaction.atomic():
               resultados = ServicioPrediciones.generar_predicciones_curso(
                   curso, periodo_objetivo
               )
               
               return Response({
                   'mensaje': 'Predicciones generadas exitosamente',
                   'curso': curso.nombre,
                   'periodo_objetivo': periodo_objetivo.nombre,
                   'resultados': resultados
               })
               
       except Exception as e:
           return Response({
               'error': f'Error generando predicciones: {str(e)}'
           }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CalculosViewSet(viewsets.GenericViewSet):
   """ViewSet para cálculos detallados de notas"""
   permission_classes = [IsAuthenticated]
   
   @action(detail=False, methods=['get'], url_path='estudiante/(?P<ci>[^/.]+)/trimestre/(?P<periodo>[^/.]+)')
   def estudiante_trimestre(self, request, ci=None, periodo=None):
       """Cálculo detallado de un estudiante en un trimestre específico"""
       from apps.students.models import Estudiante, Inscripcion
       from apps.courses.models import Periodo
       from apps.teachers.models import AsignacionCurso
       
       try:
           estudiante = Estudiante.objects.get(ci=ci, is_active=True)
           periodo_obj = Periodo.objects.get(codigo=periodo, is_active=True)
       except (Estudiante.DoesNotExist, Periodo.DoesNotExist):
           return Response({'error': 'Estudiante o período no encontrado'}, status=status.HTTP_404_NOT_FOUND)
       
       # Obtener curso del estudiante
       try:
           inscripcion = Inscripcion.objects.get(ci_estudiante=estudiante, estado='ACTIVO')
           curso = inscripcion.codigo_curso
       except Inscripcion.DoesNotExist:
           return Response({'error': 'Estudiante sin inscripción activa'}, status=status.HTTP_404_NOT_FOUND)
       
       # Obtener materias del curso
       asignaciones = AsignacionCurso.objects.filter(
           codigo_curso=curso,
           is_active=True
       ).select_related('codigo_materia')
       
       materias_calculos = []
       for asignacion in asignaciones:
           materia = asignacion.codigo_materia
           
           # Calcular notas del período si no existen
           calculos_campos = CalculadoraNotas.calcular_notas_periodo(
               estudiante, curso, materia, periodo_obj
           )
           
           # Calcular nota final
           nota_final = CalculadoraNotas.calcular_nota_final_periodo(
               estudiante, curso, materia, periodo_obj
           )
           
           materias_calculos.append({
               'materia': {
                   'codigo': materia.codigo,
                   'nombre': materia.nombre
               },
               'campos': calculos_campos,
               'nota_final': nota_final
           })
       
       return Response({
           'estudiante': estudiante.nombre_completo,
           'periodo': periodo_obj.nombre,
           'curso': curso.nombre,
           'materias': materias_calculos
       })
   
   @action(detail=False, methods=['get'], url_path='estudiante/(?P<ci>[^/.]+)/comparativo')
   def estudiante_comparativo(self, request, ci=None):
       """Comparativo histórico de un estudiante"""
       from apps.students.models import Estudiante, Inscripcion
       from apps.teachers.models import AsignacionCurso
       
       try:
           estudiante = Estudiante.objects.get(ci=ci, is_active=True)
       except Estudiante.DoesNotExist:
           return Response({'error': 'Estudiante no encontrado'}, status=status.HTTP_404_NOT_FOUND)
       
       # Obtener curso del estudiante
       try:
           inscripcion = Inscripcion.objects.get(ci_estudiante=estudiante, estado='ACTIVO')
           curso = inscripcion.codigo_curso
       except Inscripcion.DoesNotExist:
           return Response({'error': 'Estudiante sin inscripción activa'}, status=status.HTTP_404_NOT_FOUND)
       
       # Obtener materias del curso
       asignaciones = AsignacionCurso.objects.filter(
           codigo_curso=curso,
           is_active=True
       ).select_related('codigo_materia')
       
       materias_comparativo = []
       for asignacion in asignaciones:
           materia = asignacion.codigo_materia
           
           # Obtener todas las notas finales históricas
           notas_historicas = NotaFinalPeriodo.objects.filter(
               ci_estudiante=estudiante,
               codigo_curso=curso,
               codigo_materia=materia,
               is_active=True
           ).order_by('codigo_periodo__nombre')
           
           periodos_data = []
           for nota in notas_historicas:
               periodos_data.append({
                   'periodo': nota.codigo_periodo.nombre,
                   'nota_final': float(nota.nota_final),
                   'fecha_calculo': nota.fecha_calculo
               })
           
           # Calcular tendencia
           if len(periodos_data) >= 2:
               primera_nota = periodos_data[0]['nota_final']
               ultima_nota = periodos_data[-1]['nota_final']
               mejora = ultima_nota - primera_nota
               
               if mejora > 5:
                   tendencia = 'MEJORANDO'
               elif mejora < -5:
                   tendencia = 'EMPEORANDO'
               else:
                   tendencia = 'ESTABLE'
           else:
               tendencia = 'INSUFICIENTES_DATOS'
               mejora = 0
           
           materias_comparativo.append({
               'materia': {
                   'codigo': materia.codigo,
                   'nombre': materia.nombre
               },
               'periodos': periodos_data,
               'tendencia': tendencia,
               'mejora_puntos': round(mejora, 2),
               'promedio_historico': sum(p['nota_final'] for p in periodos_data) / len(periodos_data) if periodos_data else 0
           })
       
       return Response({
           'estudiante': estudiante.nombre_completo,
           'curso': curso.nombre,
           'materias': materias_comparativo
       })

class EstadisticasViewSet(viewsets.GenericViewSet):
   """ViewSet para estadísticas del sistema de predicciones"""
   permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
   
   @action(detail=False, methods=['get'])
   def modelo(self, request):
       """Estadísticas del modelo de Machine Learning"""
       # Estadísticas de predicciones
       total_predicciones = PrediccionNota.objects.filter(is_active=True).count()
       
       if total_predicciones > 0:
           precision_promedio = PrediccionNota.objects.filter(
               is_active=True,
               r2_score__isnull=False
           ).aggregate(promedio=Avg('r2_score'))['promedio'] or 0
           
           confianza_promedio = PrediccionNota.objects.filter(
               is_active=True
           ).aggregate(promedio=Avg('confianza'))['promedio'] or 0
           
           ultimo_entrenamiento = PrediccionNota.objects.filter(
               is_active=True
           ).aggregate(ultimo=Max('fecha_prediccion'))['ultimo']
           
           algoritmos = PrediccionNota.objects.filter(
               is_active=True
           ).values_list('algoritmo_usado', flat=True).distinct()
       else:
           precision_promedio = 0
           confianza_promedio = 0
           ultimo_entrenamiento = None
           algoritmos = []
       
       # Estadísticas de cálculos
       total_calculos = CalculoNotaPeriodo.objects.filter(is_active=True).count()
       total_notas_finales = NotaFinalPeriodo.objects.filter(is_active=True).count()
       
       return Response({
           'predicciones': {
               'total': total_predicciones,
               'precision_promedio': round(float(precision_promedio) * 100, 2) if precision_promedio else 0,
               'confianza_promedio': round(float(confianza_promedio), 2) if confianza_promedio else 0,
               'ultimo_entrenamiento': ultimo_entrenamiento,
               'algoritmos_usados': list(algoritmos)
           },
           'calculos': {
               'total_calculos_campos': total_calculos,
               'total_notas_finales': total_notas_finales
           }
       })
   
   @action(detail=False, methods=['get'])
   def general(self, request):
       """Estadísticas generales del sistema"""
       from apps.students.models import Estudiante
       from apps.courses.models import Curso
       from apps.subjects.models import Materia
       
       # Contar entidades principales
       total_estudiantes = Estudiante.objects.filter(is_active=True).count()
       total_cursos = Curso.objects.filter(is_active=True).count()
       total_materias = Materia.objects.filter(is_active=True).count()
       
       # Estudiantes con predicciones
       estudiantes_con_predicciones = PrediccionNota.objects.filter(
           is_active=True
       ).values('ci_estudiante').distinct().count()
       
       # Materias con más predicciones
       materias_top = PrediccionNota.objects.filter(
           is_active=True
       ).values(
           'codigo_materia__nombre'
       ).annotate(
           total_predicciones=Count('id')
       ).order_by('-total_predicciones')[:5]
       
       return Response({
           'entidades': {
               'total_estudiantes': total_estudiantes,
               'total_cursos': total_cursos,
               'total_materias': total_materias,
               'estudiantes_con_predicciones': estudiantes_con_predicciones,
               'cobertura_predicciones': round((estudiantes_con_predicciones / total_estudiantes * 100), 2) if total_estudiantes > 0 else 0
           },
           'materias_top_predicciones': list(materias_top),
           'uso_sistema': {
               'predicciones_esta_semana': PrediccionNota.objects.filter(
                   is_active=True,
                   fecha_prediccion__gte=timezone.now() - timedelta(days=7)
               ).count(),
               'calculos_este_mes': CalculoNotaPeriodo.objects.filter(
                   is_active=True,
                   fecha_calculo__gte=timezone.now() - timedelta(days=30)
               ).count()
           }
       })

# ViewSets para CRUD básico de modelos
class CalculoNotaPeriodoViewSet(viewsets.ReadOnlyModelViewSet):
   """ViewSet de solo lectura para cálculos de notas por período"""
   queryset = CalculoNotaPeriodo.objects.filter(is_active=True)
   serializer_class = CalculoNotaPeriodoSerializer
   permission_classes = [IsAuthenticated]
   filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
   filterset_fields = ['codigo_curso', 'codigo_materia', 'codigo_periodo', 'codigo_campo']
   search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido']
   ordering = ['-fecha_calculo']

class NotaFinalPeriodoViewSet(viewsets.ReadOnlyModelViewSet):
   """ViewSet de solo lectura para notas finales por período"""
   queryset = NotaFinalPeriodo.objects.filter(is_active=True)
   serializer_class = NotaFinalPeriodoSerializer
   permission_classes = [IsAuthenticated]
   filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
   filterset_fields = ['codigo_curso', 'codigo_materia', 'codigo_periodo']
   search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido']
   ordering = ['-fecha_calculo']

class PrediccionNotaViewSet(viewsets.ReadOnlyModelViewSet):
   """ViewSet de solo lectura para predicciones de notas"""
   queryset = PrediccionNota.objects.filter(is_active=True)
   serializer_class = PrediccionNotaSerializer
   permission_classes = [IsAuthenticated]
   filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
   filterset_fields = ['codigo_curso', 'codigo_materia', 'codigo_periodo_objetivo']
   search_fields = ['ci_estudiante__nombre', 'ci_estudiante__apellido']
   ordering = ['-fecha_prediccion']

class ModeloEntrenamientoViewSet(viewsets.ReadOnlyModelViewSet):
   """ViewSet de solo lectura para modelos de entrenamiento"""
   queryset = ModeloEntrenamiento.objects.filter(is_active=True)
   serializer_class = ModeloEntrenamientoSerializer
   permission_classes = [IsAuthenticated, IsDocenteOrAdministrador]
   ordering = ['-fecha_entrenamiento']