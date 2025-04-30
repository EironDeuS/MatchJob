# En tu_app/views.py


from django.forms import ValidationError

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout # logout añadido por si acaso
from .forms import LoginForm, OfertaTrabajoForm, RegistroForm, ValoracionForm, EditarPerfilPersonaForm
from .models import Usuario, PersonaNatural, Empresa, OfertaTrabajo, Categoria,Postulacion, Valoracion, CV
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
    if request.user.is_authenticated:
        return redirect('inicio')

    if request.method == 'POST':
        # Asegúrate de pasar request.FILES aquí
        form = RegistroForm(request.POST, request.FILES)
        print(f"DEBUG: POST recibido. request.FILES: {request.FILES}") # <--- DEBUG: Verifica si llega el archivo

        if form.is_valid():
            print("DEBUG: Formulario VÁLIDO.") # <--- DEBUG
            user = None
            shareable_cv_url = None # Aunque ya no usamos esto para OneDrive directo

            archivo_cv_subido = form.cleaned_data.get('cv_archivo')
            print(f"DEBUG: form.cleaned_data['cv_archivo']: {archivo_cv_subido}") # <--- DEBUG: Verifica si el form lo limpió

            tipo_usuario = form.cleaned_data['tipo_usuario']   
            print(f"DEBUG: Tipo de usuario seleccionado: {tipo_usuario}") # <--- DEBUG

            try:
                # 1. Crear Usuario
                user = Usuario.objects.create_user(
                    username=form.cleaned_data['username'],
                    correo=form.cleaned_data['correo'],
                    password=form.cleaned_data['password'],
                    telefono=form.cleaned_data.get('telefono'),
                    direccion=form.cleaned_data.get('direccion'),
                    tipo_usuario=tipo_usuario
                )
                print(f"DEBUG: Usuario creado: {user.username}") # <--- DEBUG

                # 2. Poblar Perfil y Guardar CV
                if user.tipo_usuario == 'persona':
                    print("DEBUG: Procesando perfil Persona...") # <--- DEBUG
                    perfil = user.personanatural
                    perfil.nombres = form.cleaned_data.get('nombres')
                    perfil.apellidos = form.cleaned_data.get('apellidos')
                    perfil.fecha_nacimiento = form.cleaned_data.get('fecha_nacimiento')
                    perfil.nacionalidad = form.cleaned_data.get('nacionalidad', 'Chilena')
                    perfil.save()
                    print(f"DEBUG: Perfil Persona guardado para {user.username}") # <--- DEBUG

                    # Crear o obtener CV
                    cv_obj, created = CV.objects.get_or_create(persona=perfil)
                    print(f"DEBUG: CV object {'creado' if created else 'obtenido'}: {cv_obj.id}") # <--- DEBUG

                    if archivo_cv_subido:
                        print(f"DEBUG: INTENTANDO asignar archivo '{archivo_cv_subido.name}' a cv_obj.archivo_cv...") # <--- DEBUG
                        cv_obj.archivo_cv = archivo_cv_subido
                        print("DEBUG: Asignación hecha. Llamando a cv_obj.save()...") # <--- DEBUG
                        try:
                            # Añadir logging detallado para diagnóstico de almacenamiento
                            from django.core.files.storage import default_storage
                            import traceback
                            print(f"DEBUG: Intentando guardar archivo con storage: {default_storage}")
                            print(f"DEBUG: Tipo de storage: {type(default_storage)}")
                            print(f"DEBUG: Configuración de storage: {default_storage.__dict__}")
                        except Exception as storage_log_error:
                            print(f"DEBUG: Error al loguear detalles de storage: {storage_log_error}")
                        cv_obj.save() # Aquí ocurre la subida a GCS
                        print("DEBUG: cv_obj.save() ejecutado.") # <--- DEBUG
                        # Verificar si el campo tiene valor DESPUÉS de guardar
                        if cv_obj.archivo_cv and hasattr(cv_obj.archivo_cv, 'name'):
                             print(f"DEBUG: Valor de cv_obj.archivo_cv.name DESPUÉS de guardar: {cv_obj.archivo_cv.name}") # <--- DEBUG
                        else:
                             print("DEBUG: cv_obj.archivo_cv está vacío DESPUÉS de guardar.") # <--- DEBUG
                        
                        try:
                            # Verificación adicional de almacenamiento
                            if cv_obj.archivo_cv:
                                file_exists = default_storage.exists(cv_obj.archivo_cv.name)
                                file_size = default_storage.size(cv_obj.archivo_cv.name) if file_exists else 0
                                print(f"DEBUG: Archivo guardado. Existe: {file_exists}, Tamaño: {file_size} bytes")
                                
                                # Intentar obtener URL (si es posible)
                                try:
                                    file_url = cv_obj.archivo_cv.url
                                    print(f"DEBUG: URL del archivo: {file_url}")
                                except Exception as url_error:
                                    print(f"DEBUG: No se pudo obtener URL: {url_error}")
                        except Exception as file_check_error:
                            print(f"DEBUG: Error al verificar archivo: {file_check_error}")
                    else:
                        print("DEBUG: No se proporcionó archivo CV en el formulario.") # <--- DEBUG

                elif user.tipo_usuario == 'empresa':
                    print("DEBUG: Procesando perfil Empresa...") # <--- DEBUG
                    perfil = user.empresa
                    perfil.nombre_empresa = form.cleaned_data.get('nombre_empresa')
                    perfil.razon_social = form.cleaned_data.get('razon_social')
                    perfil.giro = form.cleaned_data.get('giro')
                    perfil.save()
                    print(f"DEBUG: Perfil Empresa guardado para {user.username}") # <--- DEBUG

                messages.success(request, 'Tu cuenta ha sido creada exitosamente.')
                # Intenta loguear al usuario si tienes el backend configurado
                # login(request, user, backend='gestionOfertas.backends.AutenticacionPorRUTBackend')
                print("DEBUG: Redirigiendo a inicio...") # <--- DEBUG
                return redirect(reverse('inicio'))

            except Exception as e:
                # Imprimir cualquier excepción que ocurra
                import traceback
                print("DEBUG: !!! EXCEPCIÓN OCURRIDA !!!") # <--- DEBUG
                print(f"DEBUG: Tipo de Excepción: {type(e).__name__}")
                print(f"DEBUG: Mensaje: {e}")
                print("DEBUG: Traceback:")
                traceback.print_exc() # Imprime el traceback completo en la consola
                print("DEBUG: !!! FIN EXCEPCIÓN !!!")
                messages.error(request, f'Hubo un error inesperado al guardar los datos.') # Mensaje genérico al usuario
                if user and user.pk: user.delete() # Intenta borrar usuario si falló

        else: # Formulario no válido
            print("DEBUG: Formulario NO VÁLIDO.") # <--- DEBUG
            print(f"DEBUG: Errores del formulario: {form.errors.as_json()}") # <--- DEBUG: Muestra errores específicos
            messages.error(request, 'Por favor corrige los errores en el formulario.')
    else: # Método GET
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
            oferta = form.save()
            
            msg = _('¡Oferta de empleo creada!') if hasattr(request.user, 'empresa') else _('¡Servicio publicado!')
            messages.success(request, msg)
            
            return redirect('miperfil')
    else:
        form = OfertaTrabajoForm(user=request.user)
    
    contexto = {
        'form': form,
        'es_empresa': hasattr(request.user, 'empresa'),
        'es_persona': hasattr(request.user, 'personanatural')
    }
    
    return render(request, 'gestionOfertas/crear_oferta.html', contexto)

 # ajusta el import según tu app

