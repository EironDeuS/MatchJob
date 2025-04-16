from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Usuario, PersonaNatural, Empresa
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
    """
    Formulario de creación de usuario con campos dinámicos según el tipo de usuario.
    """
    password = forms.CharField(widget=forms.PasswordInput, required=True, label="Contraseña")
    nombres = forms.CharField(max_length=100, required=True)  # Cambiado a required=True
    apellidos = forms.CharField(max_length=100, required=True)  # Y apellidos también
    fecha_nacimiento = forms.DateField(required=False, widget=forms.DateInput(attrs={'type': 'date'}))
    nacionalidad = forms.CharField(max_length=50, initial='Chilena', required=False)
    nombre_empresa = forms.CharField(max_length=100, required=False)
    rut_empresa = forms.CharField(max_length=12, required=False, widget=forms.TextInput(attrs={'placeholder': 'RUT de la empresa'}))
    razon_social = forms.CharField(max_length=100, required=False)
    giro = forms.CharField(max_length=100, required=False)

    class Meta:
        model = Usuario
        fields = ['username', 'correo', 'telefono', 'tipo_usuario',
                  'nombres', 'apellidos', 'fecha_nacimiento', 'nacionalidad',
                  'nombre_empresa', 'rut_empresa', 'razon_social', 'giro']
        widgets = {
            'username': forms.TextInput(attrs={'placeholder': 'RUT (12345678-9)'}),
            'correo': forms.EmailInput(attrs={'placeholder': 'Correo electrónico'}),
            'telefono': forms.TextInput(attrs={'placeholder': 'Teléfono (opcional)'}),
            'tipo_usuario': forms.Select(attrs={'onchange': 'toggleUsuarioFields()'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_usuario'].choices = Usuario.TIPO_USUARIO_CHOICES

        # No es necesario agregar/remover campos aquí para la visualización inicial.
        # La lógica de mostrar/ocultar se manejará con JavaScript.

    def save(self, commit=True):
        """
        Sobrescribe el método save() para guardar solo el Usuario.
        La creación de PersonaNatural o Empresa se maneja en el modelo Usuario.
        """
        user = super().save(commit=commit)
        return user