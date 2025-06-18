import functions_framework
from google.cloud import storage
import vertexai
from vertexai.generative_models import GenerativeModel
import json
import os
# import PyPDF2 # Ya no lo usaremos directamente para PDFs, pero lo mantenemos por si acaso para otros casos.
from docx import Document
import io
import requests
import datetime
import time
import re
from urllib.parse import urlparse   

# --- Importar las librerías necesarias ---
from google.cloud import vision
import fitz # Importa PyMuPDF
from PIL import Image # Necesario para manejar las imágenes generadas por PyMuPDF
import numpy as np # Puede ser útil para manipulación de imagen, aunque no estrictamente necesario si Vision API acepta bytes

# --- Configurar el logger estándar de Python ---
import logging
logger = logging.getLogger(__name__)
logger.setLevel(os.environ.get('LOG_LEVEL', 'INFO').upper())

# --- LOGS PARA DEPURACIÓN EN LA INICIALIZACIÓN ---
logger.info("!!! DETECTIVE LOG: Script main.py started execution. !!!")

# --- Configuración de la IA (Google Gemini / Vertex AI) ---
_model = None

try:
    project_id = os.environ.get('GCP_PROJECT')
    # Asegúrate de que la región sea compatible con Vertex AI y Gemini
    region = os.environ.get('GCP_REGION', 'us-east1') 

    logger.info(f"INFO: Initializing Vertex AI with project: {project_id}, region: {region}")
    vertexai.init(project=project_id, location=region)
    
    _model = GenerativeModel("gemini-2.0-flash-001") 
    logger.info("INFO: Vertex AI and Gemini 2.0 Flash model initialized successfully.")
except Exception as e:
    logger.error(f"ERROR: Failed to initialize Vertex AI/Gemini: {e}")


# Cliente de Google Cloud Storage
storage_client = storage.Client()
logger.info("INFO: Google Cloud Storage client initialized.")

# Cliente de Google Cloud Vision (¡NUEVO!)
vision_client = vision.ImageAnnotatorClient()
logger.info("INFO: Google Cloud Vision client initialized.")

# --- CONSTANTES DE PROMPTS Y CONFIGURACIÓN (se mantienen igual) ---

CV_VALIDATION_PROMPT = """Analiza el siguiente texto y determina si corresponde a un Currículum Vitae (CV) o no. Responde únicamente 'SI_CV' si es un CV, y 'NO_CV' si no. Si tienes dudas o es contenido irrelevante, responde 'NO_CV'.
\n\n{document_text}"""

CERTIFICATE_VALIDATION_PROMPT = """Analiza el siguiente texto y determina si corresponde a un Certificado de Antecedentes (también conocido como Certificado de Penales o Antecedentes Penales). Busca frases como "Certificado de Antecedentes", "Registro Civil", "sin anotaciones", "anotaciones vigentes", "Cédula de Identidad". Responde únicamente 'SI_CERTIFICADO' si es un Certificado de Antecedentes, y 'NO_CERTIFICADO' si no. Si tienes dudas o es contenido irrelevante, responde 'NO_CERTIFICADO'.
\n\n{document_text}"""

