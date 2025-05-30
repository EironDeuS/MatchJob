# En tu_app/forms.py

from django import forms
# from django.contrib.auth.forms import ReadOnlyPasswordHashField # Solo si usas UsuarioChangeForm
from .models import Usuario, PersonaNatural, Empresa, Valoracion # Importa tus modelos
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError # Para validación personalizada
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import OfertaTrabajo, Categoria
from django.core.exceptions import ValidationError
from django.utils import timezone
import re
from pypdf import PdfReader
from pypdf.errors import PdfReadError 

# --- LoginForm (Sin cambios, parece correcto para login con RUT) ---
from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re

from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.core.validators import RegexValidator
from django.core.exceptions import ValidationError
import re

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='RUT',
        max_length=12,  # Longitud máxima para RUT con guión: 12345678-9
        widget=forms.TextInput(attrs={
            'placeholder': '12345678-9',
            'class': 'form-control',
            'autocomplete': 'rut'
        }),
        help_text="Ingrese su RUT con guión (ej: 12345678-9)"
    )
    
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Ingrese su contraseña',
            'class': 'form-control',
            'autocomplete': 'current-password'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].validators.append(self.validate_rut_format)
    
    def validate_rut_format(self, value):
        """
        Valida el formato del RUT (con guión pero sin puntos)
        """
        rut = value.upper()
        
        # Validar formato básico (permite ceros al inicio para empresas)
        if not re.match(r'^0*\d{7,8}-[\dK]$', rut):
            raise ValidationError("El formato del RUT es incorrecto. Debe ser: 12345678-9")
        
        return rut
    
    def clean_rut(self, value):
        """
        Valida el dígito verificador del RUT
        """
        rut = value.upper().replace("-", "")
        
        # Separar cuerpo y dígito verificador
        cuerpo = rut[:-1]
        dv = rut[-1]
        
        # Calcular dígito verificador esperado
        suma = 0
        multiplo = 2
        
        for c in reversed(cuerpo):
            suma += int(c) * multiplo
            multiplo = multiplo + 1 if multiplo < 7 else 2
        
        dv_esperado = 11 - (suma % 11)
        if dv_esperado == 11:
            dv_esperado = '0'
        elif dv_esperado == 10:
            dv_esperado = 'K'
        else:
            dv_esperado = str(dv_esperado)
        
        if dv != dv_esperado:
            raise ValidationError("El RUT ingresado no es válido (dígito verificador incorrecto)")
        
        # Retornar RUT con guión (sin puntos)
        return f"{cuerpo}-{dv}"
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        try:
            # Primero validar formato
            rut_formatted = self.validate_rut_format(username)
            # Luego validar dígito verificador
            return self.clean_rut(rut_formatted)
        except ValidationError as e:
            raise forms.ValidationError(e.message)

