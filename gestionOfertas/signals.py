from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import OfertaTrabajo
from .utils import notificar_oferta_urgente  # Asumiendo que tu función está en utils.py

@receiver(post_save, sender=OfertaTrabajo)
def enviar_notificacion_urgente(sender, instance, created, **kwargs):
    if instance.urgente:
        notificar_oferta_urgente(instance)

        