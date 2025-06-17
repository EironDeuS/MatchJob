# utils.py

from django.core.mail import send_mail
from django.conf import settings
from .models import PersonaNatural, CV, CertificadoAntecedentes, EstadoDocumento # Asegúrate de que CV y CertificadoAntecedentes estén aquí
import logging, requests, os
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
import re
from django.db import transaction # Para asegurar la atomicidad
import json # Para manejar los datos JSON
import google.generativeai as genai # Para interactuar con la API de Gemini
import googlemaps
logger = logging.getLogger(__name__)

# # Configuración para la API de Google Gemini (mantener esto es importante si usas Gemini)
# if hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_MAPS_API_KEY:
#     try:
#         genai.configure(api_key=settings.GOOGLE_MAPS_API_KEY)
#         logger.info("Google Gemini API configurada.")
#     except Exception as e:
#         logger.error(f"Error al configurar Google Gemini API: {e}")
# else:
#     logger.warning("GOOGLE_API_KEY no encontrada en settings.py. La funcionalidad de IA de Gemini podría no estar disponible.")

# GMAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY if hasattr(settings, 'Maps_API_KEY') else None
# if GMAPS_API_KEY:
#     gmaps = googlemaps.Client(key=GMAPS_API_KEY)
#     logger.info("Google Maps API configurada.")
# else:
#     logger.warning("Maps_API_KEY no encontrada en settings.py. La funcionalidad de distancia podría estar limitada.")

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

def calculate_dv(rut_body):
    """
    Calcula el dígito verificador de un RUT (algoritmo Módulo 11).
    rut_body: el número del RUT sin el dígito verificador (ej. 12345678).
    """
    rut_str = str(rut_body)
    reversed_digits = [int(d) for d in rut_str[::-1]]
    factors = [2, 3, 4, 5, 6, 7] # Secuencia de factores
    
    total = 0
    for i, digit in enumerate(reversed_digits):
        total += digit * factors[i % len(factors)]
    
    remainder = total % 11
    
    if remainder == 0:
        return '0'
    elif remainder == 1:
        return 'K'
    else:
        return str(11 - remainder)

def validate_rut_format(rut_input):
    """
    Valida el formato del RUT (ej. 12345678-9 o 1.234.567-K).
    Retorna el RUT formateado sin puntos y con guión.
    Lanza ValidationError si el formato es incorrecto.
    """
    if not rut_input:
        raise ValidationError("El RUT no puede estar vacío.")

    # Limpiar puntos y espacios, convertir a mayúsculas
    rut_clean = rut_input.replace('.', '').replace(' ', '').upper()

    # Regex para validar el formato "XXXXXXXX-Y" o "XXXXXXX-Y"
    # X son dígitos, Y es dígito o 'K'
    if not re.match(r'^\d{1,8}-[\dkK]$', rut_clean):
        raise ValidationError("Formato de RUT inválido. Use el formato 12345678-9 o 1.234.567-K.")

    # No se valida el dígito verificador aquí, solo el formato.
    return rut_clean

def clean_rut(rut_formatted):
    """
    Recibe un RUT ya en formato 'XXXXXXX-Y' y valida su dígito verificador.
    Lanza ValidationError si el DV es incorrecto.
    Retorna el RUT limpio y formateado con guión (si ya no lo estaba).
    """
    if not rut_formatted:
        raise ValidationError("El RUT no puede estar vacío para la validación.")

    parts = rut_formatted.split('-')
    if len(parts) != 2:
        raise ValidationError("Formato de RUT interno inválido. Se esperaba RUT con guión.")
    
    cuerpo = parts[0]
    dv_input = parts[1]

    if not cuerpo.isdigit():
        raise ValidationError("El cuerpo del RUT debe contener solo números.")
    if not (dv_input.isdigit() or dv_input == 'K'):
        raise ValidationError("El dígito verificador debe ser un número o 'K'.")

    try:
        calculated_dv = calculate_dv(int(cuerpo))
    except ValueError:
        raise ValidationError("El cuerpo del RUT no es un número válido.")
    
    if calculated_dv != dv_input:
        raise ValidationError(f"RUT inválido. Dígito verificador incorrecto. Esperado: {calculated_dv}")

    return rut_formatted # Retorna el RUT limpio y formateado con guión


