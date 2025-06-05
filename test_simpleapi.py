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

RUT_EMPRESA_PRUEBA = "77.261.280-K" # El RUT que estamos probando
URL_API = f"https://api.simpleapi.cl/api/v1/rut/empresa/{RUT_EMPRESA_PRUEBA}"
HEADERS = {
    "Authorization": f"Bearer {SIMPLEAPI_API_KEY}",
    "Content-Type": "application/json"
}

print(f"Intentando conectar a: {URL_API}")
print(f"Usando API Key (primeros 5 caracteres): {SIMPLEAPI_API_KEY[:5]}...")

try:
    response = requests.get(URL_API, headers=HEADERS, timeout=10) # Añadir timeout
    response.raise_for_status() # Esto levantará una excepción para 4xx/5xx errores HTTP

    print(f"\nRespuesta exitosa (Código {response.status_code}):")
    print(response.json())

except requests.exceptions.HTTPError as http_err:
    print(f"\nError HTTP (Código {response.status_code}): {http_err}")
    print(f"Respuesta del servidor: {response.text}")
    if response.status_code == 404:
        print("Este es el error esperado si el RUT no se encuentra en la base de datos de SimpleAPI.")
    elif response.status_code == 401:
        print("Este es el error esperado si la API Key es inválida.")

except requests.exceptions.ConnectionError as conn_err:
    print(f"\nError de Conexión: {conn_err}")
    print("Parece que no se pudo establecer la conexión al servidor de SimpleAPI.")
    print("Verifica tu conexión a internet, firewall o si hay un proxy.")

except requests.exceptions.Timeout as timeout_err:
    print(f"\nError de Tiempo de Espera: {timeout_err}")
    print("La solicitud a SimpleAPI tardó demasiado en responder.")

except requests.exceptions.RequestException as req_err:
    print(f"\nError Inesperado de requests: {req_err}")
    print("Ocurrió un error desconocido al hacer la solicitud.")

except ValueError as json_err:
    print(f"\nError al decodificar JSON: {json_err}")
    print(f"Respuesta cruda: {response.text}")

except Exception as e:
    print(f"\nOcurrió un error inesperado: {e}")