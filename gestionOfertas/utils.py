# utils.py

from django.core.mail import send_mail
from django.conf import settings
from .models import PersonaNatural, CV, CertificadoAntecedentes, EstadoDocumento, Postulacion # Asegúrate de que CV, CertificadoAntecedentes y Postulacion estén aquí
import logging, requests, os
from django.utils.html import strip_tags
from django.core.exceptions import ValidationError
from django.template.loader import render_to_string
import re
from django.db import transaction # Para asegurar la atomicidad
import json # Para manejar los datos JSON
import google.generativeai as genai # Para interactuar con la API de Gemini
import googlemaps
import json
from decimal import Decimal
from datetime import date, datetime
logger = logging.getLogger(__name__)

# Configuración para la API de Google Gemini (mantener esto es importante si usas Gemini)
if hasattr(settings, 'GOOGLE_API_KEY') and settings.GOOGLE_API_KEY:
    try:
        genai.configure(api_key=settings.GOOGLE_API_KEY)
        logger.info("Google Gemini API configurada.")
    except Exception as e:
        logger.error(f"Error al configurar Google Gemini API: {e}")
else:
    logger.warning("GOOGLE_API_KEY no encontrada en settings.py. La funcionalidad de IA de Gemini podría no estar disponible.")

GMAPS_API_KEY = settings.GOOGLE_MAPS_API_KEY if hasattr(settings, 'GOOGLE_MAPS_API_KEY') else None
if GMAPS_API_KEY:
    gmaps = googlemaps.Client(key=GMAPS_API_KEY)
    logger.info("Google Maps API configurada.")
else:
    logger.warning("GOOGLE_MAPS_API_KEY no encontrada en settings.py. La funcionalidad de distancia podría estar limitada.")

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
    Se espera que el RUT ya venga en formato 'XXXXXXXX-Y' (sin puntos, con guion).
    """
    api_key = settings.SIMPLEAPI_API_KEY

    # Según la documentación de SimpleAPI v2, el RUT en la URL DEBE incluir el guion.
    # El 'rut' que llega a esta función ya viene con el guion desde el formulario.
    rut_para_api = rut.strip() # Usamos .strip() por precaución, pero lo importante es mantener el guion.
    
    URL_BASE_V2 = "https://rut.simpleapi.cl/v2" 
    
    headers = {
        "Authorization": api_key, 
        "Content-Type": "application/json" 
    }

    # La URL se construye CON el guion, tal como el ejemplo de la documentación.
    url_completa = f"{URL_BASE_V2}/{rut_para_api}"

    # ******** AQUÍ ESTÁN LOS PRINT() ADICIONALES PARA DEPURACIÓN ********
    print(f"DEBUG_PRINT: RUT recibido en validar_rut_empresa: '{rut}'")
    print(f"DEBUG_PRINT: RUT para la API (después de strip): '{rut_para_api}'")
    print(f"DEBUG_PRINT: URL completa generada para SimpleAPI: '{url_completa}'")
    # *******************************************************************

    try:
        logger.debug(f"Intentando conectar a: {url_completa}")
        logger.debug(f"Usando API Key (primeros 5 caracteres): {api_key[:5]}...")

        response = requests.get(url_completa, headers=headers, timeout=60) 
        response.raise_for_status()

        data = response.json()

        if data and data.get('rut') and data.get('razonSocial'):
            return {'valida': True, 'datos': data}
        else:
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
        return {'valida': False, 'mensaje': 'La validación del RUT con SimpleAPI excedió el tiempo de espera. La API tarda en responder.'}
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error general de request con SimpleAPI para RUT {rut}: {req_err}")
        return {'valida': False, 'mensaje': f'Error inesperado al comunicarse con SimpleAPI: {req_err}'}
    except ValueError as json_err:
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


# --- Nuevos Umbrales desde settings.py ---
UMBRAL_APROBADO_NORMAL = getattr(settings, 'UMBRAL_IA_APROBADO_NORMAL', 70.00)
UMBRAL_APROBADO_URGENTE = getattr(settings, 'UMBRAL_IA_APROBADO_URGENTE', 55.00)

# Constante para el rechazo automático por distancia
UMBRAL_RECHAZO_DISTANCIA_KM = 300 # Nuevo umbral de 300 km

class CustomJsonEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            # Convierte Decimal a string para preservar la precisión
            return str(obj)
        elif isinstance(obj, (date, datetime)):
            # Convierte objetos date y datetime a formato ISO (string)
            return obj.isoformat()
        # Deja que la implementación por defecto maneje otros tipos
        return json.JSONEncoder.default(self, obj)
    
# Función para calcular distancia (adaptada de tu mapa.html)
def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en kilómetros entre dos puntos geográficos (latitud, longitud)
    utilizando la API de Google Maps Distance Matrix.
    Retorna la distancia en km o None si hay un error.
    """
    if not GMAPS_API_KEY:
        logger.warning("GMAPS_API_KEY no configurada. No se puede calcular la distancia.")
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

