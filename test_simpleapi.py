import requests
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Obtener la API Key
SIMPLEAPI_API_KEY = os.getenv('SIMPLEAPI_API_KEY')

if not SIMPLEAPI_API_KEY:
    print("Error: SIMPLEAPI_API_KEY no encontrada en el archivo .env")
    exit()

# *** RUTs DE EMPRESA PARA PRUEBA (puedes probar uno a uno) ***
# RUTs de empresas muy conocidas en Chile
RUTS_A_PROBAR = [
    "77.261.280-K",  # S.A.C.I. Falabella
    "97.000.000-1",  # Banco de Chile
    "60.000.000-0",  # CODELCO (Corporación Nacional del Cobre de Chile)
    "76.082.903-6",  # LATAM Airlines Group S.A.
    "78.008.400-9",  # Empresas CMPC S.A.
    "79.529.200-5",  # S.A. Gasco
    "96.586.600-4",  # Entel S.A.
    "76.000.000-1",  # Un RUT de ejemplo genérico muy usado (podría no estar en SimpleAPI)
]

# Cambia este índice para probar diferentes RUTs de la lista
# Empieza con 0 (Falabella), luego 1 (Banco de Chile), etc.
RUT_ACTUAL_PRUEBA = RUTS_A_PROBAR[0] 

# Limpiar el RUT para el path de la API, quitando puntos y guiones
rut_limpio_para_api = RUT_ACTUAL_PRUEBA.replace('.', '').replace('-', '')

# Nueva URL base del endpoint de SimpleAPI (v2)
URL_BASE_V2 = "https://rut.simpleapi.cl/v2" 
# Construir la URL completa con el RUT en el path
url_completa = f"{URL_BASE_V2}/{rut_limpio_para_api}"


HEADERS = {
    # El valor del header 'Authorization' debe ser solo la API Key, sin 'Bearer '.
    "Authorization": SIMPLEAPI_API_KEY, 
    "Content-Type": "application/json" 
}

print(f"Intentando conectar a: {url_completa}")
print(f"Usando API Key (primeros 5 caracteres): {SIMPLEAPI_API_KEY[:5]}...")

try:
    # Aumentar el tiempo de espera (timeout) a 60 segundos
    response = requests.get(url_completa, headers=HEADERS, timeout=60) # CAMBIO AQUÍ: de 30 a 60
    response.raise_for_status() # Esto levantará una excepción para 4xx/5xx errores HTTP

    print(f"\nRespuesta exitosa (Código {response.status_code}):")
    print(response.json()) 

except requests.exceptions.HTTPError as http_err:
    print(f"\nError HTTP (Código {response.status_code}): {http_err}")
    print(f"Respuesta del servidor: {response.text}")
    if response.status_code == 404:
        print("Este es el error esperado si el RUT no se encuentra en la base de datos de SimpleAPI (v2).")
    elif response.status_code == 401:
        print("Este es el error esperado si la API Key es inválida o el formato del header 'Authorization' es incorrecto.")
    elif response.status_code == 400:
        print("Error 400: Solicitud incorrecta. Posiblemente el formato del RUT en la URL no es el esperado por v2.")
    else:
        print(f"Error HTTP inesperado: {response.status_code} - {response.text}")

except requests.exceptions.ConnectionError as conn_err:
    print(f"\nError de Conexión: {conn_err}")
    print("Parece que no se pudo establecer la conexión al servidor de SimpleAPI.")
    print("Verifica tu conexión a internet, firewall, o si hay un proxy.")

except requests.exceptions.Timeout as timeout_err:
    print(f"\nError de Tiempo de Espera: {timeout_err}")
    print("La solicitud a SimpleAPI tardó demasiado en responder. Es posible que el tiempo de espera sea insuficiente o la API esté lenta.")

except requests.exceptions.RequestException as req_err:
    print(f"\nError Inesperado de requests: {req_err}")
    print("Ocurrió un error desconocido al hacer la solicitud.")

except ValueError as json_err: # Si la respuesta no es un JSON válido
    print(f"\nError al decodificar JSON: {json_err}")
    print(f"Respuesta cruda: {response.text}")

except Exception as e:
    print(f"\nOcurrió un error inesperado: {e}")
