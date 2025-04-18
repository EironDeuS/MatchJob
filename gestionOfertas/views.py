from django.utils import timezone
from django.shortcuts import render
from .models import PersonaNatural, OfertaTrabajo, Categoria,OfertaTrabajo, Empresa
from django.db.models import Q  # Para búsquedas avanzadas
from .forms import LoginForm, registroForm, OfertaTrabajoForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect,get_object_or_404
from django.urls import reverse
from django.contrib import messages
from .models import PersonaNatural, Empresa
from django.contrib.auth.decorators import login_required
from django.contrib.auth import logout
from django.views.generic.detail import DetailView
from django.contrib.contenttypes.models import ContentType

def iniciar_sesion(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            rut = form.cleaned_data['username']  # Accede al campo como 'username'
            password = form.cleaned_data['password']

            user = authenticate(request, username=rut, password=password) # Usa 'username' como el nombre de usuario de autenticación

            if user is not None:
                login(request, user)
                messages.success(request, '¡Inicio de sesión exitoso!')
                return redirect('inicio')
            else:
                form.add_error(None, 'RUT o contraseña incorrectos.')
        else:
            form = LoginForm(request)
    else:
        form = LoginForm(request)

    return render(request, 'gestionOfertas/iniciar_sesion.html', {'form': form})

# Vista para la página de inicio
def inicio(request):
    # Obtener parámetros de filtrado del request
    busqueda = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    
    # Consulta base - todas las ofertas activas
    ofertas = OfertaTrabajo.objects.all()
    
    # Aplicar filtro de búsqueda si existe
    if busqueda:
        ofertas = ofertas.filter(
            Q(nombre__icontains=busqueda) | 
            Q(descripcion__icontains=busqueda)
        )
    
    # Aplicar filtro por categoría si existe
    if categoria_id:
        ofertas = ofertas.filter(categoria_id=categoria_id)
    
    context = {
        'ofertas': ofertas,
        'categorias': Categoria.objects.all(),
        'busqueda_actual': busqueda,
        'categoria_actual': categoria_id if categoria_id else ''
    }
    return render(request, 'gestionOfertas/inicio.html', context)

# Vista para la página Mis Datos
@login_required
def mi_perfil(request):
    usuario = request.user
    perfil = None
    ofertas = None
    
    # Obtener el perfil según tipo de usuario
    try:
        if usuario.tipo_usuario == 'empresa':
            perfil = usuario.empresa
            content_type = ContentType.objects.get_for_model(Empresa)
        else:
            perfil = usuario.personanatural
            content_type = ContentType.objects.get_for_model(PersonaNatural)
            
        # Obtener ofertas del creador
        ofertas = OfertaTrabajo.objects.filter(
            content_type=content_type,
            object_id=perfil.pk
        ).order_by('-fecha_publicacion')
        
    except (Empresa.DoesNotExist, PersonaNatural.DoesNotExist):
        pass

    context = {
        'usuario': usuario,
        'perfil': perfil,
        'ofertas': ofertas,
        'es_empresa': usuario.tipo_usuario == 'empresa'
    }
    
    return render(request, 'gestionOfertas/miperfil.html', context)

# Vista para la página Mis Datos
def base(request):
    return render(request, 'gestionOfertas/base.html')


# vista registro
def registro(request):
    if request.method == 'POST':
        form = registroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.nombres = form.cleaned_data.get('nombres')
            user.apellidos = form.cleaned_data.get('apellidos')
            user.direccion = form.cleaned_data.get('direccion')
            user.fecha_nacimiento = form.cleaned_data.get('fecha_nacimiento')
            user.nacionalidad = form.cleaned_data.get('nacionalidad')
            user.nombre_empresa = form.cleaned_data.get('nombre_empresa')
            user.rut_empresa = form.cleaned_data.get('rut_empresa')
            user.razon_social = form.cleaned_data.get('razon_social')
            user.giro = form.cleaned_data.get('giro')
            user.set_password(form.cleaned_data['password'])
            user.save()
            messages.success(request, 'Tu cuenta ha sido creada exitosamente.')
            return redirect(reverse('inicio'))
        else:
            print("Formulario no es válido:", form.errors)
            # Puedes agregar lógica para mostrar los errores al usuario en el template
            # Por ejemplo:
            # for field, errors in form.errors.items():
            #     for error in errors:
            #         messages.error(request, f"Error en {field}: {error}")
    else:
        form = registroForm()
    return render(request, 'gestionOfertas/registro.html', {'form': form})

def salir(request):
    logout(request)
    return redirect('inicio')

def detalle_oferta(request, oferta_id):
    oferta = get_object_or_404(OfertaTrabajo, pk=oferta_id)
    return render(request, 'gestionOfertas/detalle_oferta.html', {'oferta': oferta})

@login_required
def crear_oferta(request):
    if request.method == 'POST':
        form = OfertaTrabajoForm(request.POST)
        if form.is_valid():
            oferta = form.save(commit=False)
            oferta.fecha_publicacion = timezone.now().date()

            try:
                if request.user.tipo_usuario == 'empresa':
                    empresa = request.user.empresa
                    oferta.content_type = ContentType.objects.get_for_model(Empresa)
                    oferta.object_id = empresa.pk
                elif request.user.tipo_usuario == 'persona':
                    persona = request.user.personanatural
                    oferta.content_type = ContentType.objects.get_for_model(PersonaNatural)
                    oferta.object_id = persona.pk
                else:
                    raise ValueError("Tipo de usuario no soportado")

                oferta.save()
                messages.success(request, '¡Oferta publicada exitosamente!')
                return redirect('mi_perfil')

            except Exception as e:
                form.add_error(None, f'Error al asignar creador: {str(e)}')
                return render(request, 'gestionOfertas/crear_oferta.html', {'form': form})
    else:
        form = OfertaTrabajoForm(initial={
            'fecha_publicacion': timezone.now().date(),
            'activa': True
        })

    return render(request, 'gestionOfertas/crear_oferta.html', {'form': form})

