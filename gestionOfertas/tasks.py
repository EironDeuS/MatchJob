# gestionOfertas/tasks.py

import os
import json
import logging
from google.cloud import tasks_v2
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction

# Importa tus modelos y utilidades
from .models import Postulacion # Asegúrate de importar Postulacion
from .utils import evaluate_postulacion_with_gemini # Asegúrate de importar tu función de análisis

logger = logging.getLogger(__name__)

# --- CONFIGURACIÓN DE CLOUD TASKS (desde settings.py) ---
GCP_PROJECT_ID = settings.GCP_PROJECT_ID
GCP_LOCATION = settings.GCP_LOCATION
GCP_QUEUE_NAME = settings.GCP_QUEUE_NAME
SERVICE_URL = settings.SERVICE_URL

# ----------------------------------------------------------------------
# Parte 1: El HANDLER de la Tarea (lo que Cloud Tasks llama por HTTP)
# ----------------------------------------------------------------------
@csrf_exempt
def analizar_postulacion_ia_task_handler(request):
    """
    Función que recibe y procesa la tarea de Cloud Tasks para analizar una postulación IA.
    """
    if request.method != 'POST':
        logger.warning(f"Método no permitido para la tarea de IA: {request.method}")
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

    postulacion_id = None # Inicializa para asegurar que siempre tenga un valor en el log de error
    try:
        data = json.loads(request.body)
        postulacion_id = data.get('postulacion_id')

        if not postulacion_id:
            logger.error("Tarea de IA recibida sin 'postulacion_id'.")
            return JsonResponse({'status': 'error', 'message': 'Missing postulacion_id'}, status=400)

        logger.info(f"Iniciando procesamiento de tarea IA para postulación ID: {postulacion_id}")

        with transaction.atomic():
            try:
                # Usamos select_for_update para bloquear la fila durante la transacción
                postulacion = Postulacion.objects.select_for_update().get(id=postulacion_id)
            except Postulacion.DoesNotExist:
                logger.error(f"Postulación con ID {postulacion_id} no encontrada para análisis IA.")
                # Si la postulación no existe, no hay nada que hacer, devolvemos 404 para que Cloud Tasks no reintente.
                return JsonResponse({'status': 'error', 'message': 'Postulación no encontrada'}, status=404)

            logger.info(f"DEBUG: Estado de análisis IA de la postulación {postulacion_id} al inicio: {postulacion.estado_ia_analisis}")

            # *** CAMBIO CRÍTICO AQUÍ: La validación de estado ***
            # La tarea solo debe proceder si el estado_ia_analisis es 'pendiente_ia'.
            # Si ya está 'en_analisis' (y no hubo un error que lo reseteara), o ya está 'aprobado_ia', etc.,
            # significa que ya se procesó o está en proceso.
            if postulacion.estado_ia_analisis != 'pendiente_ia':
                logger.warning(f"Postulación ID {postulacion_id} no está en estado 'pendiente_ia' ({postulacion.estado_ia_analisis}). Saltando análisis IA.")
                # Si se salta, se considera exitoso para Cloud Tasks para evitar reintentos innecesarios.
                return JsonResponse({'status': 'skipped', 'message': 'Postulación no en estado válido para análisis IA o ya procesada.'}, status=200)

            # Actualizar estado a "en_analisis" para evitar re-procesamiento si la tarea se reintenta
            # antes de completar o si otra instancia intenta procesarla.
            postulacion.estado_ia_analisis = 'en_analisis'
            postulacion.razon_estado_ia = 'Iniciando análisis por Cloud Task.'
            # Guardamos solo los campos que cambiamos para ser más eficientes
            postulacion.save(update_fields=['estado_ia_analisis', 'razon_estado_ia'])
            logger.info(f"Postulación ID {postulacion_id} actualizada a 'en_analisis'.")

        # El bloque de análisis NO debe estar dentro del transaction.atomic()
        # si la función de análisis es pesada o puede fallar de forma externa,
        # ya que mantendría la fila bloqueada y podría causar timeouts.
        # La transacción de arriba solo se usa para el cambio de estado inicial.
        try:
            # Ejecutar el análisis con Gemini
            # Asegúrate de que evaluate_postulacion_with_gemini devuelve un diccionario
            # con al menos 'status', 'message', 'puntaje', 'razones'.
            resultado_analisis = evaluate_postulacion_with_gemini(postulacion)

            # Actualizar la postulación con el resultado del análisis FINAL
            with transaction.atomic():
                # Obtenemos la postulación de nuevo dentro de la nueva transacción para asegurarnos
                # de que tenemos el estado más reciente, aunque select_for_update ya lo hizo arriba.
                # Esto es más bien una práctica si el análisis tomó mucho tiempo.
                # postulacion = Postulacion.objects.select_for_update().get(id=postulacion_id) # Opcional: si temes una condición de carrera MUY rara entre transacciones.
                                                                                        # Normalmente, como el ID está bloqueado en el primer bloque, no es estrictamente necesario aquí.

                # Determinar el estado final basado en el resultado de Gemini
                final_status = resultado_analisis.get('status', 'error_analisis') # Por defecto a error si no hay status
                if final_status not in [choice[0] for choice in postulacion.ESTADOS_IA_ANALISIS]:
                    # Asegúrate de que el estado de retorno de Gemini sea uno de tus ESTADOS_IA_ANALISIS
                    final_status = 'error_analisis' # Si Gemini devuelve algo inesperado, cámbialo a error

                postulacion.estado_ia_analisis = final_status
                postulacion.razon_estado_ia = resultado_analisis.get('message', 'Análisis IA finalizado.')
                postulacion.puntaje_ia = resultado_analisis.get('puntaje', None)
                postulacion.razones_ia = resultado_analisis.get('razones', {})

                postulacion.save(update_fields=[
                    'estado_ia_analisis',
                    'razon_estado_ia',
                    'puntaje_ia',
                    'razones_ia'
                ])

            logger.info(f"Análisis IA completado y postulación ID {postulacion_id} actualizada. Nuevo estado IA: '{postulacion.estado_ia_analisis}'.")
            return JsonResponse({'status': 'success', 'message': 'Análisis IA completado.'}, status=200)

        except Exception as e:
            # Captura errores durante el análisis Gemini
            logger.error(f"Error durante el análisis IA para ID {postulacion_id}: {e}", exc_info=True)
            with transaction.atomic():
                try:
                    # Intenta actualizar el estado a error_analisis
                    postulacion = Postulacion.objects.select_for_update().get(id=postulacion_id)
                    postulacion.estado_ia_analisis = 'error_analisis'
                    postulacion.razon_estado_ia = f"Error en el análisis de IA: {e}"
                    postulacion.save(update_fields=['estado_ia_analisis', 'razon_estado_ia'])
                    logger.error(f"Postulación ID {postulacion_id} actualizada a 'error_analisis' debido a fallo.")
                except Postulacion.DoesNotExist:
                    logger.error(f"Postulación ID {postulacion_id} no encontrada al intentar actualizar el error de IA.")
                except Exception as update_e:
                    logger.error(f"Error al intentar guardar el estado de error para postulación ID {postulacion_id}: {update_e}", exc_info=True)
            # Devolver 500 para que Cloud Tasks reintente, si es un error temporal.
            # Si el error es permanente (ej. datos inválidos persistentes), podrías devolver 200 y no reintentar.
            return JsonResponse({'status': 'error', 'message': f'Error interno del servidor durante el análisis: {e}'}, status=500)

    except json.JSONDecodeError as e:
        logger.error(f"Error JSON en cuerpo de tarea de IA: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': 'Invalid JSON body for IA task'}, status=400)
    except Exception as e:
        logger.error(f"Error inesperado en handler de tarea IA (fuera de try/except de análisis) para ID {postulacion_id}: {e}", exc_info=True)
        return JsonResponse({'status': 'error', 'message': f'Internal server error: {e}'}, status=500)


# ----------------------------------------------------------------------
# Parte 2: La función para ENCOLAR las tareas en Google Cloud Tasks
# ----------------------------------------------------------------------

def encolar_analisis_ia(postulacion_id):
    """
    Crea y encola una tarea de Google Cloud Tasks para analizar una postulación con IA.
    """
    client = tasks_v2.CloudTasksClient()

    parent = client.queue_path(GCP_PROJECT_ID, GCP_LOCATION, GCP_QUEUE_NAME)

    relative_path_for_task = "/tasks/analizar_ia/"
    full_target_url = f"{SERVICE_URL}{relative_path_for_task}"

    payload = json.dumps({'postulacion_id': postulacion_id})
    payload_bytes = payload.encode('utf-8')

    task_config = {
        'http_request': {
            'http_method': tasks_v2.HttpMethod.POST,
            'url': full_target_url,
            'headers': {'Content-type': 'application/json'},
            'body': payload_bytes,
        }
    }

    try:
        response = client.create_task(parent=parent, task=task_config)
        logger.info(f"Tarea de Cloud Task encolada: {response.name} para postulación ID {postulacion_id}")
        return response.name
    except Exception as e:
        logger.error(f"Error al encolar la tarea de Cloud Task para postulación ID {postulacion_id}: {e}", exc_info=True)
        raise e

# ----------------------------------------------------------------------
# Funciones para encolar lotes (si aún las necesitas)
# ----------------------------------------------------------------------

def encolar_lote_analisis_ia(postulacion_ids):
    """
    Encola tareas individuales de análisis IA para una lista de IDs de postulación.
    """
    logger.info(f"Encolando lote de {len(postulacion_ids)} postulaciones para análisis IA.")
    tasks_enqueued = []
    for postulacion_id in postulacion_ids:
        try:
            task_name = encolar_analisis_ia(postulacion_id)
            tasks_enqueued.append(task_name)
        except Exception as e:
            logger.error(f"Falló el encolado de la postulación ID {postulacion_id} en el lote: {e}")
    return tasks_enqueued