@login_required
def mi_perfil(request):
    usuario = request.user
    perfil = usuario.get_profile()

    # Ofertas creadas por este usuario (empresa o persona)
    ofertas_creadas = usuario.ofertas_creadas.order_by('-fecha_publicacion')

    # Postulaciones:
    if usuario.tipo_usuario == 'empresa':
        postulaciones = Postulacion.objects.filter(
            oferta__creador=usuario
        ).select_related('persona', 'oferta')  # Cambiado de 'postulante' a 'persona' para coincidir con tu modelo
    else:  # persona natural
        postulaciones = Postulacion.objects.filter(
            persona=perfil  # Cambiado de 'postulante' a 'persona'
        ).select_related('oferta', 'oferta__creador')

    context = {
        'usuario': usuario,
        'perfil': perfil,
        'valoracion_promedio': usuario.valoracion_promedio,
        'cantidad_valoraciones': usuario.cantidad_valoraciones,
        'ofertas_creadas': ofertas_creadas,
        'tiene_ofertas': ofertas_creadas.exists(),
        'postulaciones': postulaciones,
        'tiene_postulaciones': postulaciones.exists(),
        'valoraciones_recibidas': usuario.valoraciones_recibidas
                                     .select_related('emisor')  # Cambiado de 'autor' a 'emisor'
                                     .order_by('-fecha_creacion')[:3],  # Cambiado de 'fecha' a 'fecha_creacion'
    }

    return render(request, 'gestionOfertas/miperfil.html', context)

