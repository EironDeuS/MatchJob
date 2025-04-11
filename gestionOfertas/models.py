from django.db import models

# -----------------------------
# Modelo base de Usuario
# -----------------------------
# Representa cualquier tipo de usuario del sistema.
# Contiene información común como username, correo y tipo de usuario.
class Usuario(models.Model):
    username = models.CharField(max_length=50, unique=True)  # Nombre de usuario único
    correo = models.EmailField(unique=True)  # Correo electrónico único
    contraseña = models.CharField(max_length=128)  # Contraseña (puedes integrarlo con autenticación más adelante)
    telefono = models.CharField(max_length=20)  # Número de teléfono
    tipo_usuario = models.CharField(max_length=20)  # 'persona' o 'empresa'

    def __str__(self):
        return f"{self.username} ({self.tipo_usuario})"


# -----------------------------
# Persona Natural
# -----------------------------
# Datos adicionales solo si el usuario es una persona (no empresa).
# Está relacionado 1 a 1 con el modelo Usuario.
class PersonaNatural(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)  # Relación uno a uno con Usuario
    rut = models.CharField(max_length=12)  # RUT chileno
    nombres = models.CharField(max_length=100)  # Nombre(s) del usuario
    apellidos = models.CharField(max_length=100)  # Apellidos
    direccion = models.CharField(max_length=200)  # Dirección de residencia
    fecha_nacimiento = models.DateField()  # Fecha de nacimiento
    nacionalidad = models.CharField(max_length=50)  # Nacionalidad

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"


# -----------------------------
# Empresa
# -----------------------------
# Datos adicionales solo si el usuario es una empresa.
# Está relacionado 1 a 1 con el modelo Usuario.
class Empresa(models.Model):
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE, primary_key=True)  # Relación uno a uno con Usuario
    rut_empresa = models.CharField(max_length=12)  # RUT de la empresa
    nombre_empresa = models.CharField(max_length=100)  # Nombre comercial
    razon_cial = models.CharField(max_length=100)  # Razón social
    giro = models.CharField(max_length=100)  # Actividad económica

    def __str__(self):
        return self.nombre_empresa


# -----------------------------
# CV (Currículum Vitae)
# -----------------------------
# Representa un CV subido por una persona.
# Tiene relación uno a uno con PersonaNatural.
class CV(models.Model):
    persona = models.OneToOneField(PersonaNatural, on_delete=models.CASCADE)  # CV pertenece a una sola persona
    nombre = models.CharField(max_length=100)  # Nombre o título del CV
    correo = models.EmailField()  # Correo asociado al CV
    archivo_url = models.URLField()  # Enlace al archivo del CV (PDF, por ejemplo)
    experiencia = models.TextField()  # Resumen de experiencia general
    fecha_subida = models.DateField()  # Fecha en que se subió el CV

    def __str__(self):
        return f"CV de {self.persona}"


# -----------------------------
# Experiencia Laboral
# -----------------------------
# Detalles de experiencias pasadas que van dentro de un CV.
# Muchas experiencias pueden estar asociadas a un solo CV.
class ExperienciaLaboral(models.Model):
    cv = models.ForeignKey(CV, on_delete=models.CASCADE)  # Relación muchos a uno con CV
    nombre_empresa = models.CharField(max_length=100)  # Empresa donde se trabajó
    puesto = models.CharField(max_length=100)  # Cargo o puesto ocupado
    fecha_inicio = models.DateField()  # Fecha de inicio del trabajo
    fecha_termino = models.DateField(null=True, blank=True)  # Fecha de fin (puede estar vacío si sigue vigente)
    descripcion = models.TextField()  # Tareas realizadas

    def __str__(self):
        return f"{self.puesto} en {self.nombre_empresa}"


# -----------------------------
# Categoría de Oferta
# -----------------------------
# Categoriza las ofertas de trabajo.
class Categoria(models.Model):
    nombre_categoria = models.CharField(max_length=100)  # Nombre de la categoría (ej: Deportes, Marketing, etc.)

    def __str__(self):
        return self.nombre_categoria


# -----------------------------
# Oferta de Trabajo
# -----------------------------
# Publicada por una empresa.
# Relacionada con una categoría y una empresa.
class OfertaTrabajo(models.Model):
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE)  # Empresa que publica la oferta
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE)  # Categoría de la oferta
    nombre = models.CharField(max_length=100)  # Título de la oferta
    descripcion = models.TextField()  # Descripción del trabajo
    fecha_oferta = models.DateField()  # Fecha de publicación

    def __str__(self):
        return self.nombre


# -----------------------------
# Postulación
# -----------------------------
# Registra la postulación de una persona a una oferta.
class Postulacion(models.Model):
    persona = models.ForeignKey(PersonaNatural, on_delete=models.CASCADE)  # Persona que postula
    oferta = models.ForeignKey(OfertaTrabajo, on_delete=models.CASCADE)  # Oferta a la que se postula
    fecha_postulacion = models.DateField()  # Fecha en que se realizó la postulación

    def __str__(self):
        return f"{self.persona} postuló a {self.oferta}"
