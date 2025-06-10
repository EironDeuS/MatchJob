from django.core.mail import send_mail
from django.conf import settings
from .models import PersonaNatural
import logging, requests, os
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
    Consulta el RUT en SimpleAPI (v2) y retorna si es una empresa activa válida.

    Args:
        rut (str): RUT de la empresa (puede venir con o sin puntos y guion).

    Returns:
        dict: {'valida': True/False, 'datos': {...} o 'mensaje': str}
    """
    api_key = settings.SIMPLEAPI_API_KEY

    # Limpiar el RUT para enviarlo en el path de la URL (sin puntos ni guion)
    rut_limpio = rut.replace('.', '').replace('-', '')
    
    # Nueva URL base del endpoint de SimpleAPI (v2)
    URL_BASE_V2 = "https://rut.simpleapi.cl/v2" 
    
    headers = {
        # El valor del header 'Authorization' debe ser solo la API Key, sin 'Bearer '.
        "Authorization": api_key, 
        "Content-Type": "application/json" 
    }

    # Construir la URL completa con el RUT en el path
    url_completa = f"{URL_BASE_V2}/{rut_limpio}"

    try:
        logger.debug(f"Intentando conectar a: {url_completa}")
        logger.debug(f"Usando API Key (primeros 5 caracteres): {api_key[:5]}...")

        # Aumentar el tiempo de espera (timeout) a 60 segundos
        response = requests.get(url_completa, headers=headers, timeout=15) 
        response.raise_for_status()  # Levanta HTTPError para códigos de error 4xx/5xx

        data = response.json()

        # Lógica de validación de la respuesta para 200 OK (según docs v2)
        # Si la API v2 devuelve 200 OK y contiene el rut y la razonSocial, asumimos validez.
        if data and data.get('rut') and data.get('razonSocial'):
            return {'valida': True, 'datos': data}
        else:
            # Esto se ejecutaría si hay un 200 OK pero el JSON es vacío o no tiene los campos esperados
            return {'valida': False, 'mensaje': f"RUT encontrado, pero respuesta de SimpleAPI incompleta o inesperada.", 'datos': data}


    except requests.exceptions.HTTPError as http_err:
        error_message = response.text or str(http_err) 

        if response.status_code == 404:
            logger.warning(f"Error 404 de SimpleAPI para RUT {rut}: {error_message}")
            return {'valida': False, 'mensaje': 'RUT no encontrado en la base de datos de SimpleAPI (v2).'}
        elif response.status_code == 401:
            logger.error(f"Error 401 de SimpleAPI (API Key inválida) para RUT {rut}: {error_message}")
            return {'valida': False, 'mensaje': 'Error de autenticación con SimpleAPI. API Key inválida o formato incorrecto.'}
        elif response.status_code == 400:
            logger.warning(f"Error 400 de SimpleAPI (Solicitud incorrecta) para RUT {rut}: {error_message}")
            return {'valida': False, 'mensaje': f'Error en el formato del RUT o solicitud inválida: {error_message}'}
        else:
            logger.error(f"Error HTTP inesperado de SimpleAPI para RUT {rut}: {response.status_code} - {error_message}")
            return {'valida': False, 'mensaje': f'Error al validar RUT con SimpleAPI: Código {response.status_code} - {error_message}'}
            
    except requests.exceptions.ConnectionError as conn_err:
        logger.error(f"Error de conexión con SimpleAPI para RUT {rut}: {conn_err}")
        return {'valida': False, 'mensaje': 'Error de conexión con SimpleAPI. Verifique su conexión a internet o proxy.'}
    except requests.exceptions.Timeout as timeout_err:
        logger.error(f"Timeout al conectar con SimpleAPI para RUT {rut}: La API no respondió a tiempo ({timeout_err}).")
        # Ya no hay simulación, este es un error real si se produce.
        return {'valida': False, 'mensaje': 'La validación del RUT con SimpleAPI excedió el tiempo de espera. La API tarda en responder.'}
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error general de request con SimpleAPI para RUT {rut}: {req_err}")
        return {'valida': False, 'mensaje': f'Error inesperado al comunicarse con SimpleAPI: {req_err}'}
    except ValueError as json_err: # Si la respuesta no es un JSON válido
        logger.error(f"Error al decodificar JSON de SimpleAPI para RUT {rut}: {json_err} - Respuesta cruda: {response.text}")
        return {'valida': False, 'mensaje': 'Respuesta inválida de SimpleAPI.'}
    except Exception as e:
        logger.exception(f"Error inesperado en validar_rut_empresa para RUT {rut}: {e}") 
        return {'valida': False, 'mensaje': 'Ocurrió un error inesperado durante la validación.'}
