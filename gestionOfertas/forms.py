from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import Usuario



class LoginForm(forms.Form):
    rut = forms.CharField(
        label='RUT',
        max_length=12,
        widget=forms.TextInput(attrs={
            'placeholder': '12.345.678-9',
        })
    )
    password = forms.CharField(
        label='Contraseña',
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Contraseña',
        })
    )


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
