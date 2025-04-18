"""
Modelos optimizados para el sistema MatchJob con:
- Relaciones claras y consistentes
- Validaciones mejoradas
- Documentación completa
- Convenciones Django estándar
- Preparado para migraciones limpias
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType

# -----------------------------
# Gestor Personalizado de Usuario
# -----------------------------
class UsuarioManager(BaseUserManager):
    """
    Gestor personalizado para el modelo Usuario que reemplaza
    el gestor por defecto de Django.
    """

    def create_user(self, username, correo, password=None, **extra_fields):
        """
        Crea y guarda un usuario con username (RUT), correo y contraseña.
        Valida campos obligatorios y normaliza el correo.
        """
        if not username:
            raise ValueError(_('El RUT es obligatorio'))
        if not correo:
            raise ValueError(_('El correo electrónico es obligatorio'))

        email = self.normalize_email(correo)
        user = self.model(username=username, correo=email, **extra_fields)
        user.set_password(password)  # Hashea la contraseña
        user.save(using=self._db)
        return user

    def create_superuser(self, username, correo, password=None, **extra_fields):
        """
        Crea un superusuario con todos los permisos.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('tipo_usuario', 'admin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superusuario debe tener is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superusuario debe tener is_superuser=True'))

        return self.create_user(username, correo, password, **extra_fields)


# -----------------------------
# Modelo Usuario Personalizado
# -----------------------------
class Usuario(AbstractBaseUser, PermissionsMixin):
    """
    Modelo de usuario personalizado que reemplaza al modelo User por defecto de Django.
    Utiliza RUT como username y soporta múltiples tipos de usuarios.
    """

    TIPO_USUARIO_CHOICES = [
        ('persona', _('Persona Natural')),
        ('empresa', _('Empresa')),
        ('admin', _('Administrador')),
    ]

    # Campos básicos
    username = models.CharField(
        _('RUT/Username'),
        max_length=50,
        unique=True,
        help_text=_('RUT en formato 12345678-9')
    )
    correo = models.EmailField(
        _('Correo electrónico'),
        unique=True
    )
    telefono = models.CharField(
        _('Teléfono'),
        max_length=20,
        blank=True,
        null=True
    )
    tipo_usuario = models.CharField(
        _('Tipo de usuario'),
        max_length=20,
        choices=TIPO_USUARIO_CHOICES,
        default='persona'
    )

    # Campos de estado y permisos
    is_active = models.BooleanField(
        _('Activo'),
        default=True
    )
    is_staff = models.BooleanField(
        _('Acceso administrador'),
        default=False
    )

    # Auditoría
    fecha_creacion = models.DateTimeField(
        _('Fecha de creación'),
        auto_now_add=True,
        null=True
    )
    fecha_actualizacion = models.DateTimeField(
        _('Fecha de actualización'),
        auto_now=True,
        null=True
    )

    objects = UsuarioManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['correo']

    class Meta:
        verbose_name = _('Usuario')
        verbose_name_plural = _('Usuarios')
        ordering = ['fecha_creacion']
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['correo']),
            models.Index(fields=['tipo_usuario']),
        ]

    def __str__(self):
        return f"{self.username} ({self.get_tipo_usuario_display()})"

    def save(self, *args, **kwargs):
        """
        Sobrescribe el método save() para crear automáticamente
        el perfil de PersonaNatural o Empresa al crear un Usuario.
        """
        is_new = not self.pk  # Verificar si el usuario es nuevo
        super().save(*args, **kwargs)  # Guardar el Usuario

        if is_new:  # Solo crear el perfil si es un nuevo usuario
            if self.tipo_usuario == 'persona':
                PersonaNatural.objects.create(
                    usuario=self,
                    rut=self.username,  # Inicializar con datos básicos
                    nombres=getattr(self, 'nombres', None),
                    apellidos=getattr(self, 'apellidos', None),
                    direccion=getattr(self, 'direccion', None),
                    fecha_nacimiento=getattr(self, 'fecha_nacimiento', None),
                    nacionalidad=getattr(self, 'nacionalidad', None),
                )
            elif self.tipo_usuario == 'empresa':
                Empresa.objects.create(
                    usuario=self,
                    rut_empresa=self.username,  # Inicializar con datos básicos
                    nombre_empresa=getattr(self, 'nombre_empresa', None),
                    razon_social=getattr(self, 'razon_social', None),
                    giro=getattr(self, 'giro', None),
                )

    def clean(self):
        """
        Validaciones adicionales del modelo.
        Ya no necesitamos validar la existencia del perfil aquí,
        ya que se crea automáticamente en el save().
        """
        super().clean()
        # Puedes agregar otras validaciones específicas del Usuario aquí.