def queue_postulacion_analysis(postulacion_instance, delay_seconds=0):
    """
    Función para encolar el análisis de IA de una postulación.
    
    Args:
        postulacion_instance: Instancia de Postulacion
        delay_seconds: Segundos de retraso antes de ejecutar la tarea (opcional)
    
    Returns:
        dict: Resultado del encolado
    """
    if not postulacion_instance or not isinstance(postulacion_instance, Postulacion):
        return {'status': 'error', 'message': 'Instancia de Postulacion inválida para encolado.'}
    
    try:
        # Actualizar estado a pendiente antes de encolar
        postulacion_instance.estado_ia_analisis = 'pendiente'
        postulacion_instance.razon_estado_ia = "Análisis IA encolado para procesamiento asíncrono"
        postulacion_instance.save(update_fields=['estado_ia_analisis', 'razon_estado_ia'])
        
        # Importar la tarea aquí para evitar importaciones circulares
        from .tasks import analizar_postulacion_ia_task
        
        # Encolar la tarea
        if delay_seconds > 0:
            task_result = analizar_postulacion_ia_task.delay(
                postulacion_instance.id,
                countdown=delay_seconds
            )
        else:
            task_result = analizar_postulacion_ia_task.delay(postulacion_instance.id)
        
        logger.info(f"Análisis IA encolado para postulación ID {postulacion_instance.id}")
        
        return {
            'status': 'queued',
            'message': 'Análisis IA encolado exitosamente',
            'task_id': str(task_result) if hasattr(task_result, '__str__') else 'unknown'
        }
        
    except Exception as e:
        logger.error(f"Error al encolar análisis IA para postulación ID {postulacion_instance.id}: {e}", exc_info=True)
        
        # Revertir estado en caso de error
        try:
            postulacion_instance.estado_ia_analisis = 'error_analisis'
            postulacion_instance.razon_estado_ia = f"Error al encolar análisis IA: {str(e)}"
            postulacion_instance.save(update_fields=['estado_ia_analisis', 'razon_estado_ia'])
        except:
            pass
        
        return {'status': 'error', 'message': f'Error al encolar análisis IA: {str(e)}'}

def queue_batch_postulacion_analysis(postulacion_ids, delay_seconds=0):
    """
    Función para encolar análisis de múltiples postulaciones en lote.
    
    Args:
        postulacion_ids: Lista de IDs de postulaciones
        delay_seconds: Segundos de retraso antes de ejecutar la tarea (opcional)
    
    Returns:
        dict: Resultado del encolado
    """
    if not postulacion_ids or not isinstance(postulacion_ids, list):
        return {'status': 'error', 'message': 'Lista de IDs de postulaciones inválida.'}
    
    try:
        # Actualizar estado de todas las postulaciones a pendiente
        postulaciones = Postulacion.objects.filter(id__in=postulacion_ids)
        postulaciones.update(
            estado_ia_analisis='pendiente',
            razon_estado_ia='Análisis IA encolado para procesamiento en lote'
        )
        
        # Importar la tarea aquí para evitar importaciones circulares
        from .tasks import procesar_lote_postulaciones_task
        
        # Encolar la tarea en lote
        if delay_seconds > 0:
            task_result = procesar_lote_postulaciones_task.delay(
                postulacion_ids,
                countdown=delay_seconds
            )
        else:
            task_result = procesar_lote_postulaciones_task.delay(postulacion_ids)
        
        logger.info(f"Análisis IA en lote encolado para {len(postulacion_ids)} postulaciones")
        
        return {
            'status': 'queued',
            'message': f'Análisis IA en lote encolado exitosamente para {len(postulacion_ids)} postulaciones',
            'task_id': str(task_result) if hasattr(task_result, '__str__') else 'unknown',
            'count': len(postulacion_ids)
        }
        
    except Exception as e:
        logger.error(f"Error al encolar análisis IA en lote: {e}", exc_info=True)
        return {'status': 'error', 'message': f'Error al encolar análisis IA en lote: {str(e)}'}
    

