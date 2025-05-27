from django.core.mail import send_mail
from django.conf import settings
from .models import PersonaNatural
import logging, requests
from django.utils.html import strip_tags
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)  # para registrar errores si quieres


from django.utils.html import strip_tags

def notificar_oferta_urgente(oferta):
    if not oferta.urgente:
        logger.warning(f"Intento de notificar oferta no urgente (ID: {oferta.id})")
        return

    personas = PersonaNatural.objects.filter(
        usuario__is_active=True,
        modo_urgente=True,
        recibir_ofertas_urgentes=True
    ).select_related('usuario')

    if not personas.exists():
        logger.info("No hay personas en modo urgente para notificar")
        return

    asunto = "📢 Nueva Oferta Urgente Disponible"
    sitio_url = "https://matchjob.cl"  # cambia esto según tu dominio real

    mensaje_html = render_to_string("gestionOfertas/emails/notificar_oferta_urgente.html", {
        "oferta": oferta,
        "sitio_url": sitio_url
    })

    mensaje_texto = strip_tags(mensaje_html)

    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'matchjobbeta@gmail.com')
    recipient_count = 0

    for persona in personas:
        try:
            send_mail(
                subject=asunto,
                message=mensaje_texto,
                from_email=from_email,
                recipient_list=[persona.usuario.correo],
                fail_silently=True,
                html_message=mensaje_html
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

def validar_rut_empresa(rut):
    """
    Consulta el RUT en SimpleAPI y retorna si es una empresa activa válida.

    Args:
        rut (str): RUT de la empresa (puede venir con o sin puntos y guion).

    Returns:
        dict: {'valida': True/False, 'datos': {...} o 'mensaje': str}
    """
    api_key = '4907-W160-6391-9273-2504'

    # Limpiar el RUT para la URL: quitar puntos y guiones
    rut_limpio_para_url = rut.replace('.', '').replace('-', '')

    # Construir la URL con el RUT limpio
    url = f'https://api.simpleapi.cl/api/v1/rut/empresa/{rut_limpio_para_url}'

    try:
        # Aquí, podrías enviar el RUT original en un payload JSON si la API lo requiere,
        # pero para este endpoint GET, se espera en la URL.
        response = requests.get(url, headers={'Authorization': f'Bearer {api_key}'})

        if response.status_code == 200:
            data = response.json()
            # Asumo que la API de SimpleAPI devuelve 'activo': True/False o 'estado': 'Activo'
            # Es importante verificar la estructura de la respuesta de la API de SimpleAPI
            # según su documentación oficial.
            # Si el campo es 'estado', y valor 'Activo'
            if data.get('estado') == 'Activo':
                return {'valida': True, 'datos': data}
            else:
                # Si no está activo o el estado no es 'Activo'
                mensaje_error = data.get('mensaje', 'RUT no está activo o no encontrado')
                return {'valida': False, 'mensaje': f'RUT no es una empresa activa: {mensaje_error}'}
        elif response.status_code == 404:
            # Ahora este 404 debería ser más específico si el RUT está limpio
            return {'valida': False, 'mensaje': f'RUT no encontrado en la base de datos de SimpleAPI.'}
        elif response.status_code == 401:
            return {'valida': False, 'mensaje': 'API Key inválida o no autorizada.'}
        else:
            # Capturar otros códigos de estado HTTP
            return {'valida': False, 'mensaje': f'Error al consultar RUT (código {response.status_code}): {response.text}'}
    except requests.RequestException as e:
        logger.error(f"Error de conexión o HTTP al validar RUT {rut}: {e}", exc_info=True)
        return {'valida': False, 'mensaje': f'Error de conexión con el servicio de verificación: {str(e)}'}
    except Exception as e:
        logger.error(f"Error inesperado al validar RUT {rut}: {e}", exc_info=True)
        return {'valida': False, 'mensaje': f'Ocurrió un error inesperado durante la validación.'}
