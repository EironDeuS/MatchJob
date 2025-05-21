# En tu_app/views.py

from gestionOfertas.utils import notificar_oferta_urgente, validar_rut_empresa
from datetime import datetime, timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import json
import logging
from django.conf import settings
from django.forms import ValidationError
from django.utils.safestring import mark_safe

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout # logout añadido por si acaso
from .forms import LoginForm, OfertaTrabajoForm, RegistroForm, ValoracionForm, EditarPerfilPersonaForm,EditarOfertaTrabajoForm
from .models import Usuario, PersonaNatural, Empresa, OfertaTrabajo, Categoria,Postulacion, Valoracion, CV
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.db.models import Avg, Count, F, Window
from django.db.models.functions import Rank
from django.db.models import Q
import requests
from urllib.parse import quote
from django.core.mail import send_mail


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
#logica de verificacion rut empresa con api sii
            try:
                if tipo_usuario == 'empresa':
                    rut_empresa = form.cleaned_data['username']  # El RUT viene como 'username'
                    resultado = validar_rut_empresa(rut_empresa)
                if not resultado['valida']:
                    messages.error(request, f"❌ El RUT ingresado no es válido como empresa: {resultado.get('mensaje')}")
                    return render(request, 'gestionOfertas/registro.html', {'form': form})
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



def inicio(request):
    # Obtener parámetros de búsqueda y filtros
    busqueda = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    tipo_contrato = request.GET.get('tipo_contrato', '')
    ubicacion_id = request.GET.get('ubicacion', '')
    modalidad = request.GET.get('modalidad', '')
    salario_min = request.GET.get('salario_min', '')
    salario_max = request.GET.get('salario_max', '')
    experiencia = request.GET.get('experiencia', '')
    fecha_filtro = request.GET.get('fecha', '')
    
    # Iniciar con todas las ofertas activas
    ofertas = OfertaTrabajo.objects.filter(esta_activa=True)
    
    # Aplicar filtro de búsqueda por texto
    if busqueda:
        ofertas = ofertas.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(empresa__nombre_empresa__icontains=busqueda) |  # Asegúrate de ajustar estos campos según tu modelo
            Q(creador__personanatural__nombres__icontains=busqueda) |
            Q(creador__personanatural__apellidos__icontains=busqueda)
        ).distinct()
    
    # Aplicar filtro por categoría
    if categoria_id:
        ofertas = ofertas.filter(categoria_id=categoria_id)
    
    # Aplicar filtro por tipo de contrato
    if tipo_contrato:
        ofertas = ofertas.filter(tipo_contrato=tipo_contrato)
    
    # Aplicar filtro por ubicación
    if ubicacion_id:
        ofertas = ofertas.filter(ubicacion_id=ubicacion_id)
    
    # Aplicar filtro por modalidad de trabajo
    if modalidad:
        ofertas = ofertas.filter(modalidad=modalidad)
    
    # Aplicar filtros de salario
    if salario_min:
        ofertas = ofertas.filter(salario_min__gte=float(salario_min))
    if salario_max:
        ofertas = ofertas.filter(salario_max__lte=float(salario_max))
    
    # Aplicar filtro por experiencia mínima
    if experiencia:
        ofertas = ofertas.filter(experiencia_requerida__gte=int(experiencia))
    
    # Aplicar filtro por fecha de publicación
    if fecha_filtro:
        hoy = datetime.now().date()
        if fecha_filtro == 'hoy':
            ofertas = ofertas.filter(fecha_oferta__date=hoy)
        elif fecha_filtro == '3dias':
            tres_dias_atras = hoy - timedelta(days=3)
            ofertas = ofertas.filter(fecha_oferta__date__gte=tres_dias_atras)
        elif fecha_filtro == '7dias':
            semana_atras = hoy - timedelta(days=7)
            ofertas = ofertas.filter(fecha_oferta__date__gte=semana_atras)
        elif fecha_filtro == '30dias':
            mes_atras = hoy - timedelta(days=30)
            ofertas = ofertas.filter(fecha_oferta__date__gte=mes_atras)
    
    # Preparar contexto para la plantilla
    context = {
        'ofertas': ofertas.select_related('creador', 'categoria', 'empresa'),
        'categorias': Categoria.objects.filter(activa=True),  # Debes reemplazar esto con tu modelo de ubicaciones
        'busqueda_actual': busqueda,
        'categoria_actual': categoria_id,
        'tipo_contrato_actual': tipo_contrato,
        'modalidad_actual': modalidad,
        'salario_min_actual': salario_min,
        'salario_max_actual': salario_max,
        'experiencia_actual': experiencia,
        'fecha_actual': fecha_filtro
    }
    
    return render(request, 'gestionOfertas/Inicio.html', context)
  # Asegúrate de tener esta función en utils.py (o donde esté)