# -----------------------------
# Persona Natural
# -----------------------------
class PersonaNatural(models.Model):
    """
    Perfil extendido para usuarios de tipo Persona Natural.
    Contiene información personal adicional.
    """
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name=_('Usuario asociado'),
        related_name='personanatural'
    )
    rut = models.CharField(
        _('RUT'),
        max_length=12,
        help_text=_('Formato: 12345678-9')
    )
    nombres = models.CharField(
        _('Nombres'),
        max_length=100
    )
    apellidos = models.CharField(
        _('Apellidos'),
        max_length=100
    )
    direccion = models.CharField(
        _('Dirección'),
        max_length=200,
        blank=True,
        null=True
    )
    fecha_nacimiento = models.DateField(
        _('Fecha de nacimiento'),
        blank=True,
        null=True
    )
    nacionalidad = models.CharField(
        _('Nacionalidad'),
        max_length=50,
        default='Chilena'
    )

    class Meta:
        verbose_name = _('Persona Natural')
        verbose_name_plural = _('Personas Naturales')
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"

    def clean(self):
        """Validar que el usuario asociado sea de tipo persona"""
        super().clean()
        if self.usuario.tipo_usuario != 'persona':
            raise ValidationError(
                _('El usuario asociado debe ser de tipo Persona')
            )


# -----------------------------
# Empresa
# -----------------------------
class Empresa(models.Model):
    """
    Perfil extendido para usuarios de tipo Empresa.
    Contiene información comercial de la empresa.
    """
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        primary_key=True,
        verbose_name=_('Usuario asociado'),
        related_name='empresa'
    )
    rut_empresa = models.CharField(
        _('RUT Empresa'),
        max_length=12,
        unique=True,
        help_text=_('Formato: 12345678-9')
    )
    nombre_empresa = models.CharField(
        _('Nombre de la empresa'),
        max_length=100
    )
    razon_social = models.CharField(
        _('Razón social'),
        max_length=100,
        null=True
    )
    giro = models.CharField(
        _('Giro comercial'),
        max_length=100
    )
    fecha_registro = models.DateTimeField(
        _('Fecha de registro'),
        auto_now_add=True,
        null=True
    )
    activa = models.BooleanField(
        _('Activa'),
        default=True
    )

    class Meta:
        verbose_name = _('Empresa')
        verbose_name_plural = _('Empresas')
        ordering = ['nombre_empresa']
        indexes = [
            models.Index(fields=['nombre_empresa']),
            models.Index(fields=['rut_empresa']),
        ]

    def __str__(self):
        return f"{self.nombre_empresa} ({self.rut_empresa})"

    def clean(self):
        """Validar que el usuario asociado sea de tipo empresa"""
        super().clean()
        if self.usuario.tipo_usuario != 'empresa':
            raise ValidationError(
                _('El usuario asociado debe ser de tipo Empresa')
            )


