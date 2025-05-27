# Usa una imagen base de Python oficial para Cloud Run
FROM python:3.11-slim

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Instala gunicorn y copia los requirements.txt
# Esto se hace primero para aprovechar el cacheo de Docker si tus dependencias no cambian
COPY requirements.txt .
RUN pip install -r requirements.txt --no-cache-dir

# Copia el resto del código de tu aplicación al contenedor
COPY . .

# Genera una clave secreta si no la tienes en tus variables de entorno de Cloud Run.
# Esto es para asegurar que la clave secreta se genera durante la construcción si no se proporciona externamente.
# Mejor práctica: Inyectar SECRET_KEY como variable de entorno en Cloud Run.
# Si ya la tienes en tu .env, no necesitas esta parte en Dockerfile, pero Cloud Run la necesitará.
# Puedes quitar estas dos líneas si siempre la inyectarás como variable de entorno en Cloud Run.
# RUN python -c "import secrets; print(secrets.token_urlsafe(50))" > secret_key.txt
# ENV SECRET_KEY=$(cat secret_key.txt)


# Establece la variable de entorno para que Django sepa que está en producción
ENV DJANGO_SETTINGS_MODULE=MatchJob.settings
ENV PYTHONUNBUFFERED True

# Exponer el puerto en el que la aplicación se ejecutará (Cloud Run usa 8080 por defecto)
EXPOSE 8080

# Comando para iniciar la aplicación Gunicorn
# 'MatchJob.wsgi:application' debe apuntar al objeto WSGI de tu proyecto.
# Asegúrate de que 'MatchJob' es el nombre de tu carpeta de proyecto interna.
CMD exec gunicorn --bind :$PORT --workers 2 MatchJob.wsgi:application   