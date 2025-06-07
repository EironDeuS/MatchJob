# En tu_app/models.py

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Avg
from django.core.validators import MinValueValidator, MaxValueValidator
import os
from django.db import models
from django.utils.translation import gettext_lazy as _

# -----------------------------
# Gestor Personalizado de Usuario
# -----------------------------
class UsuarioManager(BaseUserManager):
    """ Gestor para Usuario personalizado con RUT como username. """
    def create_user(self, username, correo, password=None, **extra_fields):
        if not username:
            raise ValueError(_('El RUT (username) es obligatorio'))
        if not correo:
            raise ValueError(_('El correo electrónico es obligatorio'))
        email = self.normalize_email(correo)
        # Quitar campos de perfil para que save() los maneje
        profile_fields = ['nombres', 'apellidos', 'fecha_nacimiento', 'nacionalidad', # Persona
                          'nombre_empresa', 'razon_social', 'giro'] # Empresa
        # Dirección y teléfono ahora están en Usuario, no son de perfil específico
        user_extra_fields = {k: v for k, v in extra_fields.items() if k not in profile_fields}
        user = self.model(username=username, correo=email, **user_extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, correo, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('tipo_usuario', 'admin')
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superusuario debe tener is_staff=True'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superusuario debe tener is_superuser=True'))
        # No pasar campos de perfil al crear superuser
        return self.create_user(username, correo, password, **extra_fields)

# -----------------------------
# Modelo Usuario Personalizado (con direccion)
# -----------------------------
class Usuario(AbstractBaseUser, PermissionsMixin):
    TIPO_USUARIO_CHOICES = [
        ('persona', _('Persona Natural')),
        ('empresa', _('Empresa')),
        ('admin', _('Administrador')),
    ]
    # Usamos 'username' para almacenar el RUT
    username = models.CharField(
        _('RUT/Username'), max_length=50, unique=True, help_text=_('RUT para login')
    )
    correo = models.EmailField(_('Correo electrónico'), unique=True)
    telefono = models.CharField(_('Teléfono'), max_length=20, blank=True, null=True)
    direccion = models.CharField(
        _('Dirección'), max_length=255, blank=True, null=True
    )
    tipo_usuario = models.CharField(
        _('Tipo de usuario'), max_length=20, choices=TIPO_USUARIO_CHOICES, default='persona'
    )
    is_active = models.BooleanField(_('Activo'), default=True)
    is_staff = models.BooleanField(_('Acceso Admin Site'), default=False)
    fecha_creacion = models.DateTimeField(_('Fecha de creación'), auto_now_add=True, null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(_('Fecha de actualización'), auto_now=True, null=True, blank=True)

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
        """ Crea automáticamente el perfil si es un usuario nuevo (no admin). """
        is_new = not self.pk
        super().save(*args, **kwargs)
        if is_new and self.tipo_usuario != 'admin':
            if self.tipo_usuario == 'persona':
                PersonaNatural.objects.update_or_create(usuario=self, defaults={})
            elif self.tipo_usuario == 'empresa':
                Empresa.objects.update_or_create(usuario=self, defaults={})

    # --- Métodos de Valoración y Perfil ---
    @property
    def valoracion_promedio(self):
        avg_dict = self.valoraciones_recibidas.aggregate(promedio=Avg('puntuacion'))
        promedio = avg_dict.get('promedio')
        return round(promedio, 1) if promedio is not None else 0.0

    @property
    def cantidad_valoraciones(self):
        return self.valoraciones_recibidas.count()

    def get_profile(self):
        """Obtiene el perfil específico asociado (PersonaNatural o Empresa)."""
        if self.tipo_usuario == 'persona':
            return getattr(self, 'personanatural', None)
        elif self.tipo_usuario == 'empresa':
            return getattr(self, 'empresa', None)
        return None
    
    @property
    def email(self):
        return self.correo

# -----------------------------
# Persona Natural (Sin RUT ni Direccion)
# -----------------------------
class PersonaNatural(models.Model):
    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, primary_key=True,
        verbose_name=_('Usuario asociado'), related_name='personanatural'
    )
    # No hay RUT ni Direccion aquí
    nombres = models.CharField(_('Nombres'), max_length=100, blank=True)
    apellidos = models.CharField(_('Apellidos'), max_length=100, blank=True)
    fecha_nacimiento = models.DateField(_('Fecha de nacimiento'), blank=True, null=True)
    nacionalidad = models.CharField(_('Nacionalidad'), max_length=50, default='Chilena')
    modo_urgente = models.BooleanField(default=False)
    recibir_ofertas_urgentes = models.BooleanField(default=False, verbose_name="Recibir ofertas urgentes por correo")

    class Meta:
        verbose_name = _('Persona Natural')
        verbose_name_plural = _('Personas Naturales')
        ordering = ['apellidos', 'nombres']

    def __str__(self):
        nombre = f"{self.nombres} {self.apellidos}".strip()
        return nombre or self.usuario.username # Fallback al RUT/username

    def clean(self):
        super().clean()
        if hasattr(self, 'usuario') and self.usuario.tipo_usuario != 'persona':
            raise ValidationError(_('El usuario asociado debe ser de tipo Persona'))

    @property
    def nombre_completo(self):
        return f"{self.nombres} {self.apellidos}".strip()

    def get_postulaciones_activas(self):
        estados_finales = ['contratado', 'rechazado']
        return self.postulaciones.exclude(estado__in=estados_finales) # Usa related_name de Postulacion.persona

    def get_ofertas_creadas_activas(self):
        return self.usuario.ofertas_creadas.filter(esta_activa=True) # Usa related_name de OfertaTrabajo.creador
    
    def activar_modo_urgente(self):
        """Activa el modo urgente para esta persona."""
        self.modo_urgente = True
        self.save(update_fields=['modo_urgente'])

    def desactivar_modo_urgente(self):
        """Desactiva el modo urgente para esta persona."""
        self.modo_urgente = False
        self.save(update_fields=['modo_urgente'])

    def esta_en_modo_urgente(self):
        """Retorna True si la persona está en modo urgente."""
        return self.modo_urgente