# -----------------------------
# CV (Currículum Vitae)
# -----------------------------
class CV(models.Model):
    """
    Modelo que representa el currículum vitae de una persona.
    Relacionado 1-a-1 con PersonaNatural.
    """
    persona = models.OneToOneField(
        PersonaNatural,
        on_delete=models.CASCADE,
        verbose_name=_('Persona'),
        related_name='cv'
    )
    nombre = models.CharField(
        _('Título del CV'),
        max_length=100
    )
    correo = models.EmailField(
        _('Correo de contacto')
    )
    archivo_url = models.URLField(
        _('URL del archivo'),
        max_length=500,
        blank=True,
        null=True
    )
    experiencia = models.TextField(
        _('Resumen de experiencia'),
        blank=True
    )
    habilidades = models.TextField(
        _('Habilidades destacadas'),
        blank=True
    )
    fecha_subida = models.DateField(
        _('Fecha de subida'),
        auto_now_add=True,
        null=True
    )
    fecha_actualizacion = models.DateField(
        _('Fecha de actualización'),
        auto_now=True,
        null=True
    )

    class Meta:
        verbose_name = _('Currículum Vitae')
        verbose_name_plural = _('Currículos Vitae')
        ordering = ['-fecha_subida']

    def __str__(self):
        return f"CV de {self.persona}"


# -----------------------------
# Experiencia Laboral
# -----------------------------
class ExperienciaLaboral(models.Model):
    """
    Experiencia laboral asociada a un CV.
    Una persona puede tener múltiples experiencias laborales.
    """
    cv = models.ForeignKey(
        CV,
        on_delete=models.CASCADE,
        verbose_name=_('CV asociado'),
        related_name='experiencias'
    )
    nombre_empresa = models.CharField(
        _('Nombre de la empresa'),
        max_length=100
    )
    puesto = models.CharField(
        _('Puesto ocupado'),
        max_length=100
    )
    fecha_inicio = models.DateField(
        _('Fecha de inicio')
    )
    fecha_termino = models.DateField(
        _('Fecha de término'),
        blank=True,
        null=True
    )
    descripcion = models.TextField(
        _('Descripción de funciones'),
        blank=True
    )
    actualmente = models.BooleanField(
        _('Actualmente trabajando aquí'),
        default=False
    )

    class Meta:
        verbose_name = _('Experiencia Laboral')
        verbose_name_plural = _('Experiencias Laborales')
        ordering = ['-fecha_inicio']

    def __str__(self):
        return f"{self.puesto} en {self.nombre_empresa}"

    def clean(self):
        """Validar fechas coherentes"""
        super().clean()
        if self.fecha_termino and self.fecha_inicio > self.fecha_termino:
            raise ValidationError(
                _('La fecha de inicio no puede ser posterior a la fecha de término')
            )


# -----------------------------
# Categoría de Oferta
# -----------------------------
class Categoria(models.Model):
    """
    Categoría para clasificar las ofertas de trabajo.
    """
    nombre_categoria = models.CharField(
        _('Nombre'),
        max_length=100,
        unique=True,
        help_text=_('Ej: Tecnología, Marketing, Diseño')
    )
    descripcion = models.TextField(
        _('Descripción'),
        blank=True
    )
    icono = models.CharField(
        _('Icono'),
        max_length=50,
        blank=True,
        help_text=_('Clase de icono para mostrar en la interfaz')
    )
    activa = models.BooleanField(
        _('Activa'),
        default=True
    )

    class Meta:
        verbose_name = _('Categoría')
        verbose_name_plural = _('Categorías')
        ordering = ['nombre_categoria']

    def __str__(self):
        return self.nombre_categoria