CERTIFICATE_DATA_EXTRACTION_PROMPT = """
Eres un asistente experto en extracción de información de Certificados de Antecedentes Chilenos.
Tu tarea es extraer los datos clave del siguiente texto del certificado y formatearlos como un objeto JSON estricto.
Asegúrate de que la salida sea ÚNICAMENTE el JSON válido, sin ningún texto adicional antes o después.

Sigue estas reglas para la extracción:
1.  `rut`: str, El RUT o Cédula de Identidad de la persona. Busca formatos como "R.U.N.: X.XXX.XXX-X" o "XXXXXXXX-X". Formato limpio sin puntos y con guion (ej. "12345678-K"). Si no se encuentra, `null`.
2.  `nombre_completo`: str, Nombre completo de la persona tal como aparece en el certificado (ej. "Juan Antonio Pérez Díaz"). Puede aparecer bajo "NOMBRE". Si no se encuentra, `null`.
3.  `fecha_emision`: str, Fecha de emisión del certificado. Busca el texto "FECHA EMISIÓN:". Formato "YYYY-MM-DD". Si solo hay día y mes, asume el año actual si no se especifica. Si no se encuentra, `null`.
4.  `numero_documento`: str, Número de folio o de documento del certificado. Busca el texto "FOLIO:". Si no se encuentra, `null`.
5.  `tiene_anotaciones_vigentes`: bool, `true` si el certificado indica que tiene "anotaciones vigentes", "con anotaciones" o similar. `false` si dice "sin anotaciones", "sin antecedentes" o similar. Si no se puede determinar claramente, `null`. Prioriza las secciones "REGISTRO GENERAL DE CONDENAS" y "REGISTRO ESPECIAL DE CONDENAS".
6.  `institucion_emisora`: str, Nombre de la institución que emite el certificado. Busca "SERVICIO DE REGISTRO CIVIL E IDENTIFICACIÓN" o "Registro Civil e Identificación". Si no se encuentra, `null`.

Aquí está el texto del Certificado de Antecedentes:\n\n{certificate_text}
"""