@login_required # Asegura que solo usuarios logueados accedan
def editar_perfil(request):
    # Asumimos que solo las personas naturales pueden editar este perfil específico
    # Puedes añadir lógica para redirigir a empresas a otro form/view
    if request.user.tipo_usuario != 'persona':
        messages.error(request, "Esta sección es solo para personas naturales.")
        return redirect('inicio') # O a donde corresponda

    # Obtener perfil PersonaNatural asociado al usuario logueado
    # Usamos get_object_or_404 para manejar el caso raro de que no exista
    perfil = get_object_or_404(PersonaNatural, usuario=request.user)
    # Obtener o crear el objeto CV asociado (por si nunca subió uno)
    cv_obj, created = CV.objects.get_or_create(persona=perfil)

    if request.method == 'POST':
        # Pasar instance=perfil podría funcionar si usaras ModelForm,
        # pero con forms.Form, procesamos manualmente. Pasamos request.FILES.
        form = EditarPerfilPersonaForm(request.POST, request.FILES)
        if form.is_valid():
            # Actualizar datos del Usuario
            request.user.correo = form.cleaned_data['correo']
            request.user.telefono = form.cleaned_data.get('telefono')
            request.user.direccion = form.cleaned_data.get('direccion')
            request.user.save()

            # Actualizar datos del Perfil PersonaNatural
            perfil.nombres = form.cleaned_data['nombres']
            perfil.apellidos = form.cleaned_data['apellidos']
            perfil.fecha_nacimiento = form.cleaned_data.get('fecha_nacimiento')
            perfil.nacionalidad = form.cleaned_data.get('nacionalidad')
            perfil.save()

            # --- Procesar actualización de CV ---
            nuevo_cv_archivo = form.cleaned_data.get('cv_archivo')
            if nuevo_cv_archivo:
                # 1. Borrar el archivo antiguo de GCS (si existe)
                if cv_obj.archivo_cv:
                    try:
                        # save=False evita guardar el modelo solo por borrar el archivo
                        cv_obj.archivo_cv.delete(save=False)
                        print(f"DEBUG: Archivo CV antiguo borrado de GCS: {cv_obj.archivo_cv.name}")
                    except Exception as e:
                         print(f"DEBUG: Error al intentar borrar CV antiguo: {e}")
                         messages.warning(request, "No se pudo borrar el CV anterior del almacenamiento, pero se intentará subir el nuevo.")


                # 2. Asignar el nuevo archivo al campo
                cv_obj.archivo_cv = nuevo_cv_archivo

                # 3. Guardar el objeto CV (esto subirá el nuevo archivo a GCS y usará tu función de renombrar)
                try:
                    cv_obj.save()
                    print(f"DEBUG: Nuevo CV guardado: {cv_obj.archivo_cv.name}")
                    messages.success(request, 'Tu CV ha sido actualizado exitosamente.')
                except Exception as e:
                    print(f"DEBUG: Error al guardar/subir nuevo CV: {e}")
                    messages.error(request, f'Hubo un error al guardar el nuevo CV: {e}')
            # ------------------------------------
            elif 'cv_archivo-clear' in request.POST:
                 # Si el usuario marcó el checkbox "clear" del ClearableFileInput
                 if cv_obj.archivo_cv:
                    try:
                        cv_obj.archivo_cv.delete(save=True) # save=True aquí para guardar el campo vacío
                        print("DEBUG: CV existente eliminado por petición del usuario.")
                        messages.info(request, 'Tu CV ha sido eliminado.')
                    except Exception as e:
                        print(f"DEBUG: Error al eliminar CV existente: {e}")
                        messages.error(request, f'Hubo un error al eliminar el CV: {e}')


            if not nuevo_cv_archivo and 'cv_archivo-clear' not in request.POST :
                 messages.success(request, 'Tu perfil ha sido actualizado exitosamente.')

            return redirect('editar_perfil') # Redirige a la misma página para ver cambios

        else: # Formulario no válido
             print(f"DEBUG: Errores del formulario Editar Perfil: {form.errors.as_json()}")
             messages.error(request, 'Por favor corrige los errores en el formulario.')

    else: # Método GET <--- AQUÍ DENTRO
        initial_data = {
            'correo': request.user.correo,
            'telefono': request.user.telefono,
            'direccion': request.user.direccion,
            'nombres': perfil.nombres,
            'apellidos': perfil.apellidos,
            'fecha_nacimiento': perfil.fecha_nacimiento,
            'nacionalidad': perfil.nacionalidad,
        }
        form = EditarPerfilPersonaForm(initial=initial_data)

        context = {
            'form': form,
            'cv_actual': cv_obj.archivo_cv
        }
        return render(request, 'gestionOfertas/editar_perfil.html', context)