@login_required
def crear_oferta(request):
    if request.method == 'POST':
        form = OfertaTrabajoForm(request.POST, user=request.user)
        if form.is_valid():
            oferta = form.save()

            # 📢 Verifica si la oferta es urgente y envía la notificación
            if oferta.urgente:
                notificar_oferta_urgente(oferta)

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


@login_required
def mis_ofertas(request):
    usuario = request.user
    ofertas = OfertaTrabajo.objects.filter(creador=usuario).select_related('categoria', 'empresa')

    context = {
        'ofertas': ofertas
    }
    return render(request, 'gestionOfertas/mis_ofertas.html', context)
@login_required
def editar_oferta(request, oferta_id):
    oferta = get_object_or_404(OfertaTrabajo, id=oferta_id, creador=request.user)
    
    if request.method == 'POST':
        form = EditarOfertaTrabajoForm(request.POST, instance=oferta)
        if form.is_valid():
            form.save()
            messages.success(request, 'Oferta actualizada correctamente')
            return redirect('mis_ofertas')
    else:
        form = EditarOfertaTrabajoForm(instance=oferta)
    
    return render(request, 'gestionOfertas/editar_oferta.html', {
        'form': form,
        'oferta': oferta
    })

@login_required
def eliminar_oferta(request, oferta_id):
    oferta = get_object_or_404(OfertaTrabajo, id=oferta_id, creador=request.user)
    
    if request.method == 'POST':
        oferta.delete()
        messages.success(request, 'Oferta eliminada correctamente')
        return redirect('mis_ofertas')
    
    return render(request, 'gestionOfertas/confirmar_eliminar.html', {
        'oferta': oferta
    })


@login_required
def mi_perfil(request):
    usuario = request.user
    perfil = usuario.get_profile()

    # Ofertas creadas por este usuario (empresa o persona)
    ofertas_creadas = usuario.ofertas_creadas.order_by('-fecha_publicacion')

    # Todas las Postulaciones:
    if usuario.tipo_usuario == 'empresa':
        todas_las_postulaciones = Postulacion.objects.filter(
            oferta__creador=usuario
        ).select_related('persona', 'oferta')
    else:  # persona natural
        todas_las_postulaciones = Postulacion.objects.filter(
            persona=perfil
        ).select_related('oferta', 'oferta__creador')

    # Postulaciones Filtradas:
    postulaciones_filtradas = todas_las_postulaciones.filter(estado='filtrado').select_related('oferta')

    context = {
        'usuario': usuario,
        'perfil': perfil,
        'valoracion_promedio': usuario.valoracion_promedio,
        'cantidad_valoraciones': usuario.cantidad_valoraciones,
        'ofertas_creadas': ofertas_creadas,
        'tiene_ofertas': ofertas_creadas.exists(),
        'todas_las_postulaciones': todas_las_postulaciones,
        'tiene_todas_las_postulaciones': todas_las_postulaciones.exists(),
        'postulaciones_filtradas': postulaciones_filtradas,
        'tiene_postulaciones_filtradas': postulaciones_filtradas.exists(),
        'valoraciones_recibidas': usuario.valoraciones_recibidas
                                     .select_related('emisor')
                                     .order_by('-fecha_creacion')[:3],
    }

    return render(request, 'gestionOfertas/miperfil.html', context)