# --- Funciones de Extracción de Datos con IA (se mantienen igual) ---
def extract_cv_data(cv_text):
    logger.info("INFO: Extracting CV data with AI using improved prompt...")
    prompt = f"""
    Eres un asistente experto en extracción de información de Currículums Vitae (CVs).
    Tu tarea es extraer los datos clave del siguiente texto de CV y formatearlos como un objeto JSON estricto.
    Asegúrate de que la salida sea ÚNICAMENTE el JSON válido, sin ningún texto adicional antes o después.

    Sigue estas reglas para la extracción:
    1.  **Datos Personales**:
        -   `nombre_completo`: str, Nombre y apellidos del candidato (ej. "Juan Pérez"). Si no se encuentra, `null`.
        -   `email`: str, Dirección de correo electrónico de contacto (ej. "juan.perez@example.com"). Si no se encuentra, `null`.
        -   `telefono`: str, Número de teléfono de contacto (ej. "+56 9 12345678", "555-1234"). Formato lo más estandarizado posible. Si no se encuentra, `null`.
        -   `fecha_nacimiento`: str, Fecha de nacimiento en formato "YYYY-MM-DD" si se encuentra. Si no, `null`.
        -   `rut_o_dni`: str, Identificador nacional (RUT en Chile, DNI en otros). Formato limpio sin puntos y con guion (ej. "12345678-K"). Si no se encuentra, `null`.

    2.  **Resumen Ejecutivo / Perfil Profesional**:
        -   `resumen_ejecutivo`: str, Un párrafo o cadena de texto que describe el perfil profesional, objetivos o un "acerca de mí". Si no se encuentra, `null`.

    3.  **Experiencia Laboral**:
        -   `experiencia_laboral`: array de objetos. Cada objeto representa un puesto. Si no hay experiencia, un array vacío `[]`.
            -   `puesto`: str, Título del puesto ocupado (ej. "Ingeniero de Software Senior").
            -   `empresa`: str, Nombre de la empresa.
            -   `ciudad`: str, Ciudad donde se ubicaba el puesto (opcional, `null` si no se encuentra).
            -   `pais`: str, País donde se ubicaba el puesto (opcional, `null` si no se encuentra).
            -   `fecha_inicio`: str, Fecha de inicio en formato "YYYY-MM-DD" (si solo es año, "YYYY-01-01").
            -   `fecha_fin`: str, Fecha de fin en formato "YYYY-MM-DD" (si solo es año, "YYYY-12-31"). Si es "Actual" o "Presente", usa `null`.
            -   `actualmente_aqui`: bool, `true` si la fecha de fin es "Actual" o "Presente", `false` en caso contrario.
            -   `descripcion_logros_responsabilidades`: str, Lista de logros o responsabilidades unidas en un solo párrafo, o `null` si no hay.

    4.  **Educación**:
        -   `educacion`: array de objetos. Cada objeto representa un título o curso. Si no hay educación, un array vacío `[]`.
            -   `titulo_grado`: str, Título o grado obtenido (ej. "Máster en Ciencias de la Computación").
            -   `institucion`: str, Nombre de la institución educativa.
            -   `ciudad`: str, Ciudad de la institución (opcional, `null` si no se encuentra).
            -   `pais`: str, País de la institución (opcional, `null` si no se encuentra).
            -   `fecha_inicio`: str, Fecha de inicio (ej. "YYYY-MM-DD"). Si solo es año, "YYYY-01-01". Si no se encuentra, `null`.
            -   `fecha_fin`: str, Fecha de fin (ej. "YYYY-MM-DD"). Si solo es año, "YYYY-12-31". Si no se encuentra, `null`.
            -   `descripcion_extra`: str, Cualquier descripción adicional sobre el estudio.

    5.  **Habilidades**:
        -   `habilidades`: object. **Siempre debe ser un objeto JSON.**
            -   Si no se encuentran habilidades, este objeto debe estar vacío: `'{{{{}}}}'`, **NO `null` ni una cadena vacía.**
            -   Organiza las habilidades por categorías si es posible (ej. "programacion", "herramientas", "blandas"). Si no hay categorías claras, usa una única categoría llamada `"otras"` que contenga un array de strings.
            -   Ejemplo de un objeto de habilidades con categorías:
                `"habilidades": {{{{ "programacion": ["Python", "Java"], "idiomas_tecnicos": ["SQL", "NoSQL"], "blandas": ["Comunicación", "Liderazgo"] }}}} `
            -   Ejemplo de un objeto de habilidades sin categorías claras:
                `"habilidades": {{{{"otras": ["Negociación", "Office 365", "Ventas"]}}}}`

    6.  **Idiomas**:
        -   `idiomas`: array de objetos. Si no hay idiomas, un array vacío `[]`.
            -   `nombre`: str (ej. "Español").
            -   `nivel`: str (ej. "Nativo", "Fluido", "Intermedio", "Básico").

    **Formato de Fechas:**
    -   Siempre que sea posible, convierte fechas a formato "YYYY-MM-DD".
    -   Si solo se menciona el año, usa "YYYY-01-01" para fecha_inicio y "YYYY-12-31" para fecha_fin.
    -   Si el texto indica "Actualidad" o "Presente" para `fecha_fin`, el valor debe ser `null` y `actualmente_aqui` debe ser `true`.

    **Ejemplo de Estructura JSON de Salida (para referencia):**
    ```json
    {{{{
        "datos_personales": {{{{
            "nombre_completo": "Juan Pérez",
            "email": "juan.perez@example.com",
            "telefono": "+1234567890",
            "fecha_nacimiento": "1990-05-15",
            "rut_o_dni": "12345678-K"
        }}}},
        "resumen_ejecutivo": "Profesional con experiencia en...",
        "experiencia_laboral": [
            {{{{
                "puesto": "Desarrollador Senior",
                "empresa": "Tech Solutions",
                "ciudad": "Santiago",
                "pais": "Chile",
                "fecha_inicio": "2020-01-01",
                "fecha_fin": null,
                "actualmente_aqui": true,
                "descripcion_logros_responsabilidades": "Desarrollo de nuevas funcionalidades..."
            }}}},
            {{{{
                "puesto": "Desarrollador Junior",
                "empresa": "Startup Innovadora",
                "ciudad": "Valparaíso",
                "pais": "Chile",
                "fecha_inicio": "2018-03-01",
                "fecha_fin": "2019-12-31",
                "actualmente_aqui": false,
                "descripcion_logros_responsabilidades": "Participación en el diseño de..."
            }}}}
        ],
        "educacion": [
            {{{{
                "titulo_grado": "Ingeniería en Software",
                "institucion": "Universidad Mayor",
                "ciudad": "Santiago",
                "pais": "Chile",
                "fecha_inicio": "2014-03-01",
                "fecha_fin": "2019-12-31",
                "descripcion_extra": "Especialización en inteligencia artificial."
            }}}}
        ],
        "habilidades": {{{{
            "programacion": ["Python", "JavaScript", "SQL"],
            "herramientas": ["Docker", "Git", "Jira"],
            "blandas": ["Trabajo en equipo", "Resolución de problemas"]
        }}}},
        "idiomas": [
            {{{{ "nombre": "Español", "nivel": "Nativo" }}}},
            {{{{ "nombre": "Inglés", "nivel": "Fluido" }}}}
        ]
    }}}}
    ```
    Aquí está el texto del CV:\n\n{cv_text}
    """

    response_text = call_gemini_api(prompt)
    if response_text:
        try:
            json_match = re.search(r"```json\n(.*?)```", response_text, re.DOTALL)
            if json_match:
                json_string = json_match.group(1)
                logger.debug("JSON extracted from code block.")
            else:
                start_index = response_text.find('{')
                end_index = response_text.rfind('}') + 1
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_string = response_text[start_index:end_index]
                    logger.debug("JSON extracted by finding braces.")
                else:
                    raise ValueError("No valid JSON structure found in AI response.")

            logger.debug(f"JSON extracted by AI (first 200 chars): {json_string[:200]}...")
            return json.loads(json_string)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from AI: {e}")
            logger.error(f"Raw AI response (potential JSON issue): {response_text}")
            return None
        except ValueError as e:
            logger.error(f"{e}")
            logger.error(f"Raw AI response (no JSON found): {response_text}")
            return None
    return None

