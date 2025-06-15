from django.contrib.auth.forms import PasswordResetForm
from django.contrib.auth import get_user_model
from django import forms # Primera aparición de 'django.forms'
from .models import Usuario, PersonaNatural, Empresa, Valoracion, CV, CertificadoAntecedentes # Importa tus modelos
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError # Para validación personalizada
from django.utils.translation import gettext_lazy as _
from django.utils.safestring import mark_safe
from .models import OfertaTrabajo, Categoria
from django.utils import timezone
import re
from pypdf import PdfReader
from pypdf.errors import PdfReadError
from django.core.validators import RegexValidator
import googlemaps
from django.conf import settings
from gestionOfertas.utils import validar_rut_empresa
from .utils import validate_rut_format, clean_rut, validar_rut_empresa 


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

class CVValidationMixin:
    """
    Mixin para validar archivos CV.
    Incluye validación de formato PDF y validación de contenido básico por palabras clave.
    """
    def clean_cv_archivo(self):
        archivo = self.cleaned_data.get('cv_archivo')
        if archivo:
            if not archivo.name.lower().endswith('.pdf'):
                raise ValidationError("El archivo CV debe ser un PDF.")
            try:
                reader = PdfReader(archivo)
                if len(reader.pages) == 0:
                    raise ValidationError("El PDF del CV parece estar vacío o corrupto.")

                text_content = ""
                for page in reader.pages:
                    extracted_page_text = page.extract_text()
                    if extracted_page_text:
                        text_content += extracted_page_text
                
                if not self._contiene_palabras_clave_cv(text_content):
                    raise ValidationError(
                        "El contenido del CV no parece ser un currículum válido. "
                        "Asegúrate de incluir secciones como experiencia, educación, habilidades, etc."
                    )
                
                archivo.seek(0) # ¡Importante! Rebobinar el archivo después de la lectura
            except PdfReadError:
                raise ValidationError("El archivo subido no es un PDF válido o está corrupto.")
            except Exception as e:
                raise ValidationError(f"Error inesperado al procesar el archivo PDF del CV: {e}")
        return archivo

    def _contiene_palabras_clave_cv(self, text_content):
        keywords = ['experiencia laboral', 'educación', 'habilidades', 'currículum', 
                    'resumen profesional', 'empleo', 'formación académica', 
                    'referencias', 'logros']
        text_content_lower = text_content.lower()
        return any(keyword in text_content_lower for keyword in keywords)

class CertificadoValidationMixin:
    """
    Mixin para validar archivos de Certificado de Antecedentes (PDF).
    Incluye validación de formato PDF y validación de contenido básico por palabras clave.
    """
    def clean_certificado_pdf(self):
        archivo = self.cleaned_data.get('certificado_pdf')
        if archivo:
            if not archivo.name.lower().endswith('.pdf'):
                raise ValidationError("El archivo del certificado debe ser un PDF.")
            try:
                reader = PdfReader(archivo)
                if len(reader.pages) == 0:
                    raise ValidationError("El PDF del certificado parece estar vacío o corrupto.")
                
                text_content = ""
                for page in reader.pages:
                    extracted_page_text = page.extract_text()
                    if extracted_page_text:
                        text_content += extracted_page_text

                if not self._contiene_palabras_clave_certificado(text_content):
                    raise ValidationError(
                        "El contenido del certificado no parece ser válido. "
                        "Asegúrate de que sea un certificado de antecedentes."
                    )
                
                archivo.seek(0) # ¡Importante! Rebobinar el archivo después de la lectura
            except PdfReadError:
                raise ValidationError("El archivo subido no es un PDF válido o está corrupto.")
            except Exception as e:
                raise ValidationError(f"Error inesperado al procesar el archivo PDF del certificado: {e}")
        return archivo

    def _contiene_palabras_clave_certificado(self, text_content):
        keywords_general = ['certificado de antecedentes', 'registro civil', 'servicio de registro civil e identificación']
        keywords_content = ['sin antecedentes', 'sin anotaciones', 'condenas', 'prisión'] # Al menos una de estas para el contenido
        
        text_content_lower = text_content.lower()
        
        # Debe contener al menos una palabra clave general Y al menos una palabra clave de contenido
        present_general = any(k in text_content_lower for k in keywords_general)
        present_content = any(k in text_content_lower for k in keywords_content)
        
        return present_general and present_content
    