@login_required
def cambiar_estado_postulacion(request, postulacion_id):
    """
    Cambia el estado de una postulación específica.

    Args:
        request: La solicitud HTTP.
        postulacion_id: El ID de la postulación a cambiar.

    Returns:
        Una redirección a la página del perfil.
    """
    postulacion = get_object_or_404(
        Postulacion,
        id=postulacion_id,
        oferta__creador=request.user  # ¡SEGURIDAD!
    )

    if request.method == 'POST':
        nuevo_estado = request.POST.get('nuevo_estado')
        estados_validos = ['pendiente', 'filtrado', 'match', 'contratado', 'rechazado', 'finalizado']  # Ajusta esto a tus estados

        if nuevo_estado in estados_validos:
            postulacion.estado = nuevo_estado
            postulacion.save()
            messages.success(request, "Estado de la postulación actualizado.")
        else:
            messages.error(request, "Estado no válido.")

    return redirect('miperfil')  # Redirige al perfil (ajusta si es necesario)



@login_required
def actualizar_modo_urgente(request):
    if request.method == 'POST':
        persona = request.user.personanatural
        persona.modo_urgente = 'modo_urgente' in request.POST
        persona.recibir_ofertas_urgentes = 'recibir_ofertas_urgentes' in request.POST
        persona.save()
        messages.success(request, "Tus preferencias de urgencia han sido actualizadas.")
    return redirect('miperfil')  # Redirige al perfil (ajusta si es necesario)


# Configuración del logger
logger = logging.getLogger(__name__)

@login_required
def mapa(request):
    """
    Vista principal para mostrar el mapa con ofertas de trabajo
    """
    # Verificar que el token de Mapbox está configurado
    mapbox_token = getattr(settings, 'MAPBOX_TOKEN', '')
    if not mapbox_token:
        logger.error("MAPBOX_TOKEN no está configurado en settings")
        return render(request, 'gestionOfertas/mapa.html', {
            'error': 'Configuración del mapa no disponible',
            'ofertas': [],
            'titulo': 'Error en el mapa'
        })

    try:
        # Obtener ofertas activas con prefetch para optimizar
        ofertas_activas = OfertaTrabajo.objects.filter(
            esta_activa=True
        ).select_related('empresa').only(
            'id', 'nombre', 'ubicacion', 'empresa__nombre'
        )
        
        ofertas_con_coordenadas = []
        geocodificaciones_fallidas = 0
        
        for oferta in ofertas_activas:
            # Validar que la ubicación no esté vacía
            if not oferta.ubicacion or not oferta.ubicacion.strip():
                logger.warning(f"Oferta ID {oferta.id} no tiene ubicación definida")
                continue
                
            # Geocodificar la ubicación
            coords = geocode_direccion(oferta.ubicacion.strip(), mapbox_token)
            
            if coords and len(coords) == 2:
                ofertas_con_coordenadas.append({
                    'id': oferta.id,
                    'nombre': oferta.nombre,
                    'empresa': oferta.empresa.nombre if oferta.empresa else 'Empresa no especificada',
                    'ubicacion': oferta.ubicacion,
                    'coords': coords  # [longitud, latitud]
                })
            else:
                geocodificaciones_fallidas += 1
                logger.warning(f"No se pudo geocodificar: {oferta.ubicacion}")

        # Log de resultados
        logger.info(f"Ofertas procesadas: {len(ofertas_con_coordenadas)}. Fallos: {geocodificaciones_fallidas}")

        context = {
            'mapbox_token': mapbox_token,
            'ofertas': ofertas_con_coordenadas,
            'titulo': 'Mapa de Ofertas',
            'debug_info': {
                'total_ofertas': len(ofertas_activas),
                'ofertas_con_coords': len(ofertas_con_coordenadas),
                'geocodificaciones_fallidas': geocodificaciones_fallidas
            }
        }
        
        return render(request, 'gestionOfertas/mapa.html', context)

    except Exception as e:
        logger.error(f"Error en vista mapa: {str(e)}", exc_info=True)
        return render(request, 'gestionOfertas/mapa.html', {
            'error': 'Error al cargar el mapa. Por favor intente más tarde.',
            'ofertas': [],
            'titulo': 'Error en el mapa'
        })

