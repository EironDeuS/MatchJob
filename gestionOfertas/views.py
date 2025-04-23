# En tu_app/views.py

from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout # logout añadido por si acaso
from .forms import LoginForm, OfertaTrabajoForm, RegistroForm # Usar el nuevo RegistroForm
from .models import Usuario, PersonaNatural, Empresa, OfertaTrabajo, Categoria,Postulacion
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
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
def crear_oferta(request):
    if request.method == 'POST':
        form = OfertaTrabajoForm(request.POST, user=request.user)
        if form.is_valid():
            oferta = form.save(commit=False)
            oferta.creador = request.user
            
            # Si el usuario tiene perfil de empresa, asociamos la oferta a su empresa
            if hasattr(request.user, 'empresa'):
                oferta.empresa = request.user.empresa
                
            oferta.save()
            
            messages.success(request, _('¡Oferta creada exitosamente!'))
            return redirect('miperfil')
    else:
        # Pasamos el usuario al formulario como espera según su definición
        form = OfertaTrabajoForm(user=request.user)
    
    context = {
        'form': form,
        'es_empresa': hasattr(request.user, 'empresa')
    }
    return render(request, 'gestionOfertas/crear_oferta.html', context)

@login_required
def mi_perfil(request):
    usuario = request.user
    perfil = usuario.get_profile()
    
    context = {
        'usuario': usuario,
        'perfil': perfil,
        'valoracion_promedio': usuario.valoracion_promedio,
        'cantidad_valoraciones': usuario.cantidad_valoraciones
    }
    
    try:
        # Ofertas creadas (común para ambos tipos)
        if usuario.tipo_usuario == 'persona':
            ofertas_creadas = OfertaTrabajo.objects.filter(
                Q(creador=usuario) | Q(empresa__usuario=usuario)
            ).distinct().order_by('-fecha_publicacion')
            
            postulaciones = Postulacion.objects.filter(
                postulante=perfil
            ).select_related('oferta', 'oferta__empresa')
            context.update({
                'postulaciones': postulaciones,
                'tiene_postulaciones': postulaciones.exists()
            })
            
        elif usuario.tipo_usuario == 'empresa':
            ofertas_creadas = OfertaTrabajo.objects.filter(
                empresa=perfil
            ).order_by('-fecha_publicacion')
            
            postulaciones_recibidas = Postulacion.objects.filter(
                oferta__empresa=perfil
            ).select_related('postulante', 'oferta')
            context.update({
                'postulaciones_recibidas': postulaciones_recibidas,
                'tiene_postulaciones': postulaciones_recibidas.exists()
            })

        context.update({
            'ofertas_creadas': ofertas_creadas,
            'tiene_ofertas': ofertas_creadas.exists()
        })
            
        # Valoraciones recibidas
        context['valoraciones_recibidas'] = usuario.valoraciones_recibidas.select_related('autor').order_by('-fecha')[:3]
            
    except Exception as e:
        # Log del error para diagnóstico
        print(f"Error en mi_perfil: {str(e)}")
        # Puedes agregar un mensaje de error al contexto si lo deseas
    
    return render(request, 'gestionOfertas/miperfil.html', context)

def base(request):
    return render(request, 'gestionOfertas/base.html')

# Añadir vista de logout
def salir(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión.')
    return redirect('inicio')