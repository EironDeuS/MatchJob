# Usa una imagen base de Python
FROM python:3.11-slim

# Establece el directorio de trabajo
WORKDIR /app

# Copia los archivos de requerimientos y las instala
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia el resto de tu código de la aplicación # <-- LÍNEA CORREGIDA
COPY . .

# --- CONFIGURACIÓN DE VARIABLES DE ENTORNO PARA EL ENTORNO DE BUILD ---
# (Asegúrate de haber quitado los comentarios en la misma línea de los ENV)
ENV DJANGO_DEBUG="False" \
    GS_STATIC_BUCKET_NAME="matchjob-static-files" \
    GS_LOCATION="static" \
    GS_PROJECT_ID="matchjob-458200" \
    GS_QUERYSTRING_AUTH="False"

# --- PASO PARA RECOLECTAR Y SUBIR ARCHIVOS ESTÁTICOS A GCS ---
RUN python manage.py collectstatic --noinput

# Variables de entorno para la ejecución de la aplicación
ENV DJANGO_SETTINGS_MODULE=MatchJob.settings
ENV PYTHONUNBUFFERED True

# Expone el puerto que tu aplicación usa (generalmente 8000 para Gunicorn)
# EXPOSE 8000

# Comando para iniciar la aplicación (ej. Gunicorn)
CMD gunicorn --bind 0.0.0.0:$PORT --workers 2 MatchJob.wsgi:application