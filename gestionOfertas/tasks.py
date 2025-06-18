# MatchJob/gestionOferta/tasks.py

from celery import shared_task
import logging
# Importa tus modelos y utilidades desde la misma aplicación 'gestionOferta'
from .models import Postulacion 
from .utils import evaluate_postulacion_with_gemini 

logger = logging.getLogger(__name__)

@shared_task
def process_postulacion_evaluation(postulacion_id):
    """
    Tarea Celery para ejecutar la evaluación de la postulación con la IA en segundo plano.
    """
    try:
        # Asegúrate de volver a cargar la instancia para tener el estado más reciente
        # y evitar problemas si el objeto se modificó entre el guardado y el inicio de la tarea.
        postulacion = Postulacion.objects.get(id=postulacion_id)
        logger.info(f"Iniciando evaluación IA para Postulación ID: {postulacion_id}")
        
        # Llama a la función de evaluación
        result = evaluate_postulacion_with_gemini(postulacion)
        
        logger.info(f"Evaluación IA completada para Postulación ID: {postulacion_id}. Resultado: {result.get('status')}")
        # Aquí podrías realizar alguna acción adicional si es necesario,
        # como enviar una notificación, etc., basada en result
    except Postulacion.DoesNotExist:
        logger.error(f"Postulacion con ID {postulacion_id} no encontrada para evaluación en tarea.")
    except Exception as e:
        logger.error(f"Error inesperado en la tarea de evaluación de Postulación ID {postulacion_id}: {e}", exc_info=True)

# Puedes añadir otras tareas aquí si las necesitas, por ejemplo para limpieza.
# @shared_task
# def tarea_ejemplo_limpieza():
#     logger.info("Ejecutando tarea de limpieza de ejemplo.")
#     print("Tarea de limpieza ejecutada!")