def extract_certificate_data(certificate_text):
    """Extrae información estructurada de un Certificado de Antecedentes usando Gemini."""
    logger.info("INFO: Extracting certificate data with AI...")
    prompt = CERTIFICATE_DATA_EXTRACTION_PROMPT.format(certificate_text=certificate_text)
    
    logger.debug(f"Prompt para certificado (primeras 500 chars): {prompt[:500]}...") 
    
    response_text = call_gemini_api(prompt)
    
    logger.debug(f"Respuesta cruda de Gemini para certificado (primeras 500 chars): {response_text[:500]}...") 
    
    if response_text:
        try:
            json_match = re.search(r"```json\n(.*?)```", response_text, re.DOTALL)
            if json_match:
                json_string = json_match.group(1)
                logger.debug("JSON extracted from code block for certificate.") 
            else:
                start_index = response_text.find('{')
                end_index = response_text.rfind('}') + 1
                if start_index != -1 and end_index != -1 and start_index < end_index:
                    json_string = response_text[start_index:end_index]
                    logger.debug("JSON extracted by finding braces for certificate.") 
                else:
                    raise ValueError("No valid JSON structure found in AI response for certificate.")
            
            logger.debug(f"Certificate JSON extracted by AI (first 200 chars): {json_string[:200]}...")
            
            parsed_json = json.loads(json_string)
            
            logger.debug(f"Parsed Certificate JSON: {parsed_json}") 
            
            return parsed_json
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from AI for certificate: {e}")
            logger.error(f"Raw AI response (potential JSON issue): {response_text}")
            return None
        except ValueError as e:
            logger.error(f"{e}")
            logger.error(f"Raw AI response (no JSON found for certificate): {response_text}")
            return None
    logger.warning("Gemini API response for certificate was empty.") 
    return None

# --- Funciones de Warm-up y Reintentos (se mantienen igual) ---
def warm_up_django_service(django_base_url):
    if not django_base_url:
        logger.warning("Django base URL not configured, skipping warm-up")
        return
    try:
        logger.info(f"INFO: Warming up Django service at {django_base_url}")
        response = requests.head(django_base_url, timeout=45) 
        logger.info(f"INFO: Django warm-up response: {response.status_code}")
        time.sleep(3)
    except Exception as e:
        logger.warning(f"Django warm-up failed: {e}, but continuing...")

