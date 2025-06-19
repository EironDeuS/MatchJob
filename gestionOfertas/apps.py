from django.apps import AppConfig


class GestionofertasConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestionOfertas'

    def ready(self):
            import gestionOfertas.signals