class CVValidationMixin(forms.Form):
    """
    MixIn para añadir la validación de CV a cualquier formulario que necesite.
    Contiene el campo 'cv_archivo' y el método 'clean_cv_archivo'.
    """
    cv_archivo = forms.FileField(
        label="Actualizar Currículum Vitae (PDF)",
        required=False, # Es importante que sea False en edición, no siempre subirán uno
        help_text="Sube tu CV actualizado en formato PDF. Tamaño máximo 5MB.",
        widget=forms.ClearableFileInput(attrs={'class':'form-control', 'accept': '.pdf'})
    )

    def clean_cv_archivo(self):
        """
        Valida que el archivo subido sea un PDF, tenga un tamaño razonable
        y que su contenido parezca ser un currículum vitae.
        """
        archivo = self.cleaned_data.get('cv_archivo')

        # Manejar casos donde no se sube un archivo nuevo o se marca para borrar el existente.
        # Si el usuario marca el checkbox "Borrar" (ClearableFileInput), el valor es False.
        # Si no sube nada y no marca "Borrar", el valor es None.
        if archivo is False: # El usuario marcó para borrar el archivo existente
            return False # Retorna False para indicar a la vista que debe borrarlo
        elif not archivo: # No se subió un nuevo archivo y no se marcó para borrar
            return None # Retorna None para indicar que no hay nuevo archivo para procesar

        # 1. Validación de tipo de archivo por extensión
        if not archivo.name.lower().endswith('.pdf'):
            raise ValidationError("Solo se permiten archivos PDF.")

        # 2. Validación de tamaño del archivo
        MAX_SIZE_MB = 5 # Definir el tamaño máximo permitido
        if archivo.size > MAX_SIZE_MB * 1024 * 1024: # Convertir MB a bytes
            raise ValidationError(f"El archivo no puede superar los {MAX_SIZE_MB}MB.")

        # --- VALIDACIÓN DE CONTENIDO (Búsqueda de palabras clave en el PDF) ---
        try:
            archivo.seek(0) # ¡MUY IMPORTANTE! Restablecer el puntero del archivo al principio
                             # para que pypdf pueda leerlo.
            reader = PdfReader(archivo)

            if not reader.pages: # Si el PDF no tiene páginas o está vacío.
                raise ValidationError("El archivo PDF está vacío o corrupto.")

            text_content = ""
            # Leer solo las primeras N páginas para eficiencia, no todo el documento.
            pages_to_read = min(len(reader.pages), 5) # Lee un máximo de 5 páginas.

            for i in range(pages_to_read):
                page = reader.pages[i]
                extracted_page_text = page.extract_text()
                if extracted_page_text:
                    text_content += extracted_page_text + " "

            text_content = text_content.lower() # Convertir a minúsculas para una búsqueda insensible a mayúsculas/minúsculas

            cv_keywords = [
                "experiencia laboral", "formación académica", "habilidades",
                "educación", "resumen profesional", "objetivo profesional",
                "aptitudes", "idiomas", "proyectos", "certificaciones",
                "perfil profesional", "datos personales", "contacto",
                "currículum vitae", "empleo", "puesto", "logros", "licencias",
                "reconocimientos", "publicaciones", "idioma", "nacionalidad",
                "fecha de nacimiento", "disponibilidad", "intereses", "conocimientos"
            ]

            found_keywords_count = sum(1 for keyword in cv_keywords if keyword in text_content)
            min_text_length = 150 # Longitud mínima de texto para considerar que es un CV.

            # Si no se encuentran suficientes palabras clave o el texto es muy corto
            if found_keywords_count < 3 or len(text_content) < min_text_length:
                raise ValidationError(
                    "El contenido del archivo PDF no parece ser un currículum vitae. "
                    "Asegúrese de subir un CV con texto y estructura de CV."
                )

        except PdfReadError: # Errores específicos de pypdf si el PDF está malformado
            raise ValidationError("El archivo PDF está corrupto o no es un PDF válido.")
        except Exception as e:
            # Captura otros errores inesperados durante el procesamiento del PDF
            print(f"DEBUG: Error inesperado al procesar PDF en Edición: {e}") # Útil para depuración local
            raise ValidationError(
                "Ocurrió un error al procesar el archivo PDF. Por favor, intente con otro archivo."
            )

        archivo.seek(0) # ¡MUY IMPORTANTE! Restablecer el puntero del archivo nuevamente
                         # para que Django pueda guardarlo después de la validación.
        return archivo

# --- Formulario de Registro Actualizado ---
# --- Tu RegistroForm, ahora heredando de CVValidationMixin ---
class RegistroForm(CVValidationMixin, forms.Form):
    # Aquí irían todos los campos que ya tienes en tu RegistroForm original
    # (username, correo, password, tipo_usuario, etc., y los condicionales de PersonaNatural/Empresa)

    username = forms.CharField(
        label="RUT (sin puntos ni guión) o Nombre de Usuario",
        max_length=12,
        required=True,
        help_text='Para persona natural: RUT (Ej: 12345678K). Para empresa: RUT (Ej: 761234567).'
    )
    correo = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'tu@ejemplo.com'})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 8 caracteres'})
    )
    confirm_password = forms.CharField(
        label="Confirmar Contraseña",
        widget=forms.PasswordInput(attrs={'placeholder': 'Repite la contraseña'})
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+569 XXXXXXXX'})
    )
    direccion = forms.CharField(
        label="Dirección",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Calle, número, comuna'})
    )

    TIPO_USUARIO_CHOICES = [
        ('persona', 'Persona Natural'),
        ('empresa', 'Empresa'),
    ]
    tipo_usuario = forms.ChoiceField(
        label="Tipo de Usuario",
        choices=TIPO_USUARIO_CHOICES,
        widget=forms.RadioSelect
    )

    # Campos específicos para Persona Natural (serán opcionales/no requeridos por defecto)
    nombres = forms.CharField(label="Nombres", max_length=100, required=False)
    apellidos = forms.CharField(label="Apellidos", max_length=100, required=False)
    fecha_nacimiento = forms.DateField(label="Fecha de Nacimiento", required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    nacionalidad = forms.CharField(label="Nacionalidad", max_length=50, required=False)

    # Campos específicos para Empresa (serán opcionales/no requeridos por defecto)
    nombre_empresa = forms.CharField(label="Nombre de Empresa", max_length=200, required=False)
    razon_social = forms.CharField(label="Razón Social", max_length=200, required=False)
    giro = forms.CharField(label="Giro", max_length=200, required=False)


    # El campo 'cv_archivo' y su método 'clean_cv_archivo'
    # SON HEREDADOS automáticamente de CVValidationMixin.
    # No necesitas definirlos aquí de nuevo.

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        tipo_usuario = cleaned_data.get("tipo_usuario")
        username = cleaned_data.get("username") # En registro, username es el RUT

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Las contraseñas no coinciden.")

        if Usuario.objects.filter(username=username).exists():
            self.add_error('username', "Este RUT o nombre de usuario ya está registrado.")
        if Usuario.objects.filter(correo=cleaned_data.get('correo')).exists():
            self.add_error('correo', "Este correo electrónico ya está registrado.")

        # Lógica condicional para requerir campos según el tipo_usuario
        if tipo_usuario == 'persona':
            required_fields = ['nombres', 'apellidos', 'fecha_nacimiento', 'nacionalidad']
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, "Este campo es obligatorio para el perfil de persona natural.")
            # Si el CV es obligatorio para personas al registrarse:
            # if not cleaned_data.get('cv_archivo'):
            #     self.add_error('cv_archivo', "Es obligatorio subir un Currículum Vitae.")

        elif tipo_usuario == 'empresa':
            required_fields = ['nombre_empresa', 'razon_social', 'giro']
            for field_name in required_fields:
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, "Este campo es obligatorio para el perfil de empresa.")

        return cleaned_data

    # Puedes mantener o quitar este clean_username si tienes una validación más compleja de RUT
    # def clean_username(self):
    #     username = self.cleaned_data['username']
    #     # Aquí podrías añadir una validación de formato de RUT chileno, si no la haces en la vista.
    #     return username