# -----------------------------
# Empresa (Sin RUT ni Direccion)
# -----------------------------
class Empresa(models.Model):
    usuario = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, primary_key=True,
        verbose_name=_('Usuario asociado'), related_name='empresa'
    )
    # No hay RUT ni Direccion aquí (a menos que necesites una dirección específica de la empresa)
    nombre_empresa = models.CharField(_('Nombre de la empresa'), max_length=100, blank=True)
    razon_social = models.CharField(_('Razón social'), max_length=100, blank=True, null=True)
    giro = models.CharField(_('Giro comercial'), max_length=100, blank=True)
    fecha_registro = models.DateTimeField(_('Fecha de registro'), auto_now_add=True, null=True, blank=True)
    activa = models.BooleanField(_('Activa'), default=True)
    pagina_web = models.URLField(_("Página Web"), max_length=200, blank=True, null=True)
    redes_sociales = models.TextField(_("Redes Sociales"), blank=True, null=True)
    # direccion_fiscal = models.CharField(_('Dirección Fiscal Empresa'), max_length=255, blank=True, null=True) # Opcional

    class Meta:
        verbose_name = _('Empresa')
        verbose_name_plural = _('Empresas')
        ordering = ['nombre_empresa']
        indexes = [ models.Index(fields=['nombre_empresa']) ]

    def __str__(self):
        return self.nombre_empresa or self.usuario.username # Fallback al RUT/username

    def clean(self):
        super().clean()
        if hasattr(self, 'usuario') and self.usuario.tipo_usuario != 'empresa':
            raise ValidationError(_('El usuario asociado debe ser de tipo Empresa'))

    def get_ofertas_creadas_activas(self):
        return self.usuario.ofertas_creadas.filter(esta_activa=True) # Usa related_name de OfertaTrabajo.creador


# -----------------------------
# CV
# -----------------------------
#-- funcion para el cv_upload_to
def cv_upload_to(instance, filename):
    """
    Genera la ruta y nombre de archivo para el CV subido.
    Formato: cvs/RUT_nombreoriginal.extension
    """
    try:
        rut_usuario = instance.persona.usuario.username
    except AttributeError:
        rut_usuario = 'sin_rut'

    nombre_original, extension = os.path.splitext(filename)
    nuevo_nombre = f"{rut_usuario}_{nombre_original}{extension}"
    # Esta parte seguirá generando 'cvs/nombre.pdf'
    ruta_final = os.path.join('cvs', nuevo_nombre) 
    return ruta_final

