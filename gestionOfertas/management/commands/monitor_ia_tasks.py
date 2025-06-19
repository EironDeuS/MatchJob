# gestionOfertas/management/commands/monitor_ia_tasks.py

from django.core.management.base import BaseCommand
from django.db import models
from django.utils import timezone
from gestionOfertas.models import Postulacion
from datetime import datetime, timedelta

class Command(BaseCommand):
    help = 'Monitorea el estado de las tareas de análisis IA'

    def add_arguments(self, parser):
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Mostrar información detallada incluyendo errores recientes',
        )
        
        parser.add_argument(
            '--hours',
            type=int,
            default=24,
            help='Horas hacia atrás para mostrar estadísticas (default: 24)',
        )

    def handle(self, *args, **options):
        detailed = options['detailed']
        hours = options['hours']
        
        # Calcular fecha límite
        fecha_limite = timezone.now() - timedelta(hours=hours)
        
        self.stdout.write(f"\n=== Monitor de Análisis IA (últimas {hours} horas) ===")
        
        # Estadísticas generales
        estados = Postulacion.objects.values('estado_ia_analisis').annotate(
            count=models.Count('id')
        ).order_by('estado_ia_analisis')
        
        self.stdout.write("\n--- Estado General ---")
        total = 0
        for estado in estados:
            count = estado['count']
            total += count
            status_name = estado['estado_ia_analisis'] or 'sin_estado'
            self.stdout.write(f"{status_name:15}: {count:5}")
        
        self.stdout.write(f"{'TOTAL':15}: {total:5}")
        
        # Estadísticas recientes
        estados_recientes = Postulacion.objects.filter(
            updated_at__gte=fecha_limite
        ).values('estado_ia_analisis').annotate(
            count=models.Count('id')
        ).order_by('estado_ia_analisis')
        
        if estados_recientes:
            self.stdout.write(f"\n--- Actividad Reciente (últimas {hours}h) ---")
            total_reciente = 0
            for estado in estados_recientes:
                count = estado['count']
                total_reciente += count
                status_name = estado['estado_ia_analisis'] or 'sin_estado'
                self.stdout.write(f"{status_name:15}: {count:5}")
            
            self.stdout.write(f"{'TOTAL':15}: {total_reciente:5}")
        
        if detailed:
            # Mostrar errores recientes
            errores_recientes = Postulacion.objects.filter(
                estado_ia_analisis='error_analisis',
                updated_at__gte=fecha_limite
            ).order_by('-updated_at')[:10]
            
            if errores_recientes:
                self.stdout.write(f"\n--- Errores Recientes (últimos 10) ---")
                for post in errores_recientes:
                    fecha_str = post.updated_at.strftime('%Y-%m-%d %H:%M')
                    razon = (post.razon_estado_ia or 'Sin razón')[:60]
                    self.stdout.write(f"ID {post.id:5} | {fecha_str} | {razon}")
            
            # Mostrar postulaciones en análisis que llevan mucho tiempo
            en_analisis_antiguas = Postulacion.objects.filter(
                estado_ia_analisis='en_analisis',
                updated_at__lt=timezone.now() - timedelta(hours=2)
            ).order_by('updated_at')[:5]
            
            if en_analisis_antiguas:
                self.stdout.write(f"\n--- En Análisis Demasiado Tiempo ---")
                for post in en_analisis_antiguas:
                    fecha_str = post.updated_at.strftime('%Y-%m-%d %H:%M')
                    tiempo_transcurrido = timezone.now() - post.updated_at
                    horas = tiempo_transcurrido.total_seconds() / 3600
                    self.stdout.write(f"ID {post.id:5} | Desde: {fecha_str} | {horas:.1f}h")
            
            # Estadísticas de performance
            completados_recientes = Postulacion.objects.filter(
                estado_ia_analisis__in=['aprobado_ia', 'rechazado_ia'],
                updated_at__gte=fecha_limite
            )
            
            if completados_recientes.exists():
                aprobados = completados_recientes.filter(estado_ia_analisis='aprobado_ia').count()
                rechazados = completados_recientes.filter(estado_ia_analisis='rechazado_ia').count()
                total_completados = aprobados + rechazados
                
                tasa_aprobacion = (aprobados / total_completados * 100) if total_completados > 0 else 0
                
                self.stdout.write(f"\n--- Performance (últimas {hours}h) ---")
                self.stdout.write(f"Aprobados:      {aprobados:5}")
                self.stdout.write(f"Rechazados:     {rechazados:5}")
                self.stdout.write(f"Tasa aprobación: {tasa_aprobacion:5.1f}%")
        
        self.stdout.write(f"\n{'='*50}")