class UsuarioCreationForm(forms.ModelForm):
    """Formulario para crear usuarios DESDE EL ADMIN (o similar)."""
    password = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    # password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput) # Descomentar si se necesita confirmación aquí

    class Meta:
        model = Usuario
        # Añadir 'direccion' a los fields
        fields = ('username', 'correo', 'telefono', 'direccion', 'tipo_usuario')

    # def clean_password2(self): ... # Añadir si se usa confirmación

    def save(self, commit=True):
        user = super().save(commit=False)
        # Usar el password del form, no password1
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save() # Esto llamará al save() del modelo Usuario que crea el perfil
        return user

class UsuarioChangeForm(forms.ModelForm):
     """Formulario para actualizar usuarios DESDE EL ADMIN."""
     # password = ReadOnlyPasswordHashField() # Ya no es necesario con AbstractBaseUser (?) Revisa la documentación si usas el admin.

     class Meta:
         model = Usuario
         # Añadir 'direccion'. Quitar 'password'.
         fields = ('username', 'correo', 'telefono', 'direccion', 'tipo_usuario', 'is_active', 'is_staff', 'is_superuser')

     # def clean_password(self): ... # Ya no es necesario




from django import forms
from django.utils import timezone
from django.utils.translation import gettext as _
import googlemaps
from django.conf import settings
from .models import OfertaTrabajo, Categoria