def evaluate_postulacion_with_gemini(postulacion_instance):
    """
    Evalúa la idoneidad de un candidato (Postulacion) para una oferta de trabajo
    utilizando información del CV, Certificado de Antecedentes y la Oferta de Trabajo.
    Calcula un puntaje de 0-100 y almacena razones.
    """
    if not postulacion_instance or not isinstance(postulacion_instance, Postulacion):
        # Esta función ahora devuelve un diccionario con 'status' para el handler
        return {'status': 'error_analisis', 'message': 'Instancia de Postulacion inválida para evaluación.', 'puntaje': None, 'razones': {}}

    # Acceder a los modelos relacionados
    persona = postulacion_instance.persona
    oferta = postulacion_instance.oferta
    cv = getattr(persona, 'cv', None)
    certificado = getattr(persona, 'certificado_antecedentes', None)

    # Inicializar puntaje y razones, y los nuevos campos de estado de IA
    puntaje_ia = 0
    razones_ia = {}
    
    # Establecer estado inicial del análisis IA
    # Esto ya se hizo en tasks.py antes de llamar a esta función, pero lo mantenemos para robustez
    # y porque esta es la función que lo "pone en marcha" si se llama directamente.
    postulacion_instance.estado_ia_analisis = 'en_analisis'
    postulacion_instance.save(update_fields=['estado_ia_analisis']) # Guardar el estado inicial

    # --- 1. Verificación de distancia (Rechazo automático si > UMBRAL_RECHAZO_DISTANCIA_KM) ---
    user_lat = persona.usuario.latitud
    user_lon = persona.usuario.longitud

    if oferta.latitud and oferta.longitud and user_lat and user_lon:
        distance_km = calculate_distance(user_lat, user_lon, oferta.latitud, oferta.longitud)

        if distance_km is not None:
            if distance_km > UMBRAL_RECHAZO_DISTANCIA_KM:
                # Si hay rechazo automático por distancia, se actualizan los campos de IA y se retorna.
                # NO se modifica postulacion_instance.estado
                postulacion_instance.rechazo_automatico_distancia = True
                postulacion_instance.razones_ia['rechazo_distancia'] = f"Distancia ({distance_km:.2f} km) excede el límite de {UMBRAL_RECHAZO_DISTANCIA_KM} km."
                postulacion_instance.puntaje_ia = 0
                postulacion_instance.estado_ia_analisis = 'rechazado_ia'
                postulacion_instance.razon_estado_ia = f"Rechazo automático: Distancia ({distance_km:.2f} km) excede el límite de {UMBRAL_RECHAZO_DISTANCIA_KM} km."
                postulacion_instance.save(update_fields=[
                    'rechazo_automatico_distancia',
                    'razones_ia',
                    'puntaje_ia',
                    'estado_ia_analisis',
                    'razon_estado_ia'
                ])
                logger.info(f"Postulación ID {postulacion_instance.id} rechazada automáticamente por distancia: {distance_km:.2f} km.")
                # El return debe coincidir con el formato que espera tasks.py
                return {
                    'status': 'rechazado_ia',
                    'message': 'Rechazado automáticamente por distancia.',
                    'puntaje': 0,
                    'razones': postulacion_instance.razones_ia # Devuelve las razones actualizadas
                }
            else:
                razones_ia['distancia_km'] = f"{distance_km:.2f} km"
        else:
            logger.warning(f"No se pudo calcular la distancia para postulación ID {postulacion_instance.id}. Continuando sin chequeo de distancia.")
            razones_ia['distancia_error'] = "No se pudo calcular la distancia para evaluación."
    else:
        logger.warning(f"Coordenadas de usuario o oferta incompletas para calcular distancia para Postulación ID {postulacion_instance.id}.")
        razones_ia['distancia_error'] = "Coordenadas incompletas para cálculo de distancia."

    # --- 2. Recopilar toda la información para la IA ---
    # ... (Esta parte sigue siendo exactamente igual) ...
    person_info = {
        "nombres": persona.nombres,
        "apellidos": persona.apellidos,
        "rut_perfil": persona.usuario.username,
        "email_perfil": persona.usuario.correo,
        "telefono_perfil": persona.usuario.telefono,
        "direccion_perfil": persona.usuario.direccion,
        "latitud_perfil": user_lat,
        "longitud_perfil": user_lon,
        "fecha_nacimiento_perfil": str(persona.fecha_nacimiento) if persona.fecha_nacimiento else None,
        "nacionalidad": persona.nacionalidad,
    }

    cv_info = cv.datos_analizados_ia if cv else {}
    
    cert_info = certificado.datos_analizados_ia if certificado else {}
    if certificado:
        cert_info['estado_procesamiento'] = certificado.processing_status
        if certificado.processing_status == EstadoDocumento.REJECTED:
            cert_info['razon_rechazo'] = certificado.rejection_reason

    offer_info = {
        "titulo": oferta.nombre,
        "descripcion": oferta.descripcion,
        "requisitos": oferta.requisitos,
        "beneficios": oferta.beneficios,
        "salario": oferta.salario,
        "tipo_contrato": oferta.get_tipo_contrato_display(),
        "ubicacion_oferta_direccion": oferta.direccion,
        "latitud_oferta": oferta.latitud,
        "longitud_oferta": oferta.longitud,
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
        "validaciones_previas": razones_ia
    }

    prompt = (
        f"Eres un experto en reclutamiento y análisis de perfiles para trabajos esporádicos y de largo plazo "
        f"(como bartender, garzón, eventos, carpintería, etc.). Tu tarea es evaluar la idoneidad de un candidato "
        f"para una oferta de trabajo específica, basándote en la siguiente información estructurada en JSON. "
        f"Asigna un 'puntaje_ia' de 0 a 100, donde 100 es una coincidencia perfecta y 0 es una no coincidencia o rechazo total. "
        f"Considera los siguientes criterios, dándoles el peso adecuado:\n"
        f"- Coincidencia de habilidades y experiencia del CV con los requisitos de la oferta.\n"
        f"- Nivel educativo relevante del CV.\n"
        f"- Idiomas (especialmente inglés si es relevante para el puesto).\n"
        f"- Coherencia y profesionalismo general del CV (resumen, formato, etc.).\n"
        f"- **Estado y contenido del certificado de antecedentes: Un certificado rechazado por antecedentes negativos es un rechazo crítico.**\n"
        f"- Coherencia de datos personales entre perfil, CV y certificado.\n"
        f"- Otros factores relevantes que puedas inferir (ej. experiencia en proyectos similares).\n"
        f"- Considera la distancia entre la ubicación del candidato y la oferta. Se prefiere menor distancia.\n"
        f"- **Si la oferta es URGENTE, sé más permisivo en la evaluación, buscando una 'buena' coincidencia en lugar de 'perfecta'.**\n"
        f"- Prioriza la claridad y concisión en las razones del puntaje.\n"
        f"- Si no hay CV o certificado, evalúa el perfil base y la oferta, y ajusta el puntaje de forma conservadora.\n\n"
        f"Proporciona la respuesta en formato JSON, incluyendo 'puntaje_ia' y 'razones_ia' (un diccionario con 'fortalezas', 'oportunidades_mejora' y 'resumen_coincidencia').\n\n"
        f"Datos para el análisis:\n{json.dumps(full_input_for_gemini, indent=2, cls=CustomJsonEncoder)}\n\n"
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
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)

        response_text = response.text.strip()
        if response_text.startswith("```json") and response_text.endswith("```"):
            json_str = response_text[7:-3].strip()
        else:
            json_str = response_text
        
        ia_analysis_result = json.loads(json_str)

        new_puntaje = ia_analysis_result.get('puntaje_ia')
        new_razones = ia_analysis_result.get('razones_ia')

        if new_puntaje is not None:
            try:
                new_puntaje = int(new_puntaje)
                if not (0 <= new_puntaje <= 100):
                    raise ValueError("Puntaje IA fuera de rango (0-100).")
            except ValueError:
                logger.error(f"Puntaje IA inválido para Postulación ID {postulacion_instance.id}: {new_puntaje}")
                new_puntaje = None
        
        # --- Determinar el umbral de aprobación según si la oferta es urgente o no ---
        umbral_aprobacion = UMBRAL_APROBADO_URGENTE if oferta.urgente else UMBRAL_APROBADO_NORMAL

        with transaction.atomic():
            postulacion_instance.puntaje_ia = new_puntaje
            if new_razones and isinstance(new_razones, dict):
                postulacion_instance.razones_ia.update(new_razones)

            # Lógica para determinar estado_ia_analisis y razon_estado_ia
            # NO SE MODIFICA postulacion_instance.estado AQUÍ
            if certificado and certificado.processing_status == EstadoDocumento.REJECTED:
                postulacion_instance.estado_ia_analisis = 'rechazado_ia'
                postulacion_instance.razon_estado_ia = f"Certificado de antecedentes rechazado: {certificado.rejection_reason}"
                # REMOVIDO: postulacion_instance.estado = 'rechazado'
            elif new_puntaje is not None and new_puntaje < umbral_aprobacion:
                postulacion_instance.estado_ia_analisis = 'rechazado_ia'
                postulacion_instance.razon_estado_ia = f"Puntaje de idoneidad IA muy bajo ({new_puntaje}) para esta oferta (umbral: {umbral_aprobacion})."
                # REMOVIDO: postulacion_instance.estado = 'rechazado'
            elif new_puntaje is not None and new_puntaje >= umbral_aprobacion:
                postulacion_instance.estado_ia_analisis = 'aprobado_ia'
                postulacion_instance.razon_estado_ia = "Candidato apto según criterios de la IA."
                # REMOVIDO: postulacion_instance.estado = 'revisado'
            else: # Si el puntaje es None o hubo algún problema que no sea un error de JSON
                postulacion_instance.estado_ia_analisis = 'error_analisis'
                postulacion_instance.razon_estado_ia = "El análisis IA no pudo determinar un puntaje válido."
                # REMOVIDO: postulacion_instance.estado = 'error'

            # Guardamos solo los campos de IA y el de rechazo automático por distancia
            postulacion_instance.save(update_fields=[
                'puntaje_ia',
                'razones_ia',
                'estado_ia_analisis',
                'razon_estado_ia',
                'rechazo_automatico_distancia' # Mantenemos este, ya que es parte de la lógica de rechazo IA
            ])
            logger.info(f"Postulación de {persona.usuario.username} a {oferta.nombre} (ID: {postulacion_instance.id}) evaluada con IA. Puntaje: {new_puntaje}, Estado IA: {postulacion_instance.estado_ia_analisis}, Umbral Usado: {umbral_aprobacion}.")

        # Este return es lo que tasks.py espera para su lógica de logs y respuesta HTTP
        return {
            'status': postulacion_instance.estado_ia_analisis, # Asegura que el status devuelto es el que se guardó
            'puntaje': new_puntaje,
            'razones': new_razones,
            'message': postulacion_instance.razon_estado_ia # Devuelve la razón que se guardó
        }

    except json.JSONDecodeError as e:
        postulacion_instance.estado_ia_analisis = 'error_analisis'
        postulacion_instance.razon_estado_ia = f"Error de formato JSON en la respuesta de la IA: {e}"
        # REMOVIDO: postulacion_instance.estado = 'error'
        postulacion_instance.save(update_fields=['estado_ia_analisis', 'razon_estado_ia']) # Guardar solo campos IA
        logger.error(f"Error al decodificar JSON de Gemini para Postulación ID {postulacion_instance.id}: {e}\nRespuesta recibida: {response_text[:500]}", exc_info=True)
        return {'status': 'error_analisis', 'message': f'Error al procesar Postulación con IA (JSON inválido): {e}', 'puntaje': None, 'razones': {}}
    except Exception as e:
        postulacion_instance.estado_ia_analisis = 'error_analisis'
        postulacion_instance.razon_estado_ia = f"Error inesperado durante el procesamiento de la Postulación: {e}"
        # REMOVIDO: postulacion_instance.estado = 'error'
        postulacion_instance.save(update_fields=['estado_ia_analisis', 'razon_estado_ia']) # Guardar solo campos IA
        logger.error(f"Error inesperado al evaluar Postulación con Gemini (Postulación ID: {postulacion_instance.id}): {e}", exc_info=True)
        return {'status': 'error_analisis', 'message': f'Error al procesar Postulación con IA: {e}', 'puntaje': None, 'razones': {}}