class CV(models.Model):
    persona = models.OneToOneField(PersonaNatural, on_delete=models.CASCADE, related_name='cv')
    
    # Campo principal para el archivo PDF del CV
    archivo_cv = models.FileField(
        _('Archivo CV'),
        upload_to=cv_upload_to,
        blank=True,
        null=True
    )

    # *** EL CAMPO CLAVE: JSON completo de la IA ***
    datos_analizados_ia = models.JSONField( 
        _('Datos analizados por IA'),
        blank=True,
        null=True,
        help_text="JSON completo de la información extraída del CV por la IA."
    )

    # Campos planos para una búsqueda/display rápido y básico
    # Estos se poblarían desde el JSON_analizados_ia
    nombre_completo = models.CharField(_('Nombre completo del CV'), max_length=200, blank=True, null=True)
    email_contacto = models.EmailField(_('Correo de contacto'), blank=True, null=True)
    
    # Puedes mantener un resumen si quieres, o derivarlo del JSON si la IA lo provee
    resumen_profesional = models.TextField(_('Resumen profesional'), blank=True, null=True)


    fecha_subida = models.DateTimeField(_('Fecha de subida'), auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(_('Fecha de actualización'), auto_now=True)

    class Meta:
        verbose_name = _('CV')
        verbose_name_plural = _('CVs')

    def __str__(self):
        return f"CV de {self.nombre_completo or self.persona.usuario.username}"

    # Propiedades para acceder fácilmente a datos del JSON (ejemplos)
    @property
    def experiencia_laboral_ia(self):
        return self.datos_analizados_ia.get('experiencia_laboral', []) if self.datos_analizados_ia else []

    @property
    def educacion_ia(self):
        return self.datos_analizados_ia.get('educacion', []) if self.datos_analizados_ia else []

    @property
    def habilidades_ia_dict(self):
        return self.datos_analizados_ia.get('habilidades', {}) if self.datos_analizados_ia else {}

    @property
    def idiomas_ia_list(self):
        return self.datos_analizados_ia.get('idiomas', []) if self.datos_analizados_ia else []

# -----------------------------
# Categoría
# -----------------------------
class Categoria(models.Model):
    nombre_categoria = models.CharField(
        _('Nombre'), max_length=100, unique=True, help_text=_('Ej: Tecnología, Marketing, Diseño')
    )
    descripcion = models.TextField(_('Descripción'), blank=True)
    icono = models.CharField(
        _('Icono'), max_length=50, blank=True, help_text=_('Clase de icono')
    )
    activa = models.BooleanField(_('Activa'), default=True)

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
    TIPO_CONTRATO_CHOICES = [
        ('tiempo_completo', 'Tiempo completo'),
        ('medio_tiempo', 'Medio tiempo'),
        ('por_proyecto', 'Por proyecto'),
        ('temporal', 'Temporal'),
        ('freelance', 'Freelance'),
    ]

    # Relaciones
    creador = models.ForeignKey(
        'Usuario',
        on_delete=models.CASCADE,
        related_name='ofertas_creadas',
        verbose_name=_('Creador')
    )
    
    empresa = models.ForeignKey(
        'Empresa',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ofertas_publicadas',
        verbose_name=_('Empresa')
    )
    
    categoria = models.ForeignKey(
        'Categoria',
        on_delete=models.PROTECT,
        related_name='ofertas',
        verbose_name=_('Categoría')
    )
    
    # Campos principales
    nombre = models.CharField(_('Título'), max_length=100)
    descripcion = models.TextField(_('Descripción'))
    requisitos = models.TextField(_('Requisitos'), blank=True)
    beneficios = models.TextField(_('Beneficios'), blank=True)
    salario = models.CharField(_('Salario'), max_length=100, blank=True)
    latitud = models.FloatField(null=True, blank=True)
    longitud = models.FloatField(null=True, blank=True)
    direccion = models.CharField(_('Dirección'), max_length=255, blank=True)
    tipo_contrato = models.CharField(
        _('Tipo de contrato'),
        max_length=50,
        choices=TIPO_CONTRATO_CHOICES,
        blank=True
    )
    
    # Fechas y estadoX
    fecha_publicacion = models.DateTimeField(_('Publicación'), default=timezone.now)
    fecha_cierre = models.DateField(_('Cierre'), blank=True, null=True)
    esta_activa = models.BooleanField(_('Activa'), default=True)
    es_servicio = models.BooleanField(_('Es servicio'), default=False)
    urgente = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = _('Oferta de trabajo')
        verbose_name_plural = _('Ofertas de trabajo')
        ordering = ['-fecha_publicacion']
        permissions = [
            ('destacar_oferta', 'Puede destacar ofertas'),
        ]

    def __str__(self):
        tipo = "Servicio" if self.es_servicio else "Empleo"
        return f"{self.nombre} ({tipo})"

    def clean(self):
        # 🚦 PROTECCIÓN: si aún no hay creador, salimos y dejamos que el formulario lo asigne
        if not self.creador_id:
            return

        # --- lógica original ---
        if not self.pk:  # Solo para nuevas ofertas
            if hasattr(self.creador, 'empresa'):
                self.empresa = self.creador.empresa
                self.es_servicio = False
            elif hasattr(self.creador, 'personanatural'):
                self.es_servicio = True
                self.empresa = None

        if self.fecha_cierre and self.fecha_cierre < timezone.now().date():
            raise ValidationError(_('La fecha de cierre no puede ser en el pasado'))

    @property
    def tipo_oferta(self):
        return _("Servicio") if self.es_servicio else _("Empleo")

    @property
    def puede_postular(self, usuario):
        """Determina si un usuario puede postular a esta oferta"""
        if self.es_servicio:
            return usuario != self.creador and hasattr(usuario, 'empresa')
        else:
            return usuario != self.creador and hasattr(usuario, 'personanatural')
    def marcar_como_urgente(self):
        """Marca esta oferta como urgente."""
        self.urgente = True
        self.save(update_fields=['urgente'])

    def desmarcar_urgencia(self):
        """Desactiva el estado urgente de esta oferta."""
        self.urgente = False
        self.save(update_fields=['urgente'])

    def es_urgente(self):
        """Indica si la oferta está marcada como urgente."""
        return self.urgente

# -----------------------------
# Postulación
# -----------------------------
class Postulacion(models.Model):
    ESTADOS = [
        ('pendiente', _('Pendiente')),
        ('filtrado', _('Filtrado')),
        ('match', _('Match')),
        ('contratado', _('Contratado')),
        ('rechazado', _('Rechazado')),
        ('finalizado', _('Finalizado')),
    ]
    persona = models.ForeignKey(PersonaNatural, on_delete=models.CASCADE, related_name='postulaciones')
    oferta = models.ForeignKey(OfertaTrabajo, on_delete=models.CASCADE, related_name='postulaciones_recibidas')
    cv_enviado = models.ForeignKey(
        CV, on_delete=models.SET_NULL, verbose_name=_('CV enviado'), null=True, blank=True, related_name='+'
    )
    fecha_postulacion = models.DateTimeField(_('Fecha de postulación'), auto_now_add=True)
    mensaje = models.TextField(_('Mensaje del postulante'), blank=True)
    estado = models.CharField(_('Estado'), max_length=20, choices=ESTADOS, default='pendiente')
    feedback = models.TextField(_('Feedback'), blank=True)
    # --- CAMBIO AÑADIDO ---
    filtrada = models.BooleanField(_('Filtrada'), default=False, help_text=_('Indica si la postulación ha sido filtrada manualmente'))

    class Meta:
        verbose_name = _('Postulación')
        verbose_name_plural = _('Postulaciones')
        ordering = ['-fecha_postulacion']
        unique_together = ['persona', 'oferta']
        indexes = [
            models.Index(fields=['persona']),
            models.Index(fields=['oferta']),
            models.Index(fields=['estado']),
            models.Index(fields=['filtrada']), # Añadimos un índice para el nuevo campo
        ]

    def __str__(self):
        # Accede al nombre de la persona a través de la relación
        return f"{self.persona} postuló a {self.oferta.nombre}"

    def clean(self):
        """Asigna CV por defecto si no se especifica."""
        super().clean()
        if not self.cv_enviado and hasattr(self.persona, 'cv') and self.persona.cv:
            self.cv_enviado = self.persona.cv

    def puede_valorar(self, usuario_actual: Usuario) -> tuple[bool, Usuario | None]:
        if self.estado != 'finalizado':  # <-- CAMBIO CLAVE
            return False, None
        emisor = usuario_actual
        receptor = None
        if emisor == self.persona.usuario:
            receptor = self.oferta.creador
        elif emisor == self.oferta.creador:
            receptor = self.persona.usuario
        else:
            return False, None
        if receptor is None:
            return False, None
        valoracion_existente = Valoracion.objects.filter(
            emisor=emisor, receptor=receptor, postulacion=self
        ).exists()
        return not valoracion_existente, receptor

# -----------------------------
# Valoración
# -----------------------------
class Valoracion(models.Model):
    # Enlaza a tu modelo Usuario personalizado
    emisor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='valoraciones_emitidas')
    receptor = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='valoraciones_recibidas')
    postulacion = models.ForeignKey(
        Postulacion, on_delete=models.SET_NULL, null=True, blank=True, related_name='valoraciones'
    )
    puntuacion = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comentario = models.TextField(blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _('Valoración')
        verbose_name_plural = _('Valoraciones')
        unique_together = [['emisor', 'receptor', 'postulacion']]
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['emisor']),
            models.Index(fields=['receptor']),
            models.Index(fields=['postulacion']),
        ]

    def __str__(self):
        contexto = f" (Post. ID: {self.postulacion.id})" if self.postulacion else ""
        # Accede al RUT/username del emisor/receptor
        return f"Valoración de {self.emisor.username} a {self.receptor.username}{contexto} ({self.puntuacion}/5)"
    

# -----------------------------
# Muestra Trabajo
# -----------------------------
class MuestraTrabajo(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='muestras_trabajo')
    archivo = models.FileField(upload_to='muestras_trabajo/')
    titulo = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    fecha_subida = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.titulo} ({self.usuario.username})"

    def es_imagen(self):
        return self.archivo.name.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
