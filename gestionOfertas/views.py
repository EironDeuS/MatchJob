# En tu_app/views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout # logout añadido por si acaso
from .forms import LoginForm, RegistroForm # Usar el nuevo RegistroForm
from .models import Usuario, PersonaNatural, Empresa, OfertaTrabajo, Categoria # Importar modelos necesarios
from django.contrib.auth.decorators import login_required
from django.db.models import Q

# --- Vista iniciar_sesion (Sin cambios, parece correcta) ---
def iniciar_sesion(request):
    if request.user.is_authenticated: # Redirigir si ya está logueado
        return redirect('inicio')
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            rut = form.cleaned_data['username']
            password = form.cleaned_data['password']
            # Usar el backend de autenticación configurado (RutAuthBackend)
            user = authenticate(request, username=rut, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, '¡Inicio de sesión exitoso!')
                # Redirigir a donde corresponda (ej: inicio o perfil)
                return redirect('inicio')
            else:
                messages.error(request, 'RUT o contraseña incorrectos.') # Mensaje más claro
        else:
             messages.error(request, 'Por favor corrige los errores en el formulario.')
    else:
        form = LoginForm()
    return render(request, 'gestionOfertas/iniciar_sesion.html', {'form': form})

# --- Vista de Registro Actualizada ---
def registro(request):
    if request.user.is_authenticated: # Redirigir si ya está logueado
        return redirect('inicio')
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            # 1. Crear el Usuario con sus datos
            user = Usuario.objects.create_user(
                username=form.cleaned_data['username'],
                correo=form.cleaned_data['correo'],
                password=form.cleaned_data['password'], # create_user hashea la contraseña
                telefono=form.cleaned_data.get('telefono'),
                direccion=form.cleaned_data.get('direccion'),
                tipo_usuario=form.cleaned_data['tipo_usuario']
            )
            # user.save() # create_user ya guarda el usuario

            # 2. Poblar el perfil correspondiente (ya creado vacío por Usuario.save())
            try:
                if user.tipo_usuario == 'persona':
                    perfil = user.personanatural # Acceder via related_name
                    perfil.nombres = form.cleaned_data.get('nombres')
                    perfil.apellidos = form.cleaned_data.get('apellidos')
                    perfil.fecha_nacimiento = form.cleaned_data.get('fecha_nacimiento')
                    perfil.nacionalidad = form.cleaned_data.get('nacionalidad', 'Chilena')
                    # El RUT ya no se guarda aquí
                    perfil.save()
                elif user.tipo_usuario == 'empresa':
                    perfil = user.empresa # Acceder via related_name
                    perfil.nombre_empresa = form.cleaned_data.get('nombre_empresa')
                    perfil.razon_social = form.cleaned_data.get('razon_social')
                    perfil.giro = form.cleaned_data.get('giro')
                    # El RUT Empresa ya no se guarda aquí
                    # Guardar otros campos si se añadieron al form (pagina_web, etc.)
                    # perfil.pagina_web = form.cleaned_data.get('pagina_web')
                    perfil.save()

                messages.success(request, 'Tu cuenta ha sido creada exitosamente.')
                # Opcional: Loguear al usuario después del registro
                login(request, user, backend='tu_app_nombre.backends.RutAuthBackend') # Especificar backend
                return redirect(reverse('inicio')) # O redirigir al perfil

            except Exception as e:
                # Manejar error si el perfil no se pudo actualizar (poco probable si se creó bien)
                user.delete() # Borrar usuario si el perfil falló
                messages.error(request, f'Hubo un error al crear el perfil: {e}')

        else:
            # Mostrar errores de validación del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
            print("Formulario no válido:", form.errors) # Para debug en consola
    else:
        form = RegistroForm()
    return render(request, 'gestionOfertas/registro.html', {'form': form})


# --- Otras vistas (inicio, mi_perfil, base - Sin cambios necesarios para el registro) ---
def inicio(request):
    busqueda = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    ofertas = OfertaTrabajo.objects.filter(esta_activa=True) # Filtrar activas
    if busqueda:
        ofertas = ofertas.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(creador__empresa__nombre_empresa__icontains=busqueda) | # Buscar por nombre empresa
            Q(creador__personanatural__nombres__icontains=busqueda) | # Buscar por nombre persona
            Q(creador__personanatural__apellidos__icontains=busqueda)
        ).distinct()
    if categoria_id:
        ofertas = ofertas.filter(categoria_id=categoria_id)
    context = {
        'ofertas': ofertas.select_related('creador', 'categoria'), # Optimizar consulta
        'categorias': Categoria.objects.filter(activa=True), # Solo activas
        'busqueda_actual': busqueda,
        'categoria_actual': categoria_id if categoria_id else ''
    }
    return render(request, 'gestionOfertas/inicio.html', context)

@login_required
def mi_perfil(request):
    usuario = request.user
    # Usar el método get_profile() del modelo Usuario
    perfil = usuario.get_profile()
    context = {
        'usuario': usuario, # Pasar el objeto usuario completo
        'perfil': perfil   # Pasar el perfil específico (PersonaNatural o Empresa)
    }
    # Decidir qué template usar o cómo mostrar los datos basado en usuario.tipo_usuario
    # if usuario.tipo_usuario == 'persona':
    #     template_name = 'gestionOfertas/miperfil_persona.html'
    # elif usuario.tipo_usuario == 'empresa':
    #     template_name = 'gestionOfertas/miperfil_empresa.html'
    # else:
    #     template_name = 'gestionOfertas/miperfil_base.html' # O manejar admin
    # return render(request, template_name, context)
    return render(request, 'gestionOfertas/miperfil.html', context) # Usar un solo template por ahora

def base(request):
    return render(request, 'gestionOfertas/base.html')

# Añadir vista de logout
def cerrar_sesion(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión.')
    return redirect('inicio')