def send_to_django_with_retries(django_api_url, payload, max_retries=5):
    for attempt in range(max_retries):
        try:
            logger.info(f"INFO: Sending to Django API, attempt {attempt + 1}/{max_retries}")
            timeout = 90 if attempt < 2 else 45
            headers = {'Content-Type': 'application/json'}
            response = requests.post(
                django_api_url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            if response.status_code == 200:
                logger.info(f"Successfully sent to Django API on attempt {attempt + 1}")
                return response
            else:
                logger.warning(f"Django API returned status {response.status_code} on attempt {attempt + 1}")
                logger.debug(f"Response content: {response.text[:500]}")
        except requests.exceptions.Timeout:
            logger.warning(f"Timeout on attempt {attempt + 1} (service might be cold starting or overloaded)")
        except requests.exceptions.ConnectionError as e:
            logger.warning(f"Connection error on attempt {attempt + 1}: {e} (Django service might be down or unreachable)")
        except requests.exceptions.RequestException as e:
            logger.warning(f"General request failed on attempt {attempt + 1}: {e}")
        if attempt < max_retries - 1:
            wait_time = (2 ** attempt) + 2 
            logger.info(f"Waiting {wait_time} seconds before retry...")
            time.sleep(wait_time)
    raise Exception(f"Failed to send to Django API after {max_retries} attempts")

# --- Funciones de Extracción de Texto (¡MODIFICADAS AQUI!) ---

def extract_text_from_docx(docx_file_obj):
    """Extrae texto de un objeto de archivo DOCX en memoria."""
    logger.debug("Entering extract_text_from_docx.")
    try:
        document = Document(docx_file_obj)
        text = ""
        for paragraph in document.paragraphs:
            text += paragraph.text + "\n"
        logger.debug(f"Text extracted from DOCX (first 200 chars): {text[:200]}...")
        return text
    except Exception as e:
        logger.error(f"Error extracting text from DOCX: {e}")
        return None

def get_document_text_from_gcs_file(bucket_name, file_name):
    """
    Descarga un archivo de GCS y extrae su texto.
    Para PDFs, convierte cada página a imagen con PyMuPDF y luego usa Vision API.
    Para DOCX, usa python-docx.
    """
    logger.info(f"Attempting to get document text from gs://{bucket_name}/{file_name}")
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_name)

    try:
        file_content = blob.download_as_bytes()
        file_extension = file_name.split('.')[-1].lower()

        logger.info(f"Detected file: {file_name} with extension: {file_extension}")

        if file_extension == 'pdf':
            logger.info("INFO: Processing PDF with PyMuPDF for image conversion and then Google Cloud Vision API for OCR.")
            full_pdf_text = []
            
            try:
                # Abrir el documento PDF desde bytes en memoria
                doc = fitz.open(stream=file_content, filetype="pdf")
                logger.info(f"Opened PDF with {doc.page_count} pages using PyMuPDF.")

                for page_num in range(doc.page_count):
                    page = doc.load_page(page_num)
                    
                    # Renderizar la página a un pixmap (imagen en memoria)
                    # Aumentar el zoom para mejor resolución de OCR
                    zoom = 3.0 # Esto simula 300 DPI si el PDF base es 72 DPI. Ajusta si es necesario.
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    
                    # Convertir pixmap a bytes JPEG
                    img_bytes = pix.tobytes("jpeg") # Guarda como JPEG en memoria

                    # Crear un objeto Image para la Vision API a partir de los bytes JPEG
                    image = vision.Image(content=img_bytes)
                    
                    # Realizar la detección de texto en la imagen de la página
                    page_response = vision_client.document_text_detection(image=image)
                    
                    if page_response.full_text_annotation:
                        full_pdf_text.append(page_response.full_text_annotation.text)
                        logger.debug(f"Text extracted from page {page_num + 1} (first 200 chars): {page_response.full_text_annotation.text[:200]}...")
                    else:
                        logger.warning(f"Vision API returned empty text for page {page_num + 1} of PDF: {file_name}")
                        if page_response.error and page_response.error.message:
                            logger.error(f"Vision API response error for page {page_num + 1}: {page_response.error.message}")
                
                doc.close()
                combined_text = "\n".join(full_pdf_text)
                if not combined_text:
                    logger.warning(f"No text extracted from any page of PDF: {file_name}")
                else:
                    logger.info(f"INFO: Successfully extracted text from {len(full_pdf_text)} pages of PDF: {file_name}")
                    logger.debug(f"Combined text from PDF (first 500 chars): {combined_text[:500]}...")
                return combined_text
                
            except fitz.FileDataError as e:
                logger.error(f"ERROR: PyMuPDF could not open PDF file (corrupted or malformed): {e}")
                return None
            except Exception as e:
                logger.error(f"ERROR: An unexpected error occurred during PDF to image conversion or OCR with PyMuPDF/Vision API: {e}")
                return None

        elif file_extension == 'docx':
            return extract_text_from_docx(io.BytesIO(file_content))
        else:
            logger.error(f"Unsupported file format for {file_name}. Only PDF and DOCX are supported.")
            return None
    except Exception as e:
        logger.error(f"ERROR: Error downloading or accessing {file_name} from GCS: {e}")
        return None
    