def geocode_direccion(direccion, access_token):
    """Geocodifica una dirección usando Mapbox"""
    if not direccion or not access_token:
        logger.warning("Geocodificación: Dirección o token vacío")
        return None
        
    try:
        # Limpiar y preparar la dirección
        direccion_limpia = direccion.strip()
        if not direccion_limpia:
            return None
            
        # Codificar la dirección para URL
        direccion_codificada = quote(direccion_limpia)
        
        # Construir URL de la API
        url = f'https://api.mapbox.com/geocoding/v5/mapbox.places/{direccion_codificada}.json'
        
        # Parámetros de la solicitud
        params = {
            'access_token': access_token,
            'country': 'CL',  # Filtra por Chile
            'limit': 1,
            'language': 'es'  # Resultados en español
        }
        
        # Realizar la solicitud con timeout
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # Verificar resultados
        if data.get('features') and len(data['features']) > 0:
            coordenadas = data['features'][0]['center']
            
            # Validar que las coordenadas sean números válidos
            if (isinstance(coordenadas, list) and len(coordenadas) == 2 and
                all(isinstance(coord, (int, float)) for coord in coordenadas)):
                return coordenadas
            else:
                logger.error(f"Coordenadas inválidas recibidas para: {direccion_limpia}")
                return None
                
        return None
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error de conexión geocodificando {direccion_limpia}: {str(e)}")
        return None
    except ValueError as e:
        logger.error(f"Error parseando JSON para {direccion_limpia}: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado geocodificando {direccion_limpia}: {str(e)}")
        return None


@login_required
def buscar_direccion(request):
    """
    API View para buscar direcciones con la API de Mapbox (auto-complete).
    """
    if request.method == 'GET':
        try:
            query = request.GET.get('q', '')
            if not query:
                return JsonResponse({'error': 'Se requiere un término de búsqueda'}, status=400)

            mapbox_token = getattr(settings, 'MAPBOX_TOKEN', '')
            url = f'https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(query)}.json'
            params = {
                'access_token': mapbox_token,
                'limit': 5,
                'country': 'cl',
                'types': 'address,place'
            }

            response = requests.get(url, params=params, timeout=5)
            if response.status_code == 200:
                data = response.json()
                resultados = [
                    {
                        'nombre': feature.get('place_name', ''),
                        'lng': feature['center'][0],
                        'lat': feature['center'][1],
                    } for feature in data.get('features', [])
                ]
                return JsonResponse({'resultados': resultados})

            return JsonResponse({'error': 'Error en la búsqueda de direcciones'}, status=response.status_code)

        except Exception as e:
            logger.exception("Error en la búsqueda de direcciones")
            return JsonResponse({'error': 'Error al procesar la solicitud'}, status=500)

    return JsonResponse({'error': 'Método no permitido'}, status=405)



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


def demo_valoracion(request, postulacion_id):
    postulacion = get_object_or_404(Postulacion, id=postulacion_id)

    # --- Lógica de seguridad (importante) ---
    puede_valorar, receptor = postulacion.puede_valorar(request.user)
    if not puede_valorar:
        messages.error(request, "No tienes permiso para valorar esta postulación.")
        return redirect('miperfil')  # O a donde sea apropiado

    if request.method == 'POST':
        form = ValoracionForm(request.POST)
        if form.is_valid():
            valoracion = form.save(commit=False)
            valoracion.emisor = request.user
            valoracion.receptor = receptor  # Usar el receptor obtenido de puede_valorar
            valoracion.postulacion = postulacion
            valoracion.save()
            messages.success(request, "¡Valoración enviada con éxito!")
            return redirect('historial_valoraciones', usuario_id=request.user.id) # Redirige al historial
        else:
            messages.error(request, "Por favor, corrige los errores en el formulario.")
    else:
        form = ValoracionForm()

    context = {
        'form': form,
        'postulacion': postulacion,  # Pasar la postulación al template
    }
    return render(request, 'gestionOfertas/demo_valoracion.html', context)

