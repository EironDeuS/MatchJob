from django import forms

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