# -----------------------------
# Oferta de Trabajo
# -----------------------------
class OfertaTrabajo(models.Model):
    """
    Oferta de trabajo publicada por una empresa o persona natural.
    Utiliza GenericForeignKey para relacionarse con el creador.
    """
    # Relación genérica con el creador (Empresa o PersonaNatural)
    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name=_('Tipo de creador')
    )
    object_id = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name=_('ID del creador')
    )
    creador = GenericForeignKey('content_type', 'object_id')

    # Información de la oferta
    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        verbose_name=_('Categoría'),
        related_name='ofertas'
    )
    nombre = models.CharField(
        _('Título de la oferta'),
        max_length=100
    )
    descripcion = models.TextField(
        _('Descripción del puesto')
    )
    requisitos = models.TextField(
        _('Requisitos'),
        blank=True
    )
    beneficios = models.TextField(
        _('Beneficios'),
        blank=True
    )
    salario = models.CharField(
        _('Salario'),
        max_length=100,
        blank=True
    )
    ubicacion = models.CharField(
        _('Ubicación'),
        max_length=100,
        blank=True
    )
    tipo_contrato = models.CharField(
        _('Tipo de contrato'),
        max_length=50,
        blank=True
    )
    fecha_publicacion = models.DateField(
        _('Fecha de publicación'),
        auto_now_add=True
    )
    fecha_cierre = models.DateField(
        _('Fecha de cierre'),
        blank=True,
        null=True
    )
    activa = models.BooleanField(
        _('Activa'),
        default=True
    )

    class Meta:
        verbose_name = _('Oferta de Trabajo')
        verbose_name_plural = _('Ofertas de Trabajo')
        ordering = ['-fecha_publicacion']
        indexes = [
            models.Index(fields=['nombre']),
            models.Index(fields=['content_type', 'object_id']),
            models.Index(fields=['categoria']),
        ]

    def __str__(self):
        return self.nombre

    def clean(self):
        """Validaciones del modelo"""
        super().clean()
        
        # Validar fechas coherentes (solo si fecha_cierre no es None)
        if self.fecha_cierre and self.fecha_publicacion:
            if self.fecha_publicacion > self.fecha_cierre:
                raise ValidationError(
                    _('La fecha de publicación no puede ser posterior a la fecha de cierre')
                )
        
        # Validar que el creador sea Empresa o PersonaNatural
        if hasattr(self, 'content_type') and self.content_type:
            valid_models = [
                ContentType.objects.get_for_model(Empresa),
                ContentType.objects.get_for_model(PersonaNatural)
            ]
            if self.content_type not in valid_models:
                raise ValidationError(
                    _('El creador debe ser una Empresa o una PersonaNatural')
                )


# -----------------------------
# Postulación
# -----------------------------
class Postulacion(models.Model):
    """
    Registro de postulación de una persona a una oferta.
    """
    ESTADOS = [
        ('pendiente', _('Pendiente')),
        ('revisado', _('Revisado')),
        ('entrevista', _('Entrevista')),
        ('contratado', _('Contratado')),
        ('rechazado', _('Rechazado')),
    ]

    persona = models.ForeignKey(
        PersonaNatural,
        on_delete=models.CASCADE,
        verbose_name=_('Postulante'),
        related_name='postulaciones'
    )
    oferta = models.ForeignKey(
        OfertaTrabajo,
        on_delete=models.CASCADE,
        verbose_name=_('Oferta'),
        related_name='postulaciones'
    )
    cv = models.ForeignKey(
        CV,
        on_delete=models.SET_NULL,
        verbose_name=_('CV enviado'),
        null=True,
        blank=True
    )
    fecha_postulacion = models.DateTimeField(
        _('Fecha de postulación'),
        auto_now_add=True
    )
    mensaje = models.TextField(
        _('Mensaje del postulante'),
        blank=True
    )
    estado = models.CharField(
        _('Estado'),
        max_length=20,
        choices=ESTADOS,
        default='pendiente'
    )
    feedback = models.TextField(
        _('Feedback'),
        blank=True
    )

    class Meta:
        verbose_name = _('Postulación')
        verbose_name_plural = _('Postulaciones')
        ordering = ['-fecha_postulacion']
        unique_together = ['persona', 'oferta']
        indexes = [
            models.Index(fields=['persona']),
            models.Index(fields=['oferta']),
            models.Index(fields=['estado']),
        ]

    def __str__(self):
        return f"{self.persona} postuló a {self.oferta}"

    def clean(self):
        """Validar coherencia en la postulación"""
        super().clean()
        if not self.cv and hasattr(self.persona, 'cv'):
            self.cv = self.persona.cv