# --- RegistroForm: Cambios para añadir el campo de certificado ---
class RegistroForm(CVValidationMixin, CertificadoValidationMixin, forms.Form):
    # --- Campos del Modelo Usuario ---
    tipo_usuario = forms.ChoiceField(
        choices=[c for c in Usuario.TIPO_USUARIO_CHOICES if c[0] != 'admin'],
        required=True,
        widget=forms.Select(attrs={'onchange': 'toggleUsuarioFields()', 'class': 'form-select'}),
        label="Tipo de Usuario"
    )

    username = forms.CharField( # RUT
        label="RUT (con guión, sin puntos)",
        max_length=12,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': '12345678-9', 'class': 'form-control'})
    )
    correo = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'tu@ejemplo.com', 'class': 'form-control'})
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': '+569 XXXXXXXX', 'class': 'form-control'})
    )
    direccion = forms.CharField(
        label="Dirección",
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Calle, número, comuna', 'class': 'form-control'})
    )
    password = forms.CharField(
        label="Contraseña",
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Mínimo 8 caracteres', 'class': 'form-control'})
    )
    confirm_password = forms.CharField(
        label="Confirmar contraseña",
        required=True,
        widget=forms.PasswordInput(attrs={'placeholder': 'Repite la contraseña', 'class': 'form-control'})
    )

    # --- Campos del Perfil PersonaNatural ---
    nombres = forms.CharField(
        label="Nombres",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    apellidos = forms.CharField(
        label="Apellidos",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    fecha_nacimiento = forms.DateField(
        label="Fecha de Nacimiento",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'})
    )
    nacionalidad = forms.CharField(
        label="Nacionalidad",
        max_length=50,
        initial='Chilena',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # --- Campos del Perfil Empresa ---
    nombre_empresa = forms.CharField(
        label="Nombre de la Empresa",
        max_length=100,
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    razon_social = forms.CharField(
        label="Razón Social",
        max_length=100,
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    giro = forms.CharField(
        label="Giro Comercial",
        max_length=100,
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # --- CAMPOS DE SUBIDA DE ARCHIVOS ---
    certificado_pdf = forms.FileField(
        label="Subir Certificado de Antecedentes (PDF)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'application/pdf'}),
        help_text="Opcional. El certificado se verificará y se procesará automáticamente."
    )
    
    cv_archivo = forms.FileField(
        label="Subir Currículum Vitae (PDF)",
        required=False,
        widget=forms.ClearableFileInput(attrs={'class': 'form-control', 'accept': 'application/pdf'}),
        help_text="Opcional. El CV se procesará automáticamente para extraer tus datos."
    )

    # --- Métodos clean (validación de campos individuales) ---
    def clean_username(self):
        username = self.cleaned_data.get('username')
        # Verificar si el RUT ya está registrado
        if Usuario.objects.filter(username=username).exists():
            raise ValidationError("Este RUT o nombre de usuario ya está registrado.")
        
        # Estandarización y validación del RUT usando las funciones importadas
        try:
            # ¡CORRECCIÓN AQUÍ: Llamadas directas a las funciones importadas!
            rut_formatted = validate_rut_format(username)
            return clean_rut(rut_formatted)
        except ValidationError as e:
            raise forms.ValidationError(e.message) # Relanza la ValidationError de Django

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if Usuario.objects.filter(correo=correo).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return correo

    # --- Método clean general (validación de múltiples campos y lógica de API) ---
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password") 

        if password and confirm_password and password != confirm_password:
            self.add_error('confirm_password', "Las contraseñas no coinciden.")

        tipo_usuario = cleaned_data.get('tipo_usuario')
        username_rut = cleaned_data.get('username') # Ya validado y formateado por clean_username

        # Validaciones para Persona Natural
        if tipo_usuario == 'persona': 
            required_fields_persona = {
                'nombres': 'Nombres',
                'apellidos': 'Apellidos',
                'fecha_nacimiento': 'Fecha de Nacimiento',
                'nacionalidad': 'Nacionalidad'
            }
            for field_name, label_name in required_fields_persona.items():
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, f"{label_name} es requerido para personas.")

        # Validaciones para Empresa (lógica del SII sin cambios)
        elif tipo_usuario == 'empresa':
            if username_rut: 
                # ¡CORRECCIÓN AQUÍ: Llamada directa a la función importada!
                resultado = validar_rut_empresa(username_rut) 
                if resultado['valida']:
                    api_data = resultado['datos']
                    
                    api_razon_social = api_data.get('razonSocial')
                    if api_razon_social:
                        cleaned_data['razon_social'] = api_razon_social
                        cleaned_data['nombre_empresa'] = api_razon_social # Asignar también a nombre_empresa
                    
                    api_actividades = api_data.get('actividadesEconomicas')
                    if api_actividades and len(api_actividades) > 0:
                        first_giro_desc = api_actividades[0].get('descripcion')
                        if first_giro_desc:
                            cleaned_data['giro'] = first_giro_desc
                else:
                    self.add_error('username', f"❌ El RUT ingresado no es válido como empresa: {resultado.get('mensaje')}")
        
        return cleaned_data

    # --- MÉTODO ESENCIAL: save para crear la instancia de Usuario ---
    def save(self, commit=True):
        """
        Crea y guarda una instancia de Usuario basada en los datos validados del formulario.
        Esta función solo se encarga del objeto Usuario.
        Los perfiles (PersonaNatural/Empresa) y los archivos adjuntos se gestionan en la vista.
        """
        user = Usuario(
            username=self.cleaned_data['username'],
            correo=self.cleaned_data['correo'],
            telefono=self.cleaned_data.get('telefono'),
            direccion=self.cleaned_data.get('direccion'),
            tipo_usuario=self.cleaned_data['tipo_usuario'],
            is_active=True # Se activa al registrarse
        )
        user.set_password(self.cleaned_data['password'])
        
        if commit:
            user.save()
        
        return user 
# --- EditarPerfilPersonaForm: Cambios para añadir el campo de certificado ---
class EditarPerfilPersonaForm(CVValidationMixin, CertificadoValidationMixin, forms.ModelForm):
    # Campos de Usuario (del modelo Usuario directamente)
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

    # Campos de archivo (serán validados por las mixins)
    cv_archivo = forms.FileField( # Asegúrate que el nombre del campo sea este en tu template
        label="Subir nuevo Currículum Vitae (PDF)",
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )
    certificado_pdf = forms.FileField(
        label="Subir nuevo Certificado de Antecedentes (PDF)",
        required=False,
        widget=forms.FileInput(attrs={'class': 'form-control', 'accept': '.pdf'})
    )

    class Meta:
        model = PersonaNatural
        fields = ['nombres', 'apellidos', 'fecha_nacimiento', 'nacionalidad']
        widgets = {
            'nombres': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tus Nombres'}),
            'apellidos': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Tus Apellidos'}),
            'fecha_nacimiento': forms.DateInput(
                attrs={'type': 'date', 'class': 'form-control'},
                format='%Y-%m-%d'
            ),
            'nacionalidad': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ej: Chilena'}),
        }

    def __init__(self, *args, **kwargs):
        self.usuario_actual = kwargs.pop('usuario_actual', None) # Se guarda el objeto usuario aquí
        super().__init__(*args, **kwargs)

        # Inicializar campos de Usuario a partir de la instancia de Usuario
        # self.instance es el objeto PersonaNatural
        if self.instance and hasattr(self.instance, 'usuario') and self.instance.usuario and not self.is_bound:
            self.fields['correo'].initial = self.instance.usuario.correo
            self.fields['telefono'].initial = self.instance.usuario.telefono
            self.fields['direccion'].initial = self.instance.usuario.direccion

        # Lógica para mostrar CV y Certificado existentes
        if self.instance: # self.instance es la instancia de PersonaNatural
            try:
                # CV se relaciona con PersonaNatural via 'cv' (related_name)
                cv_instance = self.instance.cv
                if cv_instance.archivo_cv: # Asumiendo que 'archivo_cv' es el FileField en tu modelo CV
                    self.fields['cv_archivo'].help_text = mark_safe(
                        f'CV actual: <a href="{cv_instance.archivo_cv.url}" target="_blank">Ver CV</a>. Sube uno nuevo para reemplazar.'
                    )
            except CV.DoesNotExist:
                self.fields['cv_archivo'].help_text = "No has subido un CV aún. Sube uno aquí."
            except AttributeError:
                 self.fields['cv_archivo'].help_text = "No has subido un CV aún. Sube uno aquí."

            try:
                # CertificadoAntecedentes se relaciona con PersonaNatural via 'certificado_antecedentes' (related_name)
                cert_instance = self.instance.certificado_antecedentes
                if cert_instance.certificado_url:
                    self.fields['certificado_pdf'].help_text = mark_safe(
                        f'Certificado actual: <a href="{cert_instance.certificado_url}" target="_blank">Ver Certificado</a>. Sube uno nuevo para reemplazar.'
                    )
            except CertificadoAntecedentes.DoesNotExist:
                self.fields['certificado_pdf'].help_text = "No has subido un certificado de antecedentes aún. Sube uno aquí."
            except AttributeError:
                self.fields['certificado_pdf'].help_text = "No has subido un certificado de antecedentes aún. Sube uno aquí."


    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if correo:
            # Asegúrate que 'Usuario' sea el modelo de tu tabla de usuarios
            usuario_qs = Usuario.objects.filter(correo=correo)
            if self.usuario_actual:
                usuario_qs = usuario_qs.exclude(pk=self.usuario_actual.pk)
            if usuario_qs.exists():
                raise forms.ValidationError("Este correo ya está registrado.")
        return correo

    def clean(self):
        cleaned_data = super().clean()
        # Puedes añadir validaciones adicionales aquí
        return cleaned_data
    
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
            'salario': forms.NumberInput(attrs={
            'class': 'form-control',
            'step': 'any',  # Permite decimales
            'min': '0',     # Solo números positivos
            }),
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
    def clean_salario(self):
        salario = self.cleaned_data.get('salario')
        if salario is not None and not str(salario).isdigit():
            raise forms.ValidationError("El salario debe ser un número")
        return salario

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
    

from django import forms
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from .models import OfertaTrabajo, Categoria

class EditarOfertaTrabajoForm(forms.ModelForm):
    # Campo visible para autocompletado de ubicación
    ubicacion = forms.CharField(
        label=_('Ubicación'),
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'id': 'id_ubicacion',
            'placeholder': _('Escribe una dirección y selecciona una sugerencia')
        }),
    )

    # Campo de salario como número entero
    salario = forms.IntegerField(
        min_value=0,
        label=_('Salario'),
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': _('Ej: 1000000')
        })
    )

    class Meta:
        model = OfertaTrabajo
        fields = [
            'categoria', 'nombre', 'descripcion', 'requisitos',
            'beneficios', 'salario',
            'latitud', 'longitud', 'direccion',
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

        # Categorías activas
        self.fields['categoria'].queryset = Categoria.objects.filter(activa=True)

        # Fecha mínima en el selector de fecha
        min_date = timezone.now().date()
        if self.instance and self.instance.fecha_cierre:
            min_date = min(min_date, self.instance.fecha_cierre)
        self.fields['fecha_cierre'].widget.attrs['min'] = min_date.isoformat()

        # Si ya existe una oferta, inicializamos la ubicación visible
        if self.instance.pk and self.instance.direccion:
            self.fields['ubicacion'].initial = self.instance.direccion

    def clean(self):
        cleaned_data = super().clean()

        if hasattr(self.user, 'empresa'):
            if self.fields.get('tipo_contrato') and not cleaned_data.get('tipo_contrato'):
                self.add_error('tipo_contrato', _('Este campo es obligatorio para ofertas de empleo'))

            latitud = cleaned_data.get('latitud')
            longitud = cleaned_data.get('longitud')
            direccion_oculta = cleaned_data.get('direccion')

            if not (latitud and longitud and direccion_oculta):
                self.add_error('ubicacion', _('Debes seleccionar una ubicación válida en el mapa usando el autocompletado o arrastrando el marcador.'))
            elif self.fields['ubicacion'].required and not cleaned_data.get('ubicacion'):
                self.add_error('ubicacion', _('La dirección de ubicación es obligatoria.'))

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        if commit:
            instance.save()
            self.save_m2m()
        return instance





class ValoracionForm(forms.ModelForm):
    class Meta:
        model = Valoracion
        fields = ['puntuacion', 'comentario']
        widgets = {
            'comentario': forms.Textarea(attrs={
                'rows': 3,
                'class': 'form-control',
                'placeholder': 'Escribe tu opinión...'
            }),
        }
    
    def clean_puntuacion(self):
        puntuacion = self.cleaned_data.get('puntuacion')
        if not puntuacion or int(puntuacion) < 1 or int(puntuacion) > 5:
            raise forms.ValidationError("Por favor selecciona una puntuación entre 1 y 5 estrellas")
        return puntuacion


Usuario = get_user_model()

class CustomPasswordResetForm(PasswordResetForm):
    def get_users(self, email):
        active_users = Usuario._default_manager.filter(correo__iexact=email, is_active=True)
        return (u for u in active_users if u.has_usable_password())

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if not Usuario.objects.filter(correo__iexact=email, is_active=True).exists():
            raise forms.ValidationError("No existe una cuenta con ese correo.")
        return email