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

SECRET_KEY = 'django-insecure-3$59aeffoijj0z^d7aa!@_f@=9l#%l9d0@6#yxwy9n(hjy!aaf' # <-- ¡MOVER A .env!
DEBUG = True
ALLOWED_HOSTS = ['*'] # <-- Configurar adecuadamente para producción

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gestionOfertas',
    'widget_tweaks',
    'storages',
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'BDmatchjob',
        'USER': 'neondb_owner',
        'PASSWORD': 'npg_lU8ucqsIiP6X', # <-- ¡MOVER A .env!
        'HOST': 'ep-weathered-sunset-ac0mxs0q-pooler.sa-east-1.aws.neon.tech',
        'PORT': '5432',
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

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']


# --- Google Cloud Storage Configuration ---

STORAGES = {
    "default": {
        "BACKEND": "storages.backends.gcloud.GoogleCloudStorage",
        "OPTIONS": {
            "bucket_name": "matchjob", # Bucket para MEDIA
        },
    },
    "staticfiles": {
        # AQUÍ ESTÁ EL CAMBIO: Usar el backend local por defecto para estáticos
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        # No se necesitan OPTIONS especiales aquí para el backend local
    }
}
MEDIA_URL = '' # O f'https://storage.googleapis.com/matchjob/media/' si prefieres
MEDIA_ROOT = BASE_DIR / 'media_files_temp_no_usar'

# --- Autenticación ---

AUTHENTICATION_BACKENDS = [
    'gestionOfertas.backends.AutenticacionPorRUTBackend',
    # 'django.contrib.auth.backends.ModelBackend',
]

AUTH_USER_MODEL = 'gestionOfertas.Usuario'

# --- Default primary key field type ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- Opcional: URLs de Login/Logout ---
# LOGIN_URL = 'nombre_url_login'
# LOGOUT_REDIRECT_URL = 'inicio'
# LOGIN_REDIRECT_URL = 'inicio' 