#DETALLE DE LA OFERTA PUBLICADA
def detalle_oferta(request, oferta_id):
    oferta = get_object_or_404(OfertaTrabajo, id=oferta_id)
    return render(request, 'gestionOfertas/detalle_oferta.html', {'oferta': oferta})




@login_required
def realizar_postulacion(request, oferta_id):
    """
    Vista para que un usuario de tipo Persona Natural pueda postularse a una oferta de trabajo.
    
    Validaciones:
    - Usuario debe estar autenticado (garantizado por @login_required)
    - Usuario debe ser una Persona Natural
    - Usuario no puede postularse a su propia oferta
    - La oferta debe estar activa y no vencida
    - El usuario no debe haber postulado previamente a esta oferta
    """
    # Obtenemos la oferta o devolvemos 404 si no existe
    oferta = get_object_or_404(OfertaTrabajo, pk=oferta_id)
    
    # Verificamos que el usuario sea una Persona Natural
    try:
        persona = request.user.personanatural
    except PersonaNatural.DoesNotExist:
        messages.error(request, "Solo los usuarios de tipo Persona Natural pueden postular a ofertas.")
        return redirect('detalle_oferta', oferta_id=oferta_id)
    
    # Verificamos que el usuario no sea el creador de la oferta
    if oferta.creador == request.user:
        messages.error(request, "No puedes postularte a una oferta que tú mismo has creado.")
        return redirect('detalle_oferta', oferta_id=oferta_id)
    
    # Verificamos que la oferta esté activa y no vencida
    if not oferta.esta_activa:
        messages.error(request, "No es posible postular a una oferta inactiva.")
        return redirect('detalle_oferta', oferta_id=oferta_id)
    
    if oferta.fecha_cierre and oferta.fecha_cierre < timezone.now().date():
        messages.error(request, "No es posible postular a una oferta vencida.")
        return redirect('detalle_oferta', oferta_id=oferta_id)
    
    # Verificamos que el usuario no haya postulado previamente
    if Postulacion.objects.filter(persona=persona, oferta=oferta).exists():
        messages.warning(request, "Ya has postulado a esta oferta anteriormente.")
        return redirect('detalle_oferta', oferta_id=oferta_id)
    
    # Creamos la postulación
    try:
        postulacion = Postulacion(persona=persona, oferta=oferta)
        postulacion.save()
        
        # Obtenemos el nombre del creador según su tipo de usuario
        nombre_creador = oferta.creador.username
        
        if oferta.creador.tipo_usuario == 'persona':
            try:
                creador_persona = oferta.creador.personanatural
                nombre_creador = creador_persona.nombre_completo or oferta.creador.username
            except:
                pass
        elif oferta.creador.tipo_usuario == 'empresa':
            try:
                nombre_creador = oferta.creador.empresa.nombre
            except:
                pass
        
        # Preparamos el contexto para el template
        context = {
            'nombre_postulante': persona.nombre_completo or request.user.username,
            'oferta': oferta,
            'nombre_creador': nombre_creador,
            'url_perfil': request.build_absolute_uri('/perfil/'),  # Ajusta según tu URL
            'year': datetime.now().year,
            'company_name': getattr(settings, 'SITE_NAME', 'Portal de Empleos'),
            'logo_url': request.build_absolute_uri(settings.STATIC_URL + 'img/logo.png') if hasattr(settings, 'STATIC_URL') else None,
        }
        
        # Renderizamos el template HTML
        html_content = render_to_string('gestionOfertas/emails/confirmacion_postulacion.html', context)
        text_content = strip_tags(html_content)  # Versión de texto plano para clientes que no soportan HTML
        
        # Enviamos el correo con contenido HTML
        subject = f"Confirmación de postulación: {oferta.nombre}"
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com')
        to_email = request.user.correo
        
        # Creamos el mensaje con contenido alternativo (HTML y texto plano)
        msg = EmailMultiAlternatives(subject, text_content, from_email, [to_email])
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        messages.success(request, "¡Tu postulación ha sido enviada con éxito! Hemos enviado un correo de confirmación.")
        return redirect('detalle_oferta', oferta_id=oferta_id)
    
    except Exception as e:
        messages.error(request, f"Ha ocurrido un error al procesar tu postulación: {str(e)}")
        return redirect('detalle_oferta', oferta_id=oferta_id)


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
    usuario_perfil = get_object_or_404(Usuario, id=usuario_id)
    valoraciones_recibidas = Valoracion.objects.filter(
        receptor=usuario_perfil
    ).order_by('-fecha_creacion').select_related('emisor', 'postulacion')

    # Obtener postulaciones PENDIENTES de valoración (ajuste importante)
    postulaciones_pendientes = []
    if usuario_perfil.tipo_usuario == 'empresa':
        postulaciones = Postulacion.objects.filter(
            oferta__creador=usuario_perfil
        ).select_related('persona', 'oferta')
    elif usuario_perfil.tipo_usuario == 'persona':
        postulaciones = usuario_perfil.personanatural.postulaciones.all()
    else:
        postulaciones = []  # Manejar otros tipos de usuario si es necesario

    for postulacion in postulaciones:
        puede_valorar, _ = postulacion.puede_valorar(request.user)  # Usar request.user
        if puede_valorar:
            postulaciones_pendientes.append(postulacion)

    context = {
        'usuario_perfil': usuario_perfil,
        'valoraciones': valoraciones_recibidas,
        'postulaciones_pendientes': postulaciones_pendientes,
    }
    return render(request, 'gestionOfertas/historial_valoraciones.html', context)

