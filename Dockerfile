# Usa una imagen base de Python con las dependencias necesarias
FROM python:3.11-slim-buster

# Establece el directorio de trabajo dentro del contenedor
WORKDIR /app

# Copia los archivos de requirements y las instala
COPY requirements.txt .
RUN pip install -r requirements.txt

# Reinstala Gunicorn explícitamente (para asegurar que esté presente)
RUN pip install gunicorn

# Copia el archivo de credenciales JSON
COPY matchjob-458200-6a0cfe7aa83a.json /app/matchjob-458200-6a0cfe7aa83a.json

# Copia el resto de tu aplicación Django al contenedor
COPY . .

# Recopila los archivos estáticos
RUN python manage.py collectstatic --noinput

# Establece las variables de entorno (ajústalas según tu configuración)
ENV DJANGO_SETTINGS_MODULE=MatchJob.settings
ENV PYTHONUNBUFFERED=1

# Expone el puerto en el que correrá tu aplicación (el default de Django es 8000)
EXPOSE 8000

# Comando para ejecutar tu aplicación Django con Gunicorn (un servidor WSGI recomendado para producción)
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "MatchJob.wsgi"]