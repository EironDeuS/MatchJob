# MatchJob/MatchJob/celery.py

import os
from celery import Celery

# Establece el módulo de configuración de Django para 'celery'.
# ¡CORREGIDO! El nombre de tu proyecto es 'MatchJob'
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'MatchJob.settings')

# ¡CORREGIDO! El nombre de la aplicación Celery es el mismo que tu proyecto
app = Celery('MatchJob')

# Usando un objeto de configuración de Django, Celery no necesita su propio archivo de configuración.
# El nombre de espacio 'CELERY' significa que todas las variables de configuración de Celery
# deben empezar con 'CELERY_', por ejemplo, CELERY_BROKER_URL.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Descubre tareas automáticamente en todos los archivos tasks.py de tus aplicaciones Django.
app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