class OfertaTrabajoForm(forms.ModelForm):
    ubicacion = forms.CharField(
        label=_('Ubicación'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'ubicacionInput',
            'placeholder': _('Ej: Santiago, Chile')
        })
    )
    
    class Meta:
        model = OfertaTrabajo
        fields = [
            'categoria', 'nombre', 'descripcion', 'requisitos',
            'beneficios', 'salario', 'latitud', 'longitud', 'direccion',
            'tipo_contrato', 'fecha_cierre', 'esta_activa', 'urgente'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'requisitos': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'beneficios': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'fecha_cierre': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
            'urgente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
            'direccion': forms.HiddenInput(),
        }
        labels = {
            'esta_activa': _('Publicar inmediatamente'),
            'tipo_contrato': _('Tipo de Contrato'),
            'urgente': _('¿Es una oferta urgente?')
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # Configuración dinámica según tipo de usuario
        if self.user and hasattr(self.user, 'empresa'):
            self.fields['tipo_contrato'].required = True
            self.fields['ubicacion'].required = True
            self.fields['nombre'].label = _('Nombre del puesto')
        else:
            self.fields['nombre'].label = _('Título de tu servicio')
            self.fields['descripcion'].label = _('Descripción de tu servicio')
            self.fields['requisitos'].label = _('Qué necesitas para el servicio')
            self.fields.pop('tipo_contrato', None)

        # Configuración común
        self.fields['categoria'].queryset = Categoria.objects.filter(activa=True)
        self.fields['fecha_cierre'].widget.attrs['min'] = timezone.now().date().isoformat()

        # Si es una instancia existente, establecer valores iniciales
        if self.instance.pk and self.instance.latitud and self.instance.longitud:
            self.fields['ubicacion'].initial = self.instance.direccion
            self.initial['latitud'] = self.instance.latitud
            self.initial['longitud'] = self.instance.longitud
            self.initial['direccion'] = self.instance.direccion

    def clean(self):
        cleaned_data = super().clean()
        
        # Validación para empresas
        if hasattr(self.user, 'empresa') and not cleaned_data.get('tipo_contrato'):
            self.add_error('tipo_contrato', _('Este campo es obligatorio para ofertas de empleo'))
        
        # Validación de ubicación
        ubicacion = cleaned_data.get('ubicacion')
        if ubicacion and not (cleaned_data.get('latitud') and cleaned_data.get('longitud')):
            self.add_error('ubicacion', _('Debes seleccionar una ubicación válida en el mapa'))
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.creador = self.user

        # Procesar ubicación si se proporcionó
        ubicacion = self.cleaned_data.get('ubicacion')
        latitud = self.cleaned_data.get('latitud')
        longitud = self.cleaned_data.get('longitud')
        
        if latitud and longitud:
            # Geocodificación inversa para obtener dirección si no está proporcionada
            if not instance.direccion and ubicacion:
                instance.direccion = ubicacion
            elif not instance.direccion:
                try:
                    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                    reverse_geocode = gmaps.reverse_geocode((latitud, longitud))
                    if reverse_geocode:
                        instance.direccion = reverse_geocode[0]['formatted_address']
                except Exception as e:
                    print(f"Error en geocodificación inversa: {e}")

        # Asignar empresa o marcar como servicio
        if hasattr(self.user, 'empresa'):
            instance.empresa = self.user.empresa
            instance.es_servicio = False
        else:
            instance.es_servicio = True

        if commit:
            instance.save()

        return instance
    
class EditarOfertaTrabajoForm(forms.ModelForm):
    ubicacion = forms.CharField(
        label=_('Ubicación'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'ubicacionInput',
            'placeholder': _('Ej: Santiago, Chile')
        })
    )
    
    class Meta:
        model = OfertaTrabajo
        fields = [
            'categoria', 'nombre', 'descripcion', 'requisitos',
            'beneficios', 'salario', 'latitud', 'longitud', 'direccion',
            'tipo_contrato', 'fecha_cierre', 'esta_activa', 'urgente'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'rows': 4, 
                'class': 'form-control',
                'placeholder': _('Describe detalladamente la oferta')
            }),
            'requisitos': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': _('Lista los requisitos necesarios')
            }),
            'beneficios': forms.Textarea(attrs={
                'rows': 3, 
                'class': 'form-control',
                'placeholder': _('Menciona los beneficios ofrecidos')
            }),
            'fecha_cierre': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'form-control'
            }),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
            'salario': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': _('Ej: $1,000,000 - $1,500,000')
            }),
            'latitud': forms.HiddenInput(),
            'longitud': forms.HiddenInput(),
            'direccion': forms.HiddenInput(),
            'urgente': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'esta_activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'esta_activa': _('Publicar inmediatamente'),
            'tipo_contrato': _('Tipo de Contrato'),
            'urgente': _('¿Es una oferta urgente?'),
            'fecha_cierre': _('Fecha de cierre (opcional)'),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Configuración dinámica según tipo de usuario
        if self.user and hasattr(self.user, 'empresa'):
            self.fields['tipo_contrato'].required = True
            self.fields['ubicacion'].required = True
            self.fields['nombre'].label = _('Nombre del puesto')
        else:
            self.fields['nombre'].label = _('Título de tu servicio')
            self.fields['descripcion'].label = _('Descripción de tu servicio')
            self.fields['requisitos'].label = _('Qué necesitas para el servicio')
            self.fields.pop('tipo_contrato', None)
        
        # Configuración común
        self.fields['categoria'].queryset = Categoria.objects.filter(activa=True)
        
        # Establecer fecha mínima
        min_date = timezone.now().date()
        if self.instance and self.instance.fecha_cierre:
            min_date = min(min_date, self.instance.fecha_cierre)
        self.fields['fecha_cierre'].widget.attrs['min'] = min_date.isoformat()
        
        # Inicializar valores de ubicación si existen
        if self.instance.pk and self.instance.latitud and self.instance.longitud:
            self.fields['ubicacion'].initial = self.instance.direccion
            self.initial['latitud'] = self.instance.latitud
            self.initial['longitud'] = self.instance.longitud
            self.initial['direccion'] = self.instance.direccion

    def clean(self):
        cleaned_data = super().clean()
        
        # Validación para empresas
        if hasattr(self.user, 'empresa') and not cleaned_data.get('tipo_contrato'):
            self.add_error('tipo_contrato', _('Este campo es obligatorio para ofertas de empleo'))
        
        # Validación de ubicación
        ubicacion = cleaned_data.get('ubicacion')
        if hasattr(self.user, 'empresa') and not (cleaned_data.get('latitud') and cleaned_data.get('longitud')):
            self.add_error('ubicacion', _('Debes seleccionar una ubicación válida en el mapa'))
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        
        # Procesar ubicación si se proporcionó
        ubicacion = self.cleaned_data.get('ubicacion')
        latitud = self.cleaned_data.get('latitud')
        longitud = self.cleaned_data.get('longitud')
        
        if latitud and longitud:
            # Geocodificación inversa para obtener dirección si no está proporcionada
            if not instance.direccion and ubicacion:
                instance.direccion = ubicacion
            elif not instance.direccion:
                try:
                    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                    reverse_geocode = gmaps.reverse_geocode((latitud, longitud))
                    if reverse_geocode:
                        instance.direccion = reverse_geocode[0]['formatted_address']
                except Exception as e:
                    print(f"Error en geocodificación inversa: {e}")

        if commit:
            instance.save()
            self.save_m2m()  # Para relaciones many-to-many si las hay

        return instance


