from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .forms import UsuarioCreationForm, UsuarioChangeForm
from .models import Usuario, PersonaNatural, OfertaTrabajo, Categoria, Postulacion, Empresa, Valoracion

# Desregistrar Usuario si ya fue registrado
try:
    admin.site.unregister(Usuario)
except admin.sites.NotRegistered:
    pass

# Clase personalizada para el modelo Usuario
class UsuarioAdmin(BaseUserAdmin):
    form = UsuarioChangeForm
    add_form = UsuarioCreationForm

    list_display = ('username', 'correo', 'is_staff', 'tipo_usuario')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'tipo_usuario')

    fieldsets = (
        (None, {'fields': ('username', 'correo', 'password')}),
        ('Información personal', {'fields': ('telefono', 'tipo_usuario')}),
        ('Permisos', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'correo', 'telefono', 'tipo_usuario', 'password1', 'password2'),
        }),
    )

    search_fields = ('username', 'correo')
    ordering = ('username',)
    filter_horizontal = ('groups', 'user_permissions',)

# Registrar Usuario con la clase admin personalizada
admin.site.register(Usuario, UsuarioAdmin)

# Registrar los otros modelos
admin.site.register(PersonaNatural)
admin.site.register(OfertaTrabajo)
admin.site.register(Categoria)
admin.site.register(Postulacion)
admin.site.register(Empresa)
admin.site.register(Valoracion)

