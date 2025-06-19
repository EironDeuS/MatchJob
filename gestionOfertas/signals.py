# signals.py - Crear este archivo en tu app para manejar automáticamente el análisis

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import Postulacion
from .utils import queue_postulacion_analysis
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Postulacion)
def trigger_ia_analysis_on_postulacion_create(sender, instance, created, **kwargs):
    """
    Signal que se dispara cuando se crea una nueva postulación.
    Automáticamente encola el análisis de IA.
    """
    if created and instance.estado_ia_analisis == 'pendiente':
        try:
            # Pequeño delay para asegurar que todos los datos estén guardados
            resultado = queue_postulacion_analysis(instance, delay_seconds=5)
            
            if resultado['status'] == 'queued':
                logger.info(f"Análisis IA automáticamente encolado para nueva postulación ID {instance.id}")
            else:
                logger.warning(f"No se pudo encolar análisis IA para postulación ID {instance.id}: {resultado.get('message')}")
                
        except Exception as e:
            logger.error(f"Error en signal de análisis IA para postulación ID {instance.id}: {e}", exc_info=True)


# Funciones auxiliares para uso manual en views o admin

def trigger_analysis_for_pending_postulaciones():
    """
    Función para procesar todas las postulaciones pendientes de análisis.
    Útil para ejecutar manualmente o en tareas programadas.
    """
    postulaciones_pendientes = Postulacion.objects.filter(
        estado_ia_analisis='pendiente'
    ).values_list('id', flat=True)
    
    if postulaciones_pendientes:
        from .utils import queue_batch_postulacion_analysis
        resultado = queue_batch_postulacion_analysis(list(postulaciones_pendientes))
        logger.info(f"Procesamiento manual de postulaciones pendientes: {resultado}")
        return resultado
    else:
        logger.info("No hay postulaciones pendientes de análisis IA")
        return {'status': 'success', 'message': 'No hay postulaciones pendientes'}


def retry_failed_analysis():
    """
    Función para reintentar análisis fallidos.
    """
    postulaciones_error = Postulacion.objects.filter(
        estado_ia_analisis='error_analisis'
    ).values_list('id', flat=True)
    
    if postulaciones_error:
        from .utils import queue_batch_postulacion_analysis
        resultado = queue_batch_postulacion_analysis(list(postulaciones_error))
        logger.info(f"Reintento de análisis fallidos: {resultado}")
        return resultado
    else:
        logger.info("No hay análisis fallidos para reintentar")
        return {'status': 'success', 'message': 'No hay análisis fallidos'}