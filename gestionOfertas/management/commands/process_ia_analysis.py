# management/commands/process_ia_analysis.py
# Crear este archivo en: tu_app/management/commands/

from django.core.management.base import BaseCommand
from django.utils import timezone
from tu_app.models import Postulacion  # Cambia 'tu_app' por el nombre real de tu app
from tu_app.utils import queue_batch_postulacion_analysis, queue_postulacion_analysis
from tu_app.signals import trigger_analysis_for_pending_postulaciones, retry_failed_analysis
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Procesa análisis de IA para postulaciones'

    def add_arguments(self, parser):
        parser.add_argument(
            '--mode',
            type=str,
            choices=['pending', 'retry', 'all', 'specific'],
            default='pending',
            help='Modo de procesamiento: pending (pendientes), retry (fallidos), all (todos), specific (específico)',
        )
        
        parser.add_argument(
            '--postulacion-id',
            type=int,
            help='ID específico de postulación a procesar (usar con --mode=specific)',
        )
        
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Tamaño del lote para procesamiento (default: 50)',
        )
        
        parser.add_argument(
            '--delay',
            type=int,
            default=0,
            help='Delay en segundos antes de ejecutar las tareas (default: 0)',
        )

    def handle(self, *args, **options):
        mode = options['mode']
        batch_size = options['batch_size']
        delay = options['delay']
        
        self.stdout.write(f"Iniciando procesamiento de análisis IA - Modo: {mode}")
        
        try:
            if mode == 'pending':
                resultado = trigger_analysis_for_pending_postulaciones()
                self.stdout.write(
                    self.style.SUCCESS(f"Procesamiento de pendientes completado: {resultado}")
                )
                
            elif mode == 'retry':
                resultado = retry_failed_analysis()
                self.stdout.write(
                    self.style.SUCCESS(f"Reintento de fallidos completado: {resultado}")
                )
                
            elif mode == 'all':
                # Procesar todas las postulaciones sin análisis IA
                postulaciones_sin_analisis = Postulacion.objects.filter(
                    estado_ia_analisis__in=['pendiente', 'error_analisis']
                ).values_list('id', flat=True)
                
                if postulaciones_sin_analisis:
                    postulaciones_list = list(postulaciones_sin_analisis)
                    
                    # Procesar en lotes
                    total_processed = 0
                    for i in range(0, len(postulaciones_list), batch_size):
                        lote = postulaciones_list[i:i+batch_size]
                        resultado = queue_batch_postulacion_analysis(lote, delay_seconds=delay)
                        total_processed += len(lote)
                        
                        self.stdout.write(f"Lote procesado: {len(lote)} postulaciones")
                    
                    self.stdout.write(
                        self.style.SUCCESS(f"Procesamiento completo: {total_processed} postulaciones encoladas")
                    )
                else:
                    self.stdout.write("No hay postulaciones para procesar")
                    
            elif mode == 'specific':
                postulacion_id = options.get('postulacion_id')
                if not postulacion_id:
                    self.stdout.write(
                        self.style.ERROR("Se requiere --postulacion-id para modo 'specific'")
                    )
                    return
                
                try:
                    postulacion = Postulacion.objects.get(id=postulacion_id)
                    resultado = queue_postulacion_analysis(postulacion, delay_seconds=delay)
                    self.stdout.write(
                        self.style.SUCCESS(f"Postulación {postulacion_id} procesada: {resultado}")
                    )
                except Postulacion.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f"Postulación con ID {postulacion_id} no encontrada")
                    )
                    
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Error durante el procesamiento: {str(e)}")
            )
            logger.error(f"Error en comando process_ia_analysis: {e}", exc_info=True)

# management/commands/monitor_ia_tasks.py
# Comando adicional para monitoreo

from django.core.management.base import BaseCommand
from tu_app.models import Postulacion  # Cambia por tu app real

class Command(BaseCommand):
    help = 'Monitorea el estado de las tareas de análisis IA'

    def handle(self, *args, **options):
        estados = Postulacion.objects.values('estado_ia_analisis').annotate(
            count=models.Count('id')
        ).order_by('estado_ia_analisis')
        
        self.stdout.write("\n=== Estado de Análisis IA ===")
        total = 0
        for estado in estados:
            count = estado['count']
            total += count
            self.stdout.write(f"{estado['estado_ia_analisis']}: {count}")
        
        self.stdout.write(f"\nTotal: {total} postulaciones")
        
        # Mostrar postulaciones recientes con errores
        errores_recientes = Postulacion.objects.filter(
            estado_ia_analisis='error_analisis'
        ).order_by('-updated_at')[:5]
        
        if errores_recientes:
            self.stdout.write("\n=== Errores Recientes ===")
            for post in errores_recientes:
                self.stdout.write(f"ID {post.id}: {post.razon_estado_ia}")