# Función para calcular distancia (adaptada de tu mapa.html)
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en kilómetros entre dos puntos geográficos (latitud, longitud)
    utilizando la API de Google Maps Distance Matrix.
    Retorna la distancia en km o None si hay un error.
    """
    if not GMAPS_API_KEY:
        logger.warning("Maps_API_KEY no configurada. No se puede calcular la distancia.")
        return None
    
    if lat1 is None or lon1 is None or lat2 is None or lon2 is None:
        logger.warning("Coordenadas incompletas para calcular distancia.")
        return None

    try:
        origins = [(lat1, lon1)]
        destinations = [(lat2, lon2)]
        
        # Request a Distance Matrix API
        matrix = gmaps.distance_matrix(origins, destinations, mode="driving")
        
        if matrix['status'] == 'OK' and matrix['rows'][0]['elements'][0]['status'] == 'OK':
            distance_meters = matrix['rows'][0]['elements'][0]['distance']['value']
            return distance_meters / 1000.0  # Convertir a kilómetros
        else:
            logger.error(f"Error al obtener distancia de Google Maps API: {matrix.get('error_message', 'Desconocido')}")
            return None
    except Exception as e:
        logger.error(f"Excepción al calcular distancia: {e}", exc_info=True)
        return None


def evaluate_postulacion_with_gemini(postulacion_instance):
    """
    Evalúa la idoneidad de un candidato (Postulacion) para una oferta de trabajo
    utilizando información del CV, Certificado de Antecedentes y la Oferta de Trabajo.
    Calcula un puntaje de 0-100 y almacena razones.
    """
    if not postulacion_instance or not isinstance(postulacion_instance, Postulacion):
        return {'status': 'error', 'message': 'Instancia de Postulacion inválida para evaluación.'}

    # Acceder a los modelos relacionados
    persona = postulacion_instance.persona
    oferta = postulacion_instance.oferta
    cv = getattr(persona, 'cv', None)
    certificado = getattr(persona, 'certificado_antecedentes', None)

    # Inicializar el puntaje y razones
    puntaje_ia = 0
    razones_ia = {}
    rechazo_automatico_distancia = False

    # --- 1. Verificación de distancia (Rechazo automático si > 200km) ---
    if oferta.latitud and oferta.longitud and persona.usuario.direccion:
        # Intentar obtener lat/lon de la dirección de la persona si no tiene CV con coordenadas
        # Para simplificar, asumiremos que si el CV tiene lat/lon, lo usamos, sino usamos la dirección del usuario.
        # Idealmente, la dirección del usuario debería geocodificarse al momento del registro/edición del perfil
        # y guardarse en PersonaNatural.latitud/longitud.
        
        # Para este ejemplo, si no hay lat/lon en el CV (datos_analizados_ia.get('datos_personales', {}).get('ubicacion_latitud')),
        # y el usuario NO tiene lat/lon en su perfil, podríamos intentar geocodificar la dirección de su perfil.
        # Sin embargo, eso sería una llamada a la API de Google Maps Geocoding por cada postulación, lo cual es costoso y lento.
        # Es MUCHO mejor guardar lat/lon en el modelo PersonaNatural cuando el usuario introduce su dirección.

        # Asumiremos que PersonaNatural.usuario.direccion es suficiente para un geocoding *previamente hecho*.
        # Si tienes latitud y longitud directamente en PersonaNatural, úsalas.
        # Si no, deberías considerar añadir campos `latitud` y `longitud` a `PersonaNatural`
        # y poblar esos campos cuando el usuario registra su dirección.
        
        # Para la demostración, usaremos la latitud/longitud de la oferta y del CV (si disponible) o asumiremos
        # que el CV extrae la ciudad/país y lo podemos usar en el prompt, o que la PersonaNatural tiene lat/lon.

        # VOY A ASUMIR que tienes `latitud` y `longitud` en el modelo `PersonaNatural`
        # Si no los tienes, necesitarás un paso de geocodificación al guardar la dirección del usuario.
        
        # Ejemplo: Usando lat/lon del perfil de usuario, o de los datos del CV si están allí.
        # Idealmente, el modelo PersonaNatural debería tener campos latitud y longitud.
        
        # Si el CV extrae una ubicación específica que pueda ser geocodificada:
        cv_location_lat = cv.datos_analizados_ia.get('datos_personales', {}).get('ubicacion_latitud')
        cv_location_lon = cv.datos_analizados_ia.get('datos_personales', {}).get('ubicacion_longitud')

        # Si PersonaNatural tiene campos de latitud y longitud, úsalos:
        # user_lat = persona.latitud
        # user_lon = persona.longitud
        
        # Por ahora, para la demostración, si no tenemos lat/lon exactos en el CV, asumiremos una ubicación genérica
        # o haremos que Gemini infiera una ubicación aproximada de la dirección del usuario para la distancia.
        # La forma más robusta es tener `latitud` y `longitud` en `PersonaNatural`.
        
        # Si la dirección del usuario está en el campo `direccion` del modelo `Usuario`:
        user_address = persona.usuario.direccion
        if user_address:
            # Este es un punto crítico: idealmente esta dirección ya debería estar geocodificada.
            # Aquí la geocodificamos al vuelo SOLO para este ejemplo. En producción, ¡evitar esto si es posible!
            try:
                geocode_result = gmaps.geocode(user_address + ", Chile") # Asumiendo Chile como país
                if geocode_result:
                    user_lat = geocode_result[0]['geometry']['location']['lat']
                    user_lon = geocode_result[0]['geometry']['location']['lng']
                    
                    distance_km = calculate_distance(user_lat, user_lon, oferta.latitud, oferta.longitud)
                    
                    if distance_km is not None:
                        if distance_km > 200:
                            postulacion_instance.estado = 'rechazado'
                            postulacion_instance.rechazo_automatico_distancia = True
                            postulacion_instance.razones_ia['rechazo_distancia'] = f"Distancia ({distance_km:.2f} km) excede el límite de 200 km."
                            postulacion_instance.puntaje_ia = 0 # Puntaje cero por rechazo
                            postulacion_instance.save()
                            logger.info(f"Postulación ID {postulacion_instance.id} rechazada automáticamente por distancia: {distance_km:.2f} km.")
                            return {'status': 'rejected', 'message': 'Rechazado automáticamente por distancia.', 'score': 0}
                        else:
                            razones_ia['distancia_km'] = f"{distance_km:.2f} km"
                    else:
                        logger.warning(f"No se pudo calcular la distancia para postulación ID {postulacion_instance.id}. Continuando sin chequeo de distancia.")

            except Exception as e:
                logger.error(f"Error al geocodificar dirección de usuario o calcular distancia para Postulación ID {postulacion_instance.id}: {e}", exc_info=True)
                # No rechazamos automáticamente si falla la geocodificación/distancia, pero lo loggeamos.
                razones_ia['distancia_error'] = f"No se pudo calcular distancia: {e}"

    # --- 2. Recopilar toda la información para la IA ---
    # Convertir los datos a un formato textual o JSON estructurado para Gemini
    
    # Datos de la persona (usuario y PersonaNatural)
    person_info = {
        "nombres": persona.nombres,
        "apellidos": persona.apellidos,
        "rut_perfil": persona.usuario.username,
        "email_perfil": persona.usuario.correo,
        "telefono_perfil": persona.usuario.telefono,
        "direccion_perfil": persona.usuario.direccion,
        "fecha_nacimiento_perfil": str(persona.fecha_nacimiento) if persona.fecha_nacimiento else None,
        "nacionalidad": persona.nacionalidad,
    }

    # Datos del CV
    cv_info = cv.datos_analizados_ia if cv else {}
    if cv_info.get('datos_personales'):
        # Eliminar datos personales del CV si ya los tenemos del perfil para evitar redundancia o conflicto
        # o si queremos que la IA los use solo para validación cruzada.
        # Por ahora, los dejamos para que la IA los evalúe en coherencia.
        pass 
    
    # Datos del Certificado de Antecedentes
    cert_info = certificado.datos_analizados_ia if certificado else {}

    # Datos de la Oferta de Trabajo
    offer_info = {
        "titulo": oferta.nombre,
        "descripcion": oferta.descripcion,
        "requisitos": oferta.requisitos,
        "beneficios": oferta.beneficios,
        "salario": oferta.salario,
        "tipo_contrato": oferta.get_tipo_contrato_display(),
        "ubicacion_oferta_direccion": oferta.direccion,
        "es_servicio": oferta.es_servicio,
        "urgente": oferta.urgente,
        "categoria": oferta.categoria.nombre_categoria if oferta.categoria else "Sin Categoria",
        "fecha_cierre": str(oferta.fecha_cierre) if oferta.fecha_cierre else "No especificada"
    }
    
    full_input_for_gemini = {
        "candidato_perfil": person_info,
        "cv_analizado": cv_info,
        "certificado_antecedentes_analizado": cert_info,
        "oferta_trabajo": offer_info,
        "validaciones_previas": razones_ia # Incluir distancia si se calculó
    }

    # Construir el prompt para Gemini
    prompt = (
        f"Eres un experto en reclutamiento y análisis de perfiles. Tu tarea es evaluar la idoneidad de un candidato "
        f"para una oferta de trabajo específica, basándote en la siguiente información estructurada en JSON. "
        f"Asigna un 'puntaje_ia' de 0 a 100, donde 100 es una coincidencia perfecta y 0 es una no coincidencia o rechazo total. "
        f"Considera los siguientes criterios, dándoles el peso adecuado:\n"
        f"- Coincidencia de habilidades y experiencia del CV con los requisitos de la oferta.\n"
        f"- Nivel educativo relevante del CV.\n"
        f"- Idiomas (especialmente inglés si es relevante para el puesto).\n"
        f"- Coherencia y profesionalismo general del CV (resumen, formato, etc.).\n"
        f"- Ausencia de antecedentes en el certificado (es crucial para la idoneidad).\n"
        f"- Coherencia de datos personales entre perfil, CV y certificado.\n"
        f"- Otros factores relevantes que puedas inferir (ej. experiencia en proyectos similares).\n"
        f"- Prioriza la claridad y concisión en las razones del puntaje.\n"
        f"- Si no hay CV o certificado, evalúa el perfil base y la oferta, y ajusta el puntaje de forma conservadora.\n\n"
        f"Proporciona la respuesta en formato JSON, incluyendo 'puntaje_ia' y 'razones_ia' (un diccionario con 'fortalezas', 'oportunidades_mejora' y 'resumen_coincidencia').\n\n"
        f"Datos para el análisis:\n{json.dumps(full_input_for_gemini, indent=2)}\n\n"
        f"Formato JSON esperado para la salida:\n"
        f"{{\n"
        f"  \"puntaje_ia\": \"integer (0-100)\",\n"
        f"  \"razones_ia\": {{\n"
        f"    \"fortalezas\": \"string\",\n"
        f"    \"oportunidades_mejora\": \"string\",\n"
        f"    \"resumen_coincidencia\": \"string\"\n"
        f"  }}\n"
        f"}}"
    )

    try:
        # Marcar la postulación como en procesamiento
        postulacion_instance.estado = 'revisado' # O un nuevo estado 'procesando_ia' si lo defines
        postulacion_instance.save(update_fields=['estado'])

        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        response_text = response.text.strip()
        # Limpiar el output si Gemini lo envuelve en bloques de código
        if response_text.startswith("```json") and response_text.endswith("```"):
            json_str = response_text[7:-3].strip()
        else:
            json_str = response_text
        
        ia_analysis_result = json.loads(json_str)

        # Extraer puntaje y razones
        new_puntaje = ia_analysis_result.get('puntaje_ia')
        new_razones = ia_analysis_result.get('razones_ia')

        # Asegurarse de que el puntaje sea un entero válido
        if new_puntaje is not None:
            try:
                new_puntaje = int(new_puntaje)
                if not (0 <= new_puntaje <= 100):
                    raise ValueError("Puntaje IA fuera de rango (0-100).")
            except ValueError:
                logger.error(f"Puntaje IA inválido para Postulación ID {postulacion_instance.id}: {new_puntaje}")
                new_puntaje = None # Invalidar el puntaje si no es un número o está fuera de rango
        
        with transaction.atomic():
            postulacion_instance.puntaje_ia = new_puntaje
            if new_razones and isinstance(new_razones, dict):
                postulacion_instance.razones_ia.update(new_razones) # Actualizar el JSONField
            
            # Si el puntaje es muy bajo, se puede considerar un rechazo automático por IA
            if new_puntaje is not None and new_puntaje < 20: # Umbral de ejemplo, puedes ajustar
                 postulacion_instance.estado = 'rechazado'
                 postulacion_instance.razones_ia['rechazo_ia_bajo_puntaje'] = f"Puntaje de idoneidad IA muy bajo ({new_puntaje})."
            else:
                 postulacion_instance.estado = 'revisado' # Mantener 'revisado' o cambiar a 'apto_para_entrevista' etc.

            postulacion_instance.save()
            logger.info(f"Postulación de {persona.usuario.username} a {oferta.nombre} (ID: {postulacion_instance.id}) evaluada con IA. Puntaje: {new_puntaje}")

        return {'status': 'success', 'score': new_puntaje, 'reasons': new_razones, 'message': 'Postulación evaluada exitosamente.'}

    except json.JSONDecodeError as e:
        postulacion_instance.estado = 'error'
        postulacion_instance.razones_ia['error_ia'] = f"Error de formato JSON en la respuesta de la IA: {e}"
        postulacion_instance.save(update_fields=['estado', 'razones_ia'])
        logger.error(f"Error al decodificar JSON de Gemini para Postulación ID {postulacion_instance.id}: {e}\nRespuesta recibida: {response_text[:500]}", exc_info=True)
        return {'status': 'error', 'message': f'Error al procesar Postulación con IA (JSON inválido): {e}'}
    except Exception as e:
        postulacion_instance.estado = 'error'
        postulacion_instance.razones_ia['error_ia'] = f"Error inesperado durante el procesamiento de la Postulación: {e}"
        postulacion_instance.save(update_fields=['estado', 'razones_ia'])
        logger.error(f"Error inesperado al evaluar Postulación con Gemini (Postulación ID: {postulacion_instance.id}): {e}", exc_info=True)
        return {'status': 'error', 'message': f'Error al procesar Postulación con IA: {e}'}