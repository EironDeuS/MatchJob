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

# --- LoginForm (Sin cambios, parece correcto para login con RUT) ---
class LoginForm(AuthenticationForm):
    username = forms.CharField( # Mantenemos 'username' para el campo de login
        label='RUT',
        max_length=50, # Ajustar si es necesario
        widget=forms.TextInput(attrs={'placeholder': 'RUT (sin puntos ni guión)', 'class': 'form-control'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña', 'class': 'form-control'})
    )
    # __init__ se hereda bien, no necesita cambios si solo ajusta la etiqueta.


# --- Formulario de Registro Actualizado ---
class RegistroForm(forms.Form):
    """
    Formulario de registro que recopila datos para Usuario y el perfil correspondiente.
    (Versión sin gettext_lazy para labels/help_text)
    """
    # --- Campos del Modelo Usuario ---
    tipo_usuario = forms.ChoiceField(
        choices=[c for c in Usuario.TIPO_USUARIO_CHOICES if c[0] != 'admin'], # Excluir admin
        required=True,
        widget=forms.Select(attrs={'onchange': 'toggleUsuarioFields()', 'class': 'form-select'}),
        label="Tipo de Usuario" # Sin _()
    )
    username = forms.CharField( # RUT
        label="RUT", # Sin _()
        max_length=50,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'RUT (sin puntos, con guión)', 'class': 'form-control'})
    )
    correo = forms.EmailField(
        label="Correo electrónico", # Sin _()
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Correo electrónico', 'class': 'form-control'})
    )
    telefono = forms.CharField(
        label="Teléfono", # Sin _()
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Teléfono (opcional)', 'class': 'form-control'})
    )
    direccion = forms.CharField(
        label="Dirección", # Sin _()
        max_length=255,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Dirección (opcional)', 'class': 'form-control'})
    )
    password = forms.CharField(
        label="Contraseña", # Sin _()
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    password2 = forms.CharField(
        label="Confirmar contraseña", # Sin _()
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )

    # --- Campos del Perfil PersonaNatural ---
    nombres = forms.CharField(label="Nombres", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellidos = forms.CharField(label="Apellidos", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    fecha_nacimiento = forms.DateField(label="Fecha de Nacimiento", required=False, widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}))
    nacionalidad = forms.CharField(label="Nacionalidad", max_length=50, initial='Chilena', required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # --- Campo CV ---
    cv_archivo = forms.FileField(
        label="Currículum Vitae (PDF)", # Sin _()
        required=False,
        help_text="Sube tu CV actualizado en formato PDF.", # Sin _()
        widget=forms.ClearableFileInput(attrs={'class':'form-control', 'accept': '.pdf'})
    )

    # --- Campos del Perfil Empresa ---
    nombre_empresa = forms.CharField(label="Nombre de la Empresa", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    razon_social = forms.CharField(label="Razón Social", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))
    giro = forms.CharField(label="Giro Comercial", max_length=100, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # --- Métodos clean (sin cambios) ---
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if Usuario.objects.filter(username=username).exists():
            # Sin _() para mensajes de error también
            raise ValidationError("Este RUT ya está registrado.")
        return username

    def clean_correo(self):
        correo = self.cleaned_data.get('correo')
        if Usuario.objects.filter(correo=correo).exists():
            raise ValidationError("Este correo electrónico ya está registrado.")
        return correo

    def clean_password2(self):
        password = self.cleaned_data.get("password")
        password2 = self.cleaned_data.get("password2")
        if password and password2 and password != password2:
            raise ValidationError("Las contraseñas no coinciden.")
        return password2

    def clean_cv_archivo(self):
        """ Valida que el archivo sea PDF y opcionalmente su tamaño. """
        archivo = self.cleaned_data.get('cv_archivo')
        if archivo:
            if not archivo.name.lower().endswith('.pdf'):
                raise ValidationError("Solo se permiten archivos PDF.")
            MAX_SIZE_MB = 5
            if archivo.size > MAX_SIZE_MB * 1024 * 1024:
                raise ValidationError("El archivo no puede superar los {}MB.".format(MAX_SIZE_MB))
        return archivo

    def clean(self):
        """ Validaciones cruzadas. """
        cleaned_data = super().clean()
        tipo_usuario = cleaned_data.get('tipo_usuario')

        if tipo_usuario == 'persona':
            if not cleaned_data.get('nombres'):
                self.add_error('nombres', 'Este campo es requerido para personas.') # Sin _()
            if not cleaned_data.get('apellidos'):
                self.add_error('apellidos', 'Este campo es requerido para personas.') # Sin _()
            # if not cleaned_data.get('cv_archivo'): # Descomenta si CV es obligatorio
            #     self.add_error('cv_archivo', 'El CV es requerido para personas.') # Sin _()

        elif tipo_usuario == 'empresa':
            if not cleaned_data.get('nombre_empresa'):
                self.add_error('nombre_empresa', 'Este campo es requerido para empresas.') # Sin _()

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




class OfertaTrabajoForm(forms.ModelForm):
    class Meta:
        model = OfertaTrabajo
        fields = [
            'categoria', 'nombre', 'descripcion', 'requisitos',
            'beneficios', 'salario', 'ubicacion', 'tipo_contrato',
            'fecha_cierre', 'esta_activa'
        ]
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 4, 'class': 'form-control'}),
            'requisitos': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'beneficios': forms.Textarea(attrs={'rows': 3, 'class': 'form-control'}),
            'fecha_cierre': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'tipo_contrato': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'esta_activa': _('Publicar inmediatamente'),
            'tipo_contrato': _('Tipo de Contrato'),
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
            self.fields.pop('tipo_contrato')  # Eliminar el campo si no es empresa
            
        # Configuración común
        self.fields['categoria'].queryset = Categoria.objects.filter(activa=True)
        self.fields['fecha_cierre'].widget.attrs['min'] = timezone.now().date().isoformat()


    def clean(self):
        cleaned_data = super().clean()
        
        # Validación específica para empresas
        if hasattr(self.user, 'empresa') and not cleaned_data.get('tipo_contrato'):
            self.add_error('tipo_contrato', _('Este campo es obligatorio para ofertas de empleo'))
        
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.creador = self.user
        
        # Auto-configuración según tipo de usuario
        if hasattr(self.user, 'empresa'):
            instance.empresa = self.user.empresa
            instance.es_servicio = False
        else:
            instance.es_servicio = True
        
        if commit:
            instance.save()
        
        return instance


class EditarPerfilPersonaForm(forms.Form):
    # Campos del Modelo Usuario (ejemplos)
    correo = forms.EmailField(
        label="Correo electrónico",
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control'})
    )
    telefono = forms.CharField(
        label="Teléfono",
        max_length=20,
        required=False, # O True si es obligatorio
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    direccion = forms.CharField(
        label="Dirección",
        max_length=255,
        required=False, # O True si es obligatorio
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )

    # Campos del Modelo PersonaNatural (ejemplos)
    nombres = forms.CharField(label="Nombres", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    apellidos = forms.CharField(label="Apellidos", max_length=100, required=True, widget=forms.TextInput(attrs={'class': 'form-control'}))
    fecha_nacimiento = forms.DateField(label="Fecha de Nacimiento", required=False, widget=forms.DateInput(format='%Y-%m-%d', attrs={'type': 'date', 'class': 'form-control'}))
    nacionalidad = forms.CharField(label="Nacionalidad", max_length=50, required=False, widget=forms.TextInput(attrs={'class': 'form-control'}))

    # --- Campo para actualizar CV ---
    cv_archivo = forms.FileField(
        label="Actualizar Currículum Vitae (PDF)",
        required=False, # IMPORTANTE: No es obligatorio subir uno nuevo cada vez que editan
        help_text="Sube un nuevo CV en formato PDF si deseas reemplazar el actual.",
        widget=forms.ClearableFileInput(attrs={'class':'form-control', 'accept': '.pdf'})
    )

    def clean_cv_archivo(self):
        # Reutiliza validaciones si es necesario (PDF, tamaño)
        archivo = self.cleaned_data.get('cv_archivo')
        if archivo:
            if not archivo.name.lower().endswith('.pdf'):
                raise forms.ValidationError("Solo se permiten archivos PDF.")
            MAX_SIZE_MB = 5
            if archivo.size > MAX_SIZE_MB * 1024 * 1024:
                raise forms.ValidationError(f"El archivo no puede superar los {MAX_SIZE_MB}MB.")
        return archivo

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