def ranking_usuarios(request):
    tipo_usuario = request.GET.get('tipo', 'empresa')  # 'empresa' o 'persona'
    periodo = request.GET.get('periodo', 'semanal')  # 'semanal' o 'mensual'

    # --- Calcular el inicio del periodo ---
    if periodo == 'semanal':
        inicio_periodo = timezone.now() - timedelta(weeks=1)
    else:  # 'mensual'
        inicio_periodo = timezone.now() - timedelta(days=30)  # Aproximación a un mes

    # --- Filtrar valoraciones por periodo ---
    valoraciones_periodo = Valoracion.objects.filter(fecha_creacion__gte=inicio_periodo)

    # --- Anotar usuarios con su valoración promedio y cantidad (dentro del periodo) ---
    usuarios = Usuario.objects.filter(tipo_usuario=tipo_usuario).annotate(
        promedio_periodo=Avg('valoraciones_recibidas__puntuacion', filter=Q(valoraciones_recibidas__fecha_creacion__gte=inicio_periodo)),
        cantidad_periodo=Count('valoraciones_recibidas', filter=Q(valoraciones_recibidas__fecha_creacion__gte=inicio_periodo))
    ).filter(cantidad_periodo__gt=0).order_by('-promedio_periodo', '-cantidad_periodo') # Ordenar primero por promedio, luego por cantidad

    # --- Calcular el ranking usando Window function ---
    usuarios = usuarios.annotate(
        ranking=Window(
            expression=Rank(),
            order_by=(F('promedio_periodo').desc(nulls_last=True), F('cantidad_periodo').desc())
        )
    )

    # --- Preparar los datos para el template ---
    top_3 = list(usuarios[:3])
    resto = list(usuarios[3:10])

    context = {
        'tipo_usuario': tipo_usuario,
        'periodo': periodo,
        'top_3': top_3,
        'resto': resto,
    }

    return render(request, 'gestionOfertas/ranking.html', context)