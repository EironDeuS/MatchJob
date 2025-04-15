from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin

# -----------------------------
# Modelo base de Usuario
# -----------------------------
# Representa cualquier tipo de usuario del sistema.
# Contiene información común como username, correo y tipo de usuario.
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Gestor personalizado para el modelo Usuario
class UsuarioManager(BaseUserManager):
    """
    Este es el gestor personalizado para el modelo Usuario.
    Proporciona métodos para crear usuarios y superusuarios de forma personalizada.
    """
    
    def create_user(self, username, correo, password=None, **extra_fields):
        """
        Crea y guarda un usuario normal con RUT como username, correo y contraseña.
        """
        if not username:
            raise ValueError("El campo 'username' (RUT) es obligatorio")  # Aseguramos que el RUT esté presente
        
        # Normalizamos el correo (en minúsculas)
        email = self.normalize_email(correo)
        
        # Creamos el objeto usuario usando el modelo
        user = self.model(username=username, correo=email, **extra_fields)
        
        # Establecemos la contraseña encriptada
        user.set_password(password)
        
        # Guardamos el usuario en la base de datos
        user.save(using=self._db)
        return user  # Devolvemos el usuario creado

    def create_superuser(self, username, correo, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con permisos administrativos (is_staff, is_superuser).
        """
        # Establecemos que el superusuario debe tener estos campos por defecto
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        
        # Llamamos a `create_user` para crear el superusuario
        return self.create_user(username, correo, password, **extra_fields)


# Modelo personalizado de usuario
class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Este es el modelo personalizado de usuario que hereda de AbstractBaseUser y PermissionsMixin
    para integrar los campos y funcionalidades necesarias para la autenticación y permisos.
    """
    
    # Definimos los campos del modelo (usamos el RUT como el campo 'username')
    username = models.CharField(max_length=50, unique=True)  # RUT como username, único
    correo = models.EmailField(unique=True)  # Correo electrónico, único
    telefono = models.CharField(max_length=20)  # Teléfono del usuario
    tipo_usuario = models.CharField(max_length=20)  # Tipo de usuario (ejemplo: 'persona' o 'empresa')
    
    # Campos estándar de autenticación y permisos
    is_active = models.BooleanField(default=True)  # Indica si el usuario está activo
    is_staff = models.BooleanField(default=False)  # Indica si el usuario tiene acceso al admin
    
    # Este campo conecta con el gestor personalizado
    objects = UsuarioManager()

    # Se indica el campo que se usará para el login
    USERNAME_FIELD = 'username'  # Usamos el 'username' (RUT) como campo para login
    
    # Campos adicionales requeridos al crear un superusuario
    REQUIRED_FIELDS = ['correo']  # Requiere el correo al crear un superusuario

    # Función para mostrar el nombre de usuario cuando imprimimos el objeto
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
    usuario = models.OneToOneField(Usuario, on_delete=models.CASCADE)
    rut_empresa = models.CharField(max_length=12, unique=True)
    nombre_empresa = models.CharField(max_length=100)
    razon_cial = models.CharField(max_length=100)
    giro = models.CharField(max_length=100)

    class Meta:
        db_table = 'gestionofertas_empresa'  # Especifica el nombre de la tabla en la base de datos
        verbose_name = 'Empresa'
        verbose_name_plural = 'Empresas'

    def __str__(self):
        return f"{self.nombre_empresa} ({self.rut_empresa})"


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
    nombre_categoria = models.CharField(
        max_length=100,
        unique=True,  # Evita duplicados
        verbose_name="Nombre",
        help_text="Ej: Tecnología, Marketing, Diseño"
    )

    class Meta:
        verbose_name = "Categoría"
        verbose_name_plural = "Categorías"
        ordering = ['nombre_categoria']  # Orden alfabético por defecto

    def __str__(self):
        return self.nombre_categoria
    
    def natural_key(self):
        return (self.nombre_categoria,)  # Para usar en fixtures


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
