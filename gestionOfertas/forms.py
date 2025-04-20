from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Usuario, PersonaNatural, Empresa,OfertaTrabajo
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import AuthenticationForm

class LoginForm(AuthenticationForm):
    username = forms.CharField(  # OJO: Mantenemos 'username'
        label='RUT',
        max_length=12,
        widget=forms.TextInput(attrs={'placeholder': '12.345.678-9', 'class': 'form-control'})
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={'placeholder': 'Contraseña', 'class': 'form-control'})
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'RUT'  #  Mejorar la etiqueta

class UsuarioCreationForm(forms.ModelForm):
    """Formulario para crear nuevos usuarios (usa set_password)."""
    password1 = forms.CharField(label='Contraseña', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Confirmar contraseña', widget=forms.PasswordInput)

    class Meta:
        model = Usuario
        fields = ('username', 'correo', 'telefono', 'tipo_usuario')

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden")
        return password2

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])  # 🔒 Aquí se hashea
        if commit:
            user.save()
        return user


class UsuarioChangeForm(forms.ModelForm):
    """Formulario para actualizar usuarios (readonly para contraseña)."""
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = Usuario
        fields = ('username', 'correo', 'telefono', 'tipo_usuario', 'password', 'is_active', 'is_staff', 'is_superuser')

    def clean_password(self):
        return self.initial["password"]

# formulario registro
class registroForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Contraseña")
    nombres = forms.CharField(max_length=100, required=False, label="Nombres")
    apellidos = forms.CharField(max_length=100, required=False, label="Apellidos")
    fecha_nacimiento = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}), label="Fecha de Nacimiento")
    nacionalidad = forms.CharField(max_length=50, initial='Chilena', required=False, label="Nacionalidad")
    nombre_empresa = forms.CharField(max_length=100, required=False, label="Nombre de la Empresa")
    rut_empresa = forms.CharField(max_length=12, required=False, widget=forms.TextInput(attrs={'placeholder': 'RUT de la empresa'}), label="RUT de la Empresa")
    razon_social = forms.CharField(max_length=100, required=False, label="Razón Social")
    giro = forms.CharField(max_length=100, required=False, label="Giro Comercial")
    direccion = forms.CharField(max_length=255, required=False, label="Dirección")

    class Meta:
        model = Usuario
        fields = ['username', 'correo', 'telefono', 'tipo_usuario']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'RUT (12345678-9)'}),
            'correo': forms.EmailInput(attrs={'placeholder': 'Correo electrónico'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Teléfono (opcional)'}),
            'tipo_usuario': forms.Select(attrs={'onchange': 'toggleUsuarioFields()'}),
        }
        labels = {
            'username': 'RUT',
            'correo': 'Correo electrónico',
            'telefono': 'Teléfono de Contacto',
            'tipo_usuario': 'Tipo de Usuario',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if hasattr(Usuario, 'TIPO_USUARIO_CHOICES'):
             self.fields['tipo_usuario'].choices = Usuario.TIPO_USUARIO_CHOICES
        else:
             print("Advertencia: Usuario.TIPO_USUARIO_CHOICES no encontrado.")
             self.fields['tipo_usuario'].choices = []

    def clean(self):
        cleaned_data = super().clean()
        tipo_usuario = cleaned_data.get('tipo_usuario')

        if not tipo_usuario:
             self.add_error('tipo_usuario', ValidationError("Debes seleccionar un tipo de usuario.", code='required'))
             return cleaned_data

        if tipo_usuario == 'persona':
            required_persona_fields = {
                'nombres': 'Nombres',
                'apellidos': 'Apellidos',
            }
            for field_name, field_label in required_persona_fields.items():
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, ValidationError(f"El campo '{field_label}' es requerido para personas.", code='required'))

            cleaned_data['nombre_empresa'] = None
            cleaned_data['rut_empresa'] = None
            cleaned_data['razon_social'] = None
            cleaned_data['giro'] = None

        elif tipo_usuario == 'empresa':
            required_empresa_fields = {
                'nombre_empresa': 'Nombre de la Empresa',
                'rut_empresa': 'RUT de la Empresa',
            }
            for field_name, field_label in required_empresa_fields.items():
                if not cleaned_data.get(field_name):
                    self.add_error(field_name, ValidationError(f"El campo '{field_label}' es requerido para empresas.", code='required'))

            cleaned_data['nombres'] = None
            cleaned_data['apellidos'] = None
            cleaned_data['fecha_nacimiento'] = None
            cleaned_data['nacionalidad'] = None

        return cleaned_data


class OfertaTrabajoForm(forms.ModelForm):
    class Meta:
        model = OfertaTrabajo
        fields = [
            'categoria', 'nombre', 'descripcion', 'requisitos', 'beneficios',
            'salario', 'ubicacion', 'tipo_contrato', 'fecha_cierre', 'activa'
        ]  # ¡Omitimos 'empresa' aquí!
        widgets = {
            'descripcion': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'requisitos': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'beneficios': forms.Textarea(attrs={'rows': 5, 'class': 'form-control'}),
            'fecha_cierre': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            if not field.widget.attrs.get('class'):
                field.widget.attrs['class'] = 'form-control'