def base(request):
    return render(request, 'gestionOfertas/base.html')

# Añadir vista de logout
def salir(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión.')
    return redirect('inicio')


def demo_valoracion(request):
    form = ValoracionForm()
    return render(request, 'gestionOfertas/demo_valoracion.html', {'form': form})


@login_required
def valorar_postulacion(request, postulacion_id):
    postulacion = get_object_or_404(Postulacion, id=postulacion_id)
    puede_valorar, receptor = postulacion.puede_valorar(request.user)

    if not puede_valorar:
        messages.error(request, "No puedes valorar esta postulación.")
        return redirect('registro')  # o a donde tú quieras redirigir

    if request.method == 'POST':
        form = ValoracionForm(request.POST)
        if form.is_valid():
            valoracion = form.save(commit=False)
            valoracion.emisor = request.user
            valoracion.receptor = receptor
            valoracion.postulacion = postulacion
            valoracion.save()
            messages.success(request, "¡Valoración enviada con éxito!")
            return redirect('registro')  # redirección final tras enviar
    else:
        form = ValoracionForm()

    # 👇 ESTA línea es la que estaba mal
    return render(request, 'gestionOfertas/demo_valoracion.html', {'form': form})

def historial_valoraciones(request, usuario_id):
    usuario_perfil = get_object_or_404(Usuario, id=usuario_id)  # Usa tu modelo Usuario
    valoraciones_recibidas = Valoracion.objects.filter(receptor=usuario_perfil).order_by('-fecha_creacion').select_related('emisor', 'postulacion')

    context = {
        'usuario_perfil': usuario_perfil,
        'valoraciones': valoraciones_recibidas,
    }
    return render(request, 'gestionOfertas/historial_valoraciones.html', context)