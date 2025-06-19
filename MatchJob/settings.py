# settings.py

from pathlib import Path
from django.contrib.messages import constants as messages
# from google.oauth2 import service_account # Ya no es estrictamente necesario si usamos impersonación
from dotenv import load_dotenv
import os
from datetime import timedelta
import ssl
import os
from google.auth import default

# --- BASE DIRECTORY ---
BASE_DIR = Path(__file__).resolve().parent.parent

# Cargar variables de entorno del archivo .env (para desarrollo local)
load_dotenv()

# SIMPLEAPI_API_KEY = os.getenv("SIMPLEAPI_API_KEY")
SIMPLEAPI_API_KEY='6647-W930-6391-1081-4347'

# --- MESSAGE TAGS (Django Messages Framework) ---
MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# --- GENERAL SETTINGS ---

# SECRET_KEY: Genera una nueva clave secreta MUY FUERTE para producción
# NUNCA uses esta clave en producción; siempre obtenla de variables de entorno.
SECRET_KEY = os.getenv('SECRET_KEY', 'your-very-strong-and-random-secret-key-for-production') # <-- ¡CAMBIA ESTO EN PRODUCCIÓN!

# DEBUG: Lee el valor de la variable de entorno DJANGO_DEBUG.
# Por defecto es False para producción, pero puedes setear DJANGO_DEBUG=True en tu entorno local.
DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true'
# DEBUG = True # <--- Ahora, el valor de DEBUG se gestiona con la variable de entorno DJANGO_DEBUG

# --- ALLOWED_HOSTS ---
# Obtenemos los hosts de la variable de entorno ALLOWED_HOSTS.
# Si la variable de entorno está vacía o no existe, split(',') devolverá [''].
_allowed_hosts_from_env = os.getenv('ALLOWED_HOSTS', '').split(',')

# Inicializamos ALLOWED_HOSTS como una lista vacía si la variable de entorno estaba vacía.
if _allowed_hosts_from_env == ['']:
    ALLOWED_HOSTS = []
else:
    ALLOWED_HOSTS = _allowed_hosts_from_env

# Lógica condicional para añadir hosts dependiendo del modo DEBUG
if DEBUG:
    # Si DEBUG es True, permitimos todos los hosts en desarrollo
    # (o podemos ser más específicos si queremos, pero '*' es común para desarrollo)
    if not ALLOWED_HOSTS or ALLOWED_HOSTS == ['']:
        ALLOWED_HOSTS = ['*']
    # En DEBUG=True, podrías añadir explícitamente 'localhost' y '127.0.0.1'
    # si no quieres usar '*' y quieres asegurar que estén presentes.
    # if 'localhost' not in ALLOWED_HOSTS: ALLOWED_HOSTS.append('localhost')
    # if '127.0.0.1' not in ALLOWED_HOSTS: ALLOWED_HOSTS.append('127.0.0.1')
else:
    # Si DEBUG es False (producción o pruebas locales de producción)
    # Aseguramos que los hosts locales estén presentes para pruebas si no están ya.
    # Esto es crucial para probar la subida a GCS en local con DEBUG=False.
    if 'localhost' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('localhost')
    if '127.0.0.1' not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append('127.0.0.1')
    
    # Asegúrate de que el dominio de Cloud Run esté siempre en la lista de producción.
    # Se añade solo si no está ya presente en la lista obtenida de la variable de entorno.
    cloud_run_domain = 'matchjob-service-159154155877.southamerica-west1.run.app'
    if cloud_run_domain not in ALLOWED_HOSTS:
        ALLOWED_HOSTS.append(cloud_run_domain)

# --- INSTALLED APPLICATIONS ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles', # Asegúrate de que staticfiles está aquí
    'gestionOfertas',
    'widget_tweaks',
    'storages',
]

# --- MIDDLEWARE ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- URLS AND WSGI ---
ROOT_URLCONF = 'MatchJob.urls'
WSGI_APPLICATION = 'MatchJob.wsgi.application'

# --- TEMPLATES ---
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'], # Directorio para templates globales
        'APP_DIRS': True, # Busca templates en cada app
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# --- DATABASE CONFIGURATION ---
# Configuración de la base de datos (usando variables de entorno para producción)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'BDmatchjob'),
        'USER': os.getenv('DB_USER', 'neondb_owner'),
        'PASSWORD': os.getenv('DB_PASSWORD', 'npg_lU8ucqsIiP6X'), # <-- ¡NUNCA expongas esto directamente!
        'HOST': os.getenv('DB_HOST', 'ep-weathered-sunset-ac0mxs0q-pooler.sa-east-1.aws.neon.tech'),
        'PORT': os.getenv('DB_PORT', '5432'),
        'OPTIONS': {
            'sslmode': 'require',
        },
    }
}

# --- PASSWORD VALIDATORS ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# --- INTERNATIONALIZATION ---
LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# --- GOOGLE CLOUD STORAGE & STATIC/MEDIA FILES CONFIGURATION ---

# Tu ID de proyecto de Google Cloud (necesario para algunas operaciones de GCS)
GS_PROJECT_ID = os.getenv('GS_PROJECT_ID', 'matchjob-458200')

# Nombre del bucket para ARCHIVOS ESTÁTICOS (CSS, JS, imágenes del sitio)
GS_STATIC_BUCKET_NAME = os.getenv('GS_STATIC_BUCKET_NAME', 'matchjob-static-files')

# Nombre del bucket para ARCHIVOS DE MEDIOS (CVs, uploads de usuarios)
GS_MEDIA_BUCKET_NAME = os.getenv('GS_MEDIA_BUCKET_NAME', 'matchjob')

# Subcarpeta dentro del bucket para archivos estáticos (ej. bucket-name/static/css/...)
GS_LOCATION = 'static' # <--- Tus archivos están en 'gestionOfertas/static/css/base.css'
                        # cuando se recolectan, irán a bucket/static/gestionOfertas/css/base.css
                        # o a bucket/static/css/base.css si usas staticfiles_finders.
                        # Vamos a asumir que quieres que estén en bucket/static/

# Configuración de la cuenta de servicio para impersonación (firma de URLs para GCS)
GS_AUTH_IMPERSONATION_SERVICE_ACCOUNT = '159154155877-compute@developer.gserviceaccount.com'

# Controla si django-storages intenta crear el bucket automáticamente (ponlo en False si el bucket ya existe)
GS_AUTO_CREATE_BUCKET = False

# Controla si las URLs generadas para los archivos requieren autenticación mediante querystring (firma)
# Ponlo en False si tus archivos estáticos y de medios son públicos.
GS_QUERYSTRING_AUTH = False


# --- CONDICIONAL PARA STATICFILES_STORAGE y STATIC_URL (CRUCIAL PARA DESARROLLO/PRODUCCIÓN) ---
# STATIC_ROOT es el directorio donde 'collectstatic' recolectará los archivos
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_collected')

# STATICFILES_DIRS: Dónde Django busca archivos estáticos en tu proyecto (además de los de las apps)
# COMENTAMOS O ELIMINAMOS ESTO porque tus archivos están en gestionOfertas/static/
# Si tienes OTROS archivos estáticos fuera de las carpetas 'static/' de las apps, entonces necesitarías esta línea.
# STATICFILES_DIRS = [
#     os.path.join(BASE_DIR, 'static'), # Ejemplo: Si tuvieras una carpeta 'static' en la raíz del proyecto.
# ]


if DEBUG:
    # --- CONFIGURACIÓN PARA DESARROLLO LOCAL (DEBUG=True) ---
    # En desarrollo, Django sirve los archivos estáticos y de medios directamente desde el disco.
    STATIC_URL = '/static/'
    MEDIA_URL = '/media/'
    # Para archivos de medios (uploads de usuarios) en desarrollo local
    MEDIA_ROOT = os.path.join(BASE_DIR, 'media') # Crea una carpeta 'media' en la raíz del proyecto para uploads
    # Django utiliza su propio almacenamiento de archivos estáticos en desarrollo
    STORAGES = {
        "default": { # Para MEDIA_URL
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": { # Para STATIC_URL
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        }
    }
else:
    # --- CONFIGURACIÓN PARA PRODUCCIÓN EN CLOUD RUN (DEBUG=False) ---
    # En producción, los archivos estáticos y de medios se sirven desde Google Cloud Storage.
    STATIC_URL = f'https://storage.googleapis.com/{GS_STATIC_BUCKET_NAME}/{GS_LOCATION}/'
    MEDIA_URL = f'https://storage.googleapis.com/{GS_MEDIA_BUCKET_NAME}/media/' # Subcarpeta 'media/' dentro del bucket de medios

    STORAGES = {
        "default": { # Para MEDIA_URL (archivos de usuarios)
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GS_MEDIA_BUCKET_NAME,
            },
        },
        "staticfiles": { # Para STATIC_URL (archivos del sitio)
            "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
            "OPTIONS": {
                "bucket_name": GS_STATIC_BUCKET_NAME,
                # Las credenciales de impersonación ya se gestionan a nivel de django-storages global
            },
        }
    }

# --- SEGURIDAD ADICIONAL (CSRF y SSL) ---
# Fuerza las cookies de sesión y CSRF para que solo se envíen sobre HTTPS
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True



# Dile a Django qué orígenes son de confianza para las solicitudes CSRF.
# Esto es CRÍTICO para los 403 CSRF cuando DEBUG=False.
# Asegúrate de incluir la URL EXACTA de tu servicio de Cloud Run.
# Si usas un dominio personalizado, añade 'https://tu.dominio.personalizado'.
CSRF_TRUSTED_ORIGINS = [
    'https://matchjob-service-159154155877.southamerica-west1.run.app',
    # 'https://*.cloudrun.app', # Opcional: Para permitir todos los subdominios de cloudrun.app
    # Si usas un dominio personalizado, añádelo aquí: 'https://www.tudominio.com',
]


# --- APIs y Otros ---
MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN", "pk.eyJ1IjoiYWFtdW51b2JpLCJhIjoiY21hbjk0NTc2MHQwbjJ4b2ppcGtwcWVyYiJ9.fjKCOM0r_euWhIprM9crfQ") # <--- Mover a .env
Maps_API_KEY = os.getenv("MAPS_API_KEY", "AIzaSyBY4CCIFbyI3FH59aSkifR9-ThyY0Na8l0") # <--- Mover a .env


# --- AUTHENTICATION ---
AUTHENTICATION_BACKENDS = [
    'gestionOfertas.backends.AutenticacionPorRUTBackend',
    # 'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = 'gestionOfertas.Usuario'

# --- DEFAULT PRIMARY KEY FIELD TYPE ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- EMAIL CONFIGURATION ---
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'matchjobbeta@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'rbxf vwqk yhxv yyxp') # <--- ¡NUNCA expongas esto directamente!
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'matchjobbeta@gmail.com')
SITE_NAME = os.getenv('SITE_NAME', 'MatchJob')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose' if os.environ.get('DJANGO_DEBUG') == 'True' else 'simple',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'gestionOfertas': {  # Reemplaza 'myapp' con el nombre de tu app
            'handlers': ['console'],
            'level': 'DEBUG' if os.environ.get('DJANGO_DEBUG') == 'True' else 'INFO',
            'propagate': False,
        },
    },
}

GOOGLE_MAPS_API_KEY ='AIzaSyBY4CCIFbyI3FH59aSkifR9-ThyY0Na8l0'

GOOGLE_API_KEY='AIzaSyBE299IBQEwygvoUL882_64HrKQTLskEhE'

LOGIN_URL = '/iniciar_sesion/'

# Configuración de los umbrales de IA para postulaciones
UMBRAL_IA_APROBADO_NORMAL = 70.00
UMBRAL_IA_APROBADO_URGENTE = 55.00 # Más permisivo



# REDIS_COMMON_URL = "rediss://:377f3208-99dd-4c7a-a593-7881a916f70c@10.220.97.147:6378/0"

# CACHES = {
#     "default": {
#         "BACKEND": "django_redis.cache.RedisCache",
#         "LOCATION": REDIS_COMMON_URL,
#         "OPTIONS": {
#             "CLIENT_CLASS": "django_redis.client.DefaultClient",
#             "IGNORE_EXCEPTIONS": True,
#             "CONNECTION_ARGS": {
#                 "ssl_cert_reqs": ssl.CERT_NONE,
#                 "ssl_check_hostname": False,
#             },
#         }
#     }
# }

# # --- Celery Configuration ---
# # Celery necesita configuración SSL separada
# CELERY_BROKER_URL = "rediss://:377f3208-99dd-4c7a-a593-7881a916f70c@10.220.97.147:6378/0"
# CELERY_RESULT_BACKEND = "rediss://:377f3208-99dd-4c7a-a593-7881a916f70c@10.220.97.147:6378/0"

# # Configuración SSL para Celery
# CELERY_REDIS_BACKEND_USE_SSL = {
#     'ssl_cert_reqs': ssl.CERT_NONE,
#     'ssl_check_hostname': False,
# }
# CELERY_BROKER_USE_SSL = {
#     'ssl_cert_reqs': ssl.CERT_NONE,
#     'ssl_check_hostname': False,
# }

# CELERY_ACCEPT_CONTENT = ['json']
# CELERY_TASK_SERIALIZER = 'json'
# CELERY_RESULT_SERIALIZER = 'json'
# CELERY_TIMEZONE = 'America/Santiago'
# CELERY_ENABLE_UTC = True


# Configuración de Google Cloud
GCP_PROJECT_ID = os.getenv('GCP_PROJECT_ID', 'matchjob-458200')
GCP_LOCATION = os.getenv('GCP_LOCATION', 'southamerica-east1') # <--- Asegúrate de que coincida con la cola
GCP_QUEUE_NAME = os.getenv('GCP_QUEUE_NAME', 'default')
SERVICE_URL = os.getenv('SERVICE_URL', 'https://matchjob-service-159154155877.southamerica-west1.run.app')