# --- Tu formulario de edición de perfil para Persona Natural ---
# Hereda de CVValidationMixin para obtener el campo cv_archivo y su método clean_cv_archivo.
class EditarPerfilPersonaForm(CVValidationMixin, forms.ModelForm):
    # Campos de Usuario:
    correo = forms.EmailField(
        label="Correo electrónico",
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'tu@ejemplo.com'})
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: +56912345678'})
    )
    direccion = forms.CharField(
        label="Dirección",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Calle Falsa 123'})
    )

    # Campo para CV: solo para subir nuevo o reemplazar
    cv_archivo = forms.FileField(
        label="Subir nuevo Currículum Vitae (PDF)", # Cambiado el label
        required=False, # Si no sube uno nuevo, se mantiene el anterior
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )
    # ¡ELIMINADO: borrar_cv_existente = forms.BooleanField(...)

    class Meta:
        model = PersonaNatural
        fields = ['nombres', 'apellidos', 'fecha_nacimiento', 'nacionalidad']
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tus Nombres'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tus Apellidos'}),
            'fecha_nacimiento': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'nacionalidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Chilena'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        if self.instance and hasattr(self.instance, 'usuario') and self.instance.usuario:
            if not self.is_bound:
                self.fields['correo'].initial = self.instance.usuario.correo
                self.fields['telefono'].initial = self.instance.usuario.telefono
                self.fields['direccion'].initial = self.instance.usuario.direccion

        # No es necesario inicializar cv_archivo.initial si no es un ClearableFileInput
        # y solo lo usamos para la carga de un NUEVO archivo.
        # Si quisieras mostrar el nombre del archivo actual en el input, necesitarías un widget personalizado.
        # Por ahora, el FileInput estándar no muestra el nombre del archivo actual, solo el botón "Elegir archivo".
        # La lógica de mostrar el enlace del CV actual va en el template.

    def clean(self):
        cleaned_data = super().clean()
        return cleaned_data

    # Asegúrate de que tu CVValidationMixin tenga el clean_cv_archivo para la validación del tipo PDF.
    # Si no lo tienes, deberías añadirlo aquí:
    # def clean_cv_archivo(self):
    #     archivo = self.cleaned_data.get('cv_archivo')
    #     if archivo:
    #         if not archivo.name.endswith('.pdf'):
    #             raise ValidationError("El archivo CV debe ser un PDF.")
    #     return archivo


class ValoracionForm(forms.ModelForm):
    class Meta:
        model = Valoracion
        fields = ['puntuacion', 'comentario']
        widgets = {
            'puntuacion': forms.RadioSelect(choices=[(i, f'{i} estrellas') for i in range(1, 6)]),
            'comentario': forms.Textarea(attrs={'placeholder': 'Escribe un comentario opcional...', 'rows': 4}),
        }
        labels = {
            'puntuacion': 'Calificación',
            'comentario': 'Comentario',
        }
