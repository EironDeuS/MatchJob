# Dockerfile

# Usar una imagen base de Python.
# Puedes elegir una versión específica como python:3.10-slim-buster
# Si usas 3.13 en tu Cloud Run, asegúrate de que esté disponible y sea compatible.
# Para esta configuración, 3.11 es una opción segura y probada.
FROM python:3.11-slim-buster

# Establecer el directorio de trabajo dentro del contenedor.
WORKDIR /app

# Copiar el archivo requirements.txt primero para aprovechar el cache de Docker.
COPY requirements.txt .

# Instalar las dependencias de Python especificadas en requirements.txt.
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de tu código (main.py) al directorio de trabajo.
COPY main.py .

# Establecer la variable de entorno FUNCTION_TARGET.
# Esto le dice a `functions-framework` qué función dentro de `main.py` debe ejecutar
# cuando el servicio de Cloud Run reciba un evento.
# ¡IMPORTANTE! Cambiado a process_document_from_gcs
ENV FUNCTION_TARGET=process_document_from_gcs

# Definir el comando que se ejecutará cuando el contenedor se inicie.
# `functions-framework` es una herramienta de Google que facilita la ejecución
# de funciones en entornos de contenedores como Cloud Run.
# `--signature-type event`: Indica que la función espera un evento (no una solicitud HTTP directa).
# ¡IMPORTANTE! Cambiado a process_document_from_gcs
CMD ["functions-framework", "--target", "process_document_from_gcs", "--signature-type", "event"]