from django.utils import timezone
from django.shortcuts import render
import logging

# Configure logger
logger = logging.getLogger(__name__)
from .models import PersonaNatural, OfertaTrabajo, Categoria,OfertaTrabajo, Empresa
from django.db.models import Q  # Para búsquedas avanzadas
from django.db import IntegrityError  # Para manejar errores de integridad
from .forms import LoginForm, registroForm, OfertaTrabajoForm
from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import redirect,get_object_or_404
from django.urls import reverse
from django.contrib import messages
from .models import PersonaNatural, Empresa
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
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
            try:
                # Guardamos el usuario base SIN commit todavía
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password'])
                # Guardamos el objeto Usuario base AHORA
                user.save() # Llama al save() SIMPLIFICADO del modelo

                # --- Crear el Perfil Específico EXPLÍCITAMENTE ---
                tipo_usuario = form.cleaned_data.get('tipo_usuario')

                if tipo_usuario == 'persona':
                    PersonaNatural.objects.create(
                        usuario=user,
                        rut=user.username,
                        nombres=form.cleaned_data.get('nombres'),
                        apellidos=form.cleaned_data.get('apellidos'),
                        fecha_nacimiento=form.cleaned_data.get('fecha_nacimiento'),
                        nacionalidad=form.cleaned_data.get('nacionalidad'),
                        direccion=form.cleaned_data.get('direccion'),
                        # Añade otros campos si los necesitas
                    )
                    logger.info(f"Perfil PersonaNatural creado para {user.username}")

                elif tipo_usuario == 'empresa':
                    Empresa.objects.create(
                        usuario=user,
                        rut_empresa=form.cleaned_data.get('rut_empresa'),
                        nombre_empresa=form.cleaned_data.get('nombre_empresa'),
                        razon_social=form.cleaned_data.get('razon_social'),
                        giro=form.cleaned_data.get('giro'), # Necesita tener valor si tipo es 'empresa'
                        # Añade otros campos si los necesitas
                    )
                    logger.info(f"Perfil Empresa creado para {user.username}")

                messages.success(request, 'Tu cuenta ha sido creada exitosamente.')
                return redirect(reverse('inicio'))

            except IntegrityError as ie:
                 logger.error(f"Error de Integridad de BD en registro para {form.cleaned_data.get('username')}: {ie}", exc_info=True)
                 if 'unique constraint' in str(ie).lower() and 'correo' in str(ie).lower():
                      messages.error(request, 'El correo electrónico ingresado ya está registrado.')
                 elif 'unique constraint' in str(ie).lower() and ('username' in str(ie).lower() or 'rut' in str(ie).lower()):
                       messages.error(request, 'El RUT ingresado ya está registrado.')
                 else:
                       messages.error(request, f'Error de base de datos durante el registro.')

            except Exception as e: # Otros errores inesperados
                logger.error(f"Error inesperado en registro para {form.cleaned_data.get('username')}: {e}", exc_info=True)
                messages.error(request, f'Ocurrió un error inesperado durante el registro. Por favor, inténtalo de nuevo.')

        else: # form.is_valid() es False
            print("Formulario no es válido:", form.errors.as_json(escape_html=True))
            messages.error(request, 'Por favor corrige los errores en el formulario.')

    else: # GET
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
        print(f"DEBUG: Form POST received. Is valid? {form.is_valid()}") # <-- DEBUG 1: Check validity

        if form.is_valid():
            try:
                oferta = form.save(commit=False)
                # oferta.fecha_publicacion = timezone.now().date() # <-- REMOVER ESTA LÍNEA (auto_now_add lo hace)

                user_tipo = getattr(request.user, 'tipo_usuario', None)
                print(f"DEBUG: User '{request.user.username}', tipo_usuario: '{user_tipo}'") # <-- DEBUG 2: Check user type

                if user_tipo == 'empresa':
                    print("DEBUG: Assigning creator as Empresa...") # <-- DEBUG 3a
                    try:
                        empresa = request.user.empresa # Puede fallar si no existe la relación
                        oferta.content_type = ContentType.objects.get_for_model(Empresa)
                        oferta.object_id = empresa.pk
                        print(f"DEBUG: Empresa PK {empresa.pk} assigned.") # <-- DEBUG 4a
                    except ObjectDoesNotExist:
                         logger.error(f"User {request.user.id} has tipo_usuario 'empresa' but no related Empresa object.", exc_info=True)
                         messages.error(request, "Error: Tu usuario es de tipo empresa pero no se encontró el perfil de empresa asociado.")
                         return render(request, 'gestionOfertas/crear_oferta.html', {'form': form})

                elif user_tipo == 'persona':
                    print("DEBUG: Assigning creator as PersonaNatural...") # <-- DEBUG 3b
                    try:
                        persona = request.user.personanatural # Puede fallar si no existe la relación
                        oferta.content_type = ContentType.objects.get_for_model(PersonaNatural)
                        oferta.object_id = persona.pk
                        print(f"DEBUG: PersonaNatural PK {persona.pk} assigned.") # <-- DEBUG 4b
                    except ObjectDoesNotExist:
                        logger.error(f"User {request.user.id} has tipo_usuario 'persona' but no related PersonaNatural object.", exc_info=True)
                        messages.error(request, "Error: Tu usuario es de tipo persona pero no se encontró el perfil de persona natural asociado.")
                        return render(request, 'gestionOfertas/crear_oferta.html', {'form': form})

                else:
                    print(f"DEBUG: Unsupported user type: {user_tipo}") # <-- DEBUG 3c
                    # Lanzar un error específico o manejarlo como prefieras
                    messages.error(request, f"Error: El tipo de usuario '{user_tipo}' no está permitido para crear ofertas.")
                    # No lanzar ValueError aquí, usar messages y render
                    return render(request, 'gestionOfertas/crear_oferta.html', {'form': form}) # Renderiza de nuevo el form

                print("DEBUG: Attempting oferta.save()...") # <-- DEBUG 5
                oferta.save() # Guardar en la BD
                print("DEBUG: oferta.save() successful!") # <-- DEBUG 6
                messages.success(request, '¡Oferta publicada exitosamente!')
                # Asegúrate que 'mi_perfil' es el nombre correcto de tu URL
                return redirect('miperfil') # Redirigir

            # Captura errores específicos primero si puedes
            except ObjectDoesNotExist as e: # Ya manejado arriba, pero por si acaso
                 logger.error(f"ObjectDoesNotExist during offer creation for user {request.user.id}: {e}", exc_info=True)
                 messages.error(request, f'Error al buscar el perfil asociado: {str(e)}')
                 return render(request, 'gestionOfertas/crear_oferta.html', {'form': form})
            except Exception as e:
                 # Captura cualquier otro error inesperado
                 logger.error(f"Unexpected error creating offer for user {request.user.id}: {e}", exc_info=True) # Log completo
                 print(f"ERROR during save/creator assignment: {type(e).__name__} - {e}") # <-- DEBUG 7: Print error type
                 # Usa messages.error para que sea visible con tu template actual
                 messages.error(request, f'Error inesperado al guardar la oferta: {str(e)}')
                 return render(request, 'gestionOfertas/crear_oferta.html', {'form': form})
        else:
             # Si el formulario NO es válido
             print("DEBUG: Form is invalid. Errors below:") # <-- DEBUG 8a
             print(form.errors.as_json()) # <-- DEBUG 8b: Ver errores exactos
             messages.error(request, 'El formulario contiene errores. Por favor, revísalos.')
             # La vista continuará y renderizará el form con errores
    else: # Método GET
        form = OfertaTrabajoForm(initial={
            # 'fecha_publicacion': timezone.now().date(), # <-- REMOVER ESTA LÍNEA
            'activa': True
        })

    # Render final para GET o si el form POST no fue válido o si hubo error manejado con render()
    return render(request, 'gestionOfertas/crear_oferta.html', {'form': form})
