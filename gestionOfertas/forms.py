# En tu_app/forms.py

from django import forms
# from django.contrib.auth.forms import ReadOnlyPasswordHashField # Solo si usas UsuarioChangeForm
from .models import Usuario, PersonaNatural, Empresa # Importa tus modelos
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError # Para validación personalizada

# --- LoginForm (Sin cambios, parece correcto para login con RUT) ---
class LoginForm(AuthenticationForm):
    username = forms.CharField( # Mantenemos 'username' para el campo de login
        label='RUT',
        max_length=50, # Ajustar si es necesario
        widget=forms.TextInput(attrs={'placeholder': 'RUT (sin puntos, con guión)', 'class': 'form-control'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña', 'class': 'form-control'})
    )
    # __init__ se hereda bien, no necesita cambios si solo ajusta la etiqueta.


# --- Formulario de Registro Actualizado ---
class RegistroForm(forms.Form): # Cambiado a forms.Form en lugar de ModelForm
    """
    Formulario de registro que recopila datos para Usuario y el perfil correspondiente.
    """
    # --- Campos del Modelo Usuario ---
    tipo_usuario = forms.ChoiceField(
        choices=Usuario.TIPO_USUARIO_CHOICES[:-1], # Excluir 'admin' de las opciones públicas
        required=True,
        widget=forms.Select(attrs={'onchange': 'toggleUsuarioFields()'}),
        label="Tipo de Usuario"
    )
    username = forms.CharField( # RUT
        label="RUT",
        max_length=50, # Coincidir con el modelo
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'RUT (sin puntos, con guión)'})
    )
    correo = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Correo electrónico'})
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False, # Opcional como en el modelo
        widget=forms.TextInput(attrs={'placeholder': 'Teléfono (opcional)'})
    )
    # Dirección ahora es parte de Usuario
    direccion = forms.CharField(
        label="Dirección",
        max_length=255,
        required=False, # Opcional como en el modelo
        widget=forms.TextInput(attrs={'placeholder': 'Dirección (opcional)'})
    )
    password = forms.CharField(
        label="Contraseña",
        widget=forms.PasswordInput,
        required=True
    )
    password2 = forms.CharField(
        label="Confirmar contraseña",
        widget=forms.PasswordInput,
        required=True
    )

    # --- Campos del Perfil PersonaNatural ---
    nombres = forms.CharField(label="Nombres", max_length=100, required=False)
    apellidos = forms.CharField(label="Apellidos", max_length=100, required=False)
    fecha_nacimiento = forms.DateField(
        label="Fecha de Nacimiento",
        required=False,
        widget=forms.DateInput(attrs={'type': 'date'})
    )
    nacionalidad = forms.CharField(
        label="Nacionalidad",
        max_length=50,
        initial='Chilena',
        required=False
    )

    # --- Campos del Perfil Empresa ---
    nombre_empresa = forms.CharField(label="Nombre de la Empresa", max_length=100, required=False)
    # rut_empresa ya no existe en el modelo Empresa
    razon_social = forms.CharField(label="Razón Social", max_length=100, required=False)
    giro = forms.CharField(label="Giro Comercial", max_length=100, required=False)
    # Puedes añadir aquí pagina_web, redes_sociales si quieres recolectarlos en el registro

    def clean_username(self):
        """ Valida que el RUT (username) no exista ya. """
        username = self.cleaned_data.get('username')
        if Usuario.objects.filter(username=username).exists():
            raise ValidationError("Este RUT ya está registrado.")
        # Aquí podrías añadir validación del formato del RUT si quieres
        return username

    def clean_correo(self):
        """ Valida que el correo no exista ya. """
        correo = self.cleaned_data.get('correo')
        if Usuario.objects.filter(correo=correo).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return correo

    def clean_password2(self):
        """ Valida que las contraseñas coincidan. """
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise ValidationError("Las contraseñas no coinciden.")
        return password2

    def clean(self):
        """
        Validación cruzada de campos: asegura que los campos requeridos
        para el tipo de usuario seleccionado estén presentes.
        """
        cleaned_data = super().clean()
        tipo_usuario = cleaned_data.get('tipo_usuario')

        if tipo_usuario == 'persona':
            if not cleaned_data.get('nombres'):
                self.add_error('nombres', 'Este campo es requerido para personas.')
            if not cleaned_data.get('apellidos'):
                self.add_error('apellidos', 'Este campo es requerido para personas.')
            # Puedes añadir validaciones para otros campos de persona si son obligatorios

        elif tipo_usuario == 'empresa':
            if not cleaned_data.get('nombre_empresa'):
                self.add_error('nombre_empresa', 'Este campo es requerido para empresas.')
            # Puedes añadir validaciones para otros campos de empresa si son obligatorios

        return cleaned_data

# --- Formularios UsuarioCreationForm y UsuarioChangeForm ---
# Estos son útiles para el admin o gestión interna, pero no para el registro público.
# Hay que actualizarlos para incluir 'direccion' si los usas.

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
from django.utils.translation import gettext_lazy as _
from .models import OfertaTrabajo, Categoria
from django.core.exceptions import ValidationError
from django.utils import timezone

class OfertaTrabajoForm(forms.ModelForm):
    class Meta:
        model = OfertaTrabajo
        fields = [
            'categoria',
            'nombre', 
            'descripcion', 
            'requisitos',
            'beneficios',
            'salario', 
            'ubicacion', 
            'tipo_contrato',
            'fecha_cierre',
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': _('Describe detalladamente el puesto de trabajo')
            }),
            'requisitos': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('Lista los requisitos necesarios para el puesto')
            }),
            'beneficios': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': _('Menciona los beneficios que ofrece el puesto')
            }),
            'fecha_cierre': forms.DateInput(attrs={
                'type': 'date',
                'min': timezone.now().date().isoformat()
            }),
        }
        labels = {
            'categoria': _('Categoría'),
            'nombre': _('Título de la oferta'),
            'descripcion': _('Descripción del puesto'),
            'requisitos': _('Requisitos'),
            'beneficios': _('Beneficios'),
            'salario': _('Salario'),
            'ubicacion': _('Ubicación'),
            'tipo_contrato': _('Tipo de contrato'),
            'fecha_cierre': _('Fecha de cierre'),
        }
        help_texts = {
            'fecha_cierre': _('Opcional. Si no se especifica, la oferta permanecerá activa indefinidamente.'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        # Filtramos categorías activas
        self.fields['categoria'].queryset = Categoria.objects.filter(activa=True)
        
        # Marcamos campos opcionales
        for field in ['beneficios', 'salario', 'ubicacion', 'tipo_contrato', 'fecha_cierre']:
            self.fields[field].required = False

    def clean_fecha_cierre(self):
        fecha_cierre = self.cleaned_data.get('fecha_cierre')
        if fecha_cierre and fecha_cierre < timezone.now().date():
            raise ValidationError(_('La fecha de cierre no puede ser anterior a la fecha actual.'))
        return fecha_cierre