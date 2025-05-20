from django.core.mail import send_mail
from django.conf import settings
from .models import PersonaNatural
import logging

logger = logging.getLogger(__name__)  # para registrar errores si quieres

def notificar_oferta_urgente(oferta):
    """
    Notifies all PersonaNatural users in urgent mode about a new urgent job offer.
    
    Args:
        oferta (OfertaTrabajo): The urgent job offer to notify about
    """
    # Only proceed if the offer is actually marked as urgent
    if not oferta.urgente:
        logger.warning(f"Intento de notificar oferta no urgente (ID: {oferta.id})")
        return

    # Get active users who want urgent notifications
    personas = PersonaNatural.objects.filter(
        usuario__is_active=True,
        modo_urgente=True,
        recibir_ofertas_urgentes=True
    ).select_related('usuario')

    if not personas.exists():
        logger.info("No hay personas en modo urgente para notificar")
        return

    # Email content
    asunto = "📢 Nueva Oferta Urgente Disponible"
    mensaje = (
        f"¡Hola!\n\n"
        f"Se ha publicado una nueva oferta marcada como urgente:\n\n"
        f"🔹 Título: {oferta.nombre}\n"
        f"📍 Ubicación: {oferta.ubicacion}\n"
        f"📝 Descripción: {oferta.descripcion[:300]}...\n\n"  # Limit description length
        f"Fecha cierre: {oferta.fecha_cierre or 'No especificada'}\n\n"
        f"Visita MatchJob para más detalles y postular."
    )

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'matchjobbeta@gmail.com')
    recipient_count = 0

    for persona in personas:
        try:
            send_mail(
                subject=asunto,
                message=mensaje,
                from_email=from_email,
                recipient_list=[persona.usuario.correo],
                fail_silently=True  # Don't raise exceptions for failed emails
            )
            recipient_count += 1
        except Exception as e:
            logger.error(
                f"Error al enviar correo a {persona.usuario.correo} "
                f"(Persona ID: {persona.pk}): {str(e)}",
                exc_info=True
            )

    logger.info(
        f"Notificación de oferta urgente (ID: {oferta.id}) enviada a "
        f"{recipient_count}/{len(personas)} personas"
    )