# --- Funciones de Interacción con la IA (Gemini) ---
def call_gemini_api(prompt):
    if _model is None:
        logger.error("Gemini model not initialized. Cannot call API.")
        return None
        
    logger.debug("Calling Gemini API...")
    try:
        response = _model.generate_content(prompt)
        if response and response.text:
            logger.debug("Gemini API responded with text.")
            return response.text
        else:
            logger.warning("Gemini API responded but generated no text content.")
            return None
    except Exception as e:
        logger.error(f"Error calling Gemini API: {e}")
        return None

def validate_document_type(document_text, validation_prompt_template, expected_response_keyword):
    logger.info("INFO: Validating document type...")
    prompt = validation_prompt_template.format(document_text=document_text)
    response = call_gemini_api(prompt)
    logger.info(f"Document validation raw response: {response}")
    return response and expected_response_keyword in response.strip().upper()

def normalize_rut(rut_string):
    if not rut_string:
        return None
    cleaned_rut = rut_string.replace('.', '').replace('-', '')
    if len(cleaned_rut) > 1:
        body = cleaned_rut[:-1]
        dv = cleaned_rut[-1].upper()
        return f"{body}-{dv}"
    else:
        logger.warning(f"RUT string '{rut_string}' is too short or invalid for normalization.")
    return None


# --- Función Principal (Entrypoint para el evento de Cloud Storage) ---
@functions_framework.cloud_event
def process_document_from_gcs(cloud_event):
    logger.info("!!! DETECTIVE LOG: process_document_from_gcs function entered. Receiving event. !!!")

    data = cloud_event.data
    bucket_name = data.get("bucket")
    file_name = data.get("name")

    if not bucket_name or not file_name:
        logger.error("No bucket name or file name received in event.")
        return "Missing bucket or file name", 400

    gcs_url = f"gs://{bucket_name}/{file_name}"
    logger.info(f"Processing file: {gcs_url}")

    document_type = None
    
    if "cvs/" in file_name.lower():
        document_type = "cv"
    elif "certificados/" in file_name.lower():
        document_type = "CERTIFICADO_ANTECEDENTES"
    else:
        logger.error(f"Unknown document type based on file path: {file_name}. Expected 'cvs/' or 'certificados/'.")
        return "Unknown document type", 400

    DJANGO_RECEIVER_URL = os.environ.get('DJANGO_RECEIVER_URL')
    if not DJANGO_RECEIVER_URL:
        logger.error("La variable de entorno DJANGO_RECEIVER_URL no está configurada. No se puede enviar datos a Django.")
        return f"DJANGO_RECEIVER_URL not configured", 500
    
    django_api_url = DJANGO_RECEIVER_URL
    
    parsed_url = urlparse(DJANGO_RECEIVER_URL)
    django_base_url_for_warmup = f"{parsed_url.scheme}://{parsed_url.netloc}/"
    logger.info(f"Django base URL for warm-up: {django_base_url_for_warmup}")

    warm_up_django_service(django_base_url_for_warmup)

    user_rut = None
    base_file_name = os.path.basename(file_name)
    
    match_rut_prefix = re.match(r'^(\d{1,2}\.?\d{3}\.?\d{3}-?[0-9Kk])_.*', base_file_name, re.IGNORECASE)
    if match_rut_prefix:
        raw_rut = match_rut_prefix.group(1)
        user_rut = normalize_rut(raw_rut)
        logger.info(f"User RUT extracted from filename prefix (raw: {raw_rut}, normalized: {user_rut})")
    else:
        path_parts = file_name.split('/')
        for part in path_parts:
            if re.fullmatch(r'^\d{1,2}\.?\d{3}\.?\d{3}-?[0-9Kk]$', part, re.IGNORECASE):
                user_rut = normalize_rut(part)
                logger.info(f"User RUT extracted from path segment (raw: {part}, normalized: {user_rut})")
                break
        
        if not user_rut:
            logger.warning(f"No clear user_rut pattern found in file path: {file_name}.")

    if not user_rut:
        logger.error(f"Could not determine user_rut for file: {file_name}. Cannot proceed.")
        payload_error_rut = {
            'rut': 'unknown',
            'file_gcs_url': gcs_url,
            'processing_status': 'rejected',
            'rejection_reason': 'No se pudo determinar el RUT del usuario a partir del nombre del archivo.',
            'document_type': document_type
        }
        try:
            send_to_django_with_retries(django_api_url, payload_error_rut)
            return "Missing user RUT, notified Django", 200
        except Exception as e:
            logger.error(f"Also failed to send rejection notification for missing RUT to Django: {e}")
            return "Missing user RUT", 500


    logger.info(f"Final User RUT for processing: {user_rut}")
    logger.info(f"Starting processing for file: {gcs_url} for user_rut: {user_rut}")

    document_text = get_document_text_from_gcs_file(bucket_name, file_name)

    if not document_text:
        logger.error(f"Could not get text from file {file_name}. Terminating processing.")
        payload_error = {
            'rut': user_rut, 
            'file_gcs_url': gcs_url,
            'processing_status': 'rejected',
            'rejection_reason': 'El documento no pudo ser leído o está vacío.',
            'document_type': document_type
        }
        try:
            send_to_django_with_retries(django_api_url, payload_error)
            return "Failed to extract text from document, notified Django", 200
        except Exception as e:
            logger.error(f"Also failed to send rejection notification to Django: {e}")
            return "Failed to extract text from document", 500

    extracted_data = None
    status_to_send = "error"
    reason_to_send = None

    if document_type == "cv":
        is_valid_document = validate_document_type(document_text, CV_VALIDATION_PROMPT, 'SI_CV')
        if is_valid_document:
            logger.info("Document validated as a CV. Proceeding to data extraction...")
            extracted_data = extract_cv_data(document_text)
            status_to_send = "processed" if extracted_data else "rejected"
            reason_to_send = None if extracted_data else "La IA no pudo extraer datos significativos del CV."
        else:
            logger.info("Document is NOT a CV. No data extraction proceeded.")
            status_to_send = "rejected"
            reason_to_send = "El documento no fue identificado como un CV válido por la IA."
            extracted_data = None

    elif document_type == "CERTIFICADO_ANTECEDENTES":
        is_valid_document = validate_document_type(document_text, CERTIFICATE_VALIDATION_PROMPT, 'SI_CERTIFICADO')
        if is_valid_document:
            logger.info("Document validated as a Certificate. Proceeding to data extraction...")
            extracted_data = extract_certificate_data(document_text)
            status_to_send = "processed" if extracted_data else "rejected"
            reason_to_send = None if extracted_data else "La IA no pudo extraer datos significativos del certificado."
        else:
            logger.info("Document is NOT a Certificate. No data extraction proceeded.")
            status_to_send = "rejected"
            reason_to_send = "El documento no fue identificado como un Certificado de Antecedentes válido por la IA."
            extracted_data = None
    
    payload = {
        'rut': user_rut, 
        'file_gcs_url': gcs_url, 
        'document_type': document_type,
        'processing_status': status_to_send,
        'rejection_reason': reason_to_send,
    }
    if extracted_data:
        payload['extracted_data'] = extracted_data 

    logger.debug(f"Sending data to Django API: {django_api_url} with payload (first 500 chars): {json.dumps(payload)[:500]}...")

    try:
        response = send_to_django_with_retries(django_api_url, payload)
        logger.info(f"Document data sent to Django API for user {user_rut} successfully. Status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Failed to send data to Django API for user {user_rut} after all retries: {e}")
        return "Failed to send data to Django", 500 

    logger.info(f"Processing for {file_name} finished.")
    return "OK", 200