# settings.py

from pathlib import Path
from django.contrib.messages import constants as messages
from google.oauth2 import service_account
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv()

MESSAGE_TAGS = {
    messages.DEBUG: 'secondary',
    messages.INFO: 'info',
    messages.SUCCESS: 'success',
    messages.WARNING: 'warning',
    messages.ERROR: 'danger',
}

# --- CONFIGURACIÓN PARA PRODUCCIÓN EN CLOUD RUN ---
# IMPORTANTE: Mueve estos valores a variables de entorno en Cloud Run.
# Aquí se usan os.getenv para leerlas desde el entorno.

# SECRET_KEY: Genera una nueva clave secreta MUY FUERTE para producción
# NUNCA uses esta clave en producción, cámbiala a os.getenv('SECRET_KEY')
SECRET_KEY = os.getenv('SECRET_KEY', 'your-very-strong-and-random-secret-key-for-production') # <-- ¡CAMBIA ESTO EN PRODUCCIÓN!

DEBUG = os.getenv('DJANGO_DEBUG', 'False').lower() == 'true' # Leer DEBUG de variable de entorno
# Permitir todos los hosts para Cloud Run inicialmente. En producción, restringe a la URL de Cloud Run.
ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gestionOfertas',
    'widget_tweaks',
    'storages', # Agregado para django-storages
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'MatchJob.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
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

WSGI_APPLICATION = 'MatchJob.wsgi.application'

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

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-cl'
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True

# --- Google Cloud Storage Configuration ---

# Tu ID de proyecto de Google Cloud (necesario para algunas operaciones de GCS)
GS_PROJECT_ID = os.getenv('GS_PROJECT_ID', 'matchjob-458200')

# Bucket para ARCHIVOS DE MEDIOS (CVs, uploads de usuarios)
GS_MEDIA_BUCKET_NAME = os.getenv('GS_MEDIA_BUCKET_NAME', 'matchjob')

# Bucket para ARCHIVOS ESTÁTICOS (CSS, JS, imágenes del sitio)
GS_STATIC_BUCKET_NAME = os.getenv('GS_STATIC_BUCKET_NAME', 'matchjob-static-files') # <--- ¡Tu nuevo bucket!

# URL base para los archivos estáticos. Apunta a la raíz de tu bucket de estáticos.
STATIC_URL = f'https://storage.googleapis.com/{GS_STATIC_BUCKET_NAME}/'

# Ruta local donde collectstatic reunirá los archivos antes de subirlos a GCS
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles_collected')

# URL base para los archivos de medios. Apunta a una subcarpeta 'media/' dentro de tu bucket de medios.
MEDIA_URL = f'https://storage.googleapis.com/{GS_MEDIA_BUCKET_NAME}/media/'

# Ruta local temporal para archivos de medios. No se usa en producción con GCS.
MEDIA_ROOT = BASE_DIR / 'media_files_temp_no_usar'

# Configuración de los backends de almacenamiento de Django Storages
STORAGES = {
    "default": { # Para MEDIA_URL y DEFAULT_FILE_STORAGE (archivos de usuarios)
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_MEDIA_BUCKET_NAME,
            # Las credenciales se obtienen automáticamente en Cloud Run si la cuenta de servicio tiene permisos
            # "credentials": GS_CREDENTIALS, # Solo necesario si no usas Application Default Credentials explícitamente
        },
    },
    "staticfiles": { # Para STATIC_URL y STATICFILES_STORAGE (archivos del sitio)
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": GS_STATIC_BUCKET_NAME,
            # Las credenciales se obtienen automáticamente en Cloud Run si la cuenta de servicio tiene permisos
            # "credentials": GS_CREDENTIALS, # Solo necesario si no usas Application Default Credentials explícitamente
        },
    }
}
# La parte de GS_CREDENTIALS_FILE y GS_CREDENTIALS puede simplificarse o quitarse
# si confías en Application Default Credentials en Cloud Run.
# En desarrollo local, podrías necesitarla si usas una cuenta de servicio específica.
GS_CREDENTIALS_FILE = os.getenv('GOOGLE_APPLICATION_CREDENTIALS') # Cloud Run lo gestiona solo
GS_CREDENTIALS = service_account.Credentials.from_service_account_file(GS_CREDENTIALS_FILE) if GS_CREDENTIALS_FILE and os.path.exists(GS_CREDENTIALS_FILE) else None


MAPBOX_TOKEN = "pk.eyJ1IjoiYWFtdW5venAiLCJhIjoiY21hbjk0NTc2MHQwbjJ4b2ppcGtwcWVyYiJ9.fjKCOM0r_euWhIprM9crfQ" # <--- Mover a .env
Maps_API_KEY = "AIzaSyBY4CCIFbyI3FH59aSkifR9-ThyY0Na8l0" # <--- Mover a .env

# --- Autenticación ---
AUTHENTICATION_BACKENDS = [
    'gestionOfertas.backends.AutenticacionPorRUTBackend',
    # 'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = 'gestionOfertas.Usuario'

# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Configuración de Email (usando variables de entorno para producción)
EMAIL_BACKEND = os.getenv('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_USE_TLS = os.getenv('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', 'matchjobbeta@gmail.com')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', 'rbxf vwqk yhxv yyxp') # <--- ¡NUNCA expongas esto directamente!
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', 'matchjobbeta@gmail.com')
SITE_NAME = os.getenv('SITE_NAME', 'MatchJob')