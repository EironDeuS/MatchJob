# En tu_app/views.py

from gestionOfertas.utils import notificar_oferta_urgente, validar_rut_empresa
from django.contrib.auth.views import PasswordResetView
from django.contrib.auth import get_user_model
from django.urls import reverse_lazy
from gestionOfertas.forms import CustomPasswordResetForm
from django.views.generic import ListView
from django.views.decorators.http import require_POST
from datetime import datetime, timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils.functional import cached_property
import json
import logging
logger = logging.getLogger(__name__)
from django.conf import settings
from django.forms import ValidationError
from django.utils.safestring import mark_safe

from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.models import User
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout # logout añadido por si acaso
from .forms import LoginForm, OfertaTrabajoForm, RegistroForm, ValoracionForm, EditarOfertaTrabajoForm, UsuarioPerfilForm, PersonaNaturalPerfilForm
from .models import Usuario, PersonaNatural, Empresa, OfertaTrabajo, Categoria,Postulacion, Valoracion, CV, MuestraTrabajo  
from django.contrib.auth.decorators import login_required
from django.utils.translation import gettext_lazy as _
import os
from django.utils import timezone
import uuid  # Import the uuid module for generating unique identifiers
from django.db.models import Avg, Count, F, Window
from django.db.models.functions import Rank
from django.db.models import Q
import requests
from urllib.parse import quote
from django.core.mail import send_mail
from django.core.files.storage import FileSystemStorage
import io # Necesario para manejar el PDF en memoria
from django.template.loader import get_template # Para cargar templates para el PDF
from xhtml2pdf import pisa # La librería para generar PDFs
from django.core.files.storage import default_storage
from django.conf import settings
from .models import CertificadoAntecedentes, Usuario # Asegúrate de importar CertificadoAntecedentes y Usuario
from django.db import transaction, IntegrityError # Importar para asegurar atomicidad y manejar errores de integridad
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
import json
import logging
from django.shortcuts import get_object_or_404
from .models import PersonaNatural, CV, CertificadoAntecedentes, EstadoDocumento, Usuario # Asegúrate de importar Usuario si lo necesitas para buscar por RUT
from django.db import transaction
from django.utils import timezone
from datetime import datetime as dt # Para parsear fechas si es necesario
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.conf import settings
import googlemaps
from django.db import transaction
from .forms import OfertaTrabajoForm




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

# --- Vista de Registro (Versión Final Simplificada) ---
Usuario = get_user_model() # Obtén tu modelo de Usuario personalizado

# --- VISTA DE REGISTRO CON GEOCODIFICACIÓN PARA USUARIO ---
def registro(request):
    # Redirigir si el usuario ya está autenticado
    if request.user.is_authenticated:
        messages.info(request, _("Ya has iniciado sesión. No puedes registrarte de nuevo."))
        return redirect('miperfil') 

    if request.method == 'POST':
        form = RegistroForm(request.POST, request.FILES)
        logger.debug(f"POST recibido en registro. request.FILES: {request.FILES}")

        if form.is_valid():
            logger.debug("Formulario de registro VÁLIDO.")
            rut = form.cleaned_data['username'] # El RUT es el username

            # Obtener los datos validados para la ubicación del usuario
            ubicacion_display = form.cleaned_data.get('ubicacion_display') # El campo de texto visible
            direccion_form = form.cleaned_data.get('direccion') # Este viene del hidden input de la dirección formateada
            latitud_form = form.cleaned_data.get('latitud')     # Este viene del hidden input
            longitud_form = form.cleaned_data.get('longitud')   # Este viene del hidden input

            # Inicializar latitud, longitud y dirección para el modelo Usuario
            latitud_db = None
            longitud_db = None
            direccion_db = direccion_form # Priorizamos la dirección formateada del JS si existe

            # Si el JS no llenó la latitud/longitud, intentar geocodificar en el backend usando ubicacion_display
            if ubicacion_display and not (latitud_form and longitud_form) and gmaps:
                try:
                    gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                    geocode_result = gmaps.geocode(ubicacion_display)
                    if geocode_result:
                        location = geocode_result[0]['geometry']['location']
                        latitud_db = location['lat']
                        longitud_db = location['lng']
                        # Usar la dirección formateada por Google si la geocodificación fue exitosa
                        direccion_db = geocode_result[0]['formatted_address']
                        messages.success(request, _('Tu dirección ha sido geocodificada exitosamente.'))
                        logger.info(f"Dirección geocodificada en registro (ubicacion_display): {direccion_db}")
                    else:
                        messages.warning(request, _('No se pudo geocodificar tu dirección. Por favor, revisa la dirección.'))
                        logger.warning(f"No se pudo geocodificar en registro (ubicacion_display): {ubicacion_display}")
                except Exception as e:
                    messages.error(request, _(f'Error al geocodificar tu dirección: {e}'))
                    logger.error(f"Error al geocodificar en registro {ubicacion_display}: {e}")
            elif (latitud_form and longitud_form): # Si el JS llenó los campos ocultos (mapa o autocompletado)
                latitud_db = latitud_form
                longitud_db = longitud_form
                # Si la dirección formateada no vino del JS, pero sí las coords, intentar geocodificación inversa
                if not direccion_db and gmaps:
                     try:
                        reverse_geocode = gmaps.reverse_geocode((latitud_db, longitud_db))
                        if reverse_geocode:
                            direccion_db = reverse_geocode[0]['formatted_address']
                            messages.info(request, _('Dirección obtenida por geocodificación inversa usando las coordenadas del mapa.'))
                            logger.info(f"Dirección geocodificada inversa en registro (lat/lng): {direccion_db}")
                        else:
                            messages.warning(request, _('No se pudo obtener la dirección completa por geocodificación inversa.'))
                            logger.warning(f"No se pudo obtener dirección inversa para lat:{latitud_db}, lng:{longitud_db} en registro")
                     except Exception as e:
                        logger.warning(f"Error en geocodificación inversa en registro (solo lat/lng): {e}")
            elif not gmaps:
                messages.warning(request, _('La geocodificación de la dirección no está disponible (API Key no configurada).'))

            try:
                # --- Usar una transacción atómica para asegurar que todo se guarda o nada ---
                with transaction.atomic():
                    # Crear y guardar el usuario
                    usuario = form.save(commit=False)
                    usuario.latitud = latitud_db      # Asigna la latitud final
                    usuario.longitud = longitud_db    # Asigna la longitud final
                    usuario.direccion = direccion_db  # Asigna la dirección final
                    usuario.save() # Guarda el usuario con los campos de ubicación actualizados
                    logger.info(f"Usuario creado y geocodificado: {usuario.username} (ID: {usuario.pk}) - Lat: {usuario.latitud}, Lng: {usuario.longitud}, Dir: {usuario.direccion}")

                    # 2. Crear el perfil (PersonaNatural o Empresa)
                    tipo_usuario = form.cleaned_data['tipo_usuario']
                    
                    if tipo_usuario == 'persona':
                        # Crea la PersonaNatural, enlazándola al usuario recién creado
                        persona_natural = PersonaNatural.objects.create(
                            usuario=usuario, # Pasa la instancia de usuario recién creada
                            nombres=form.cleaned_data.get('nombres'),
                            apellidos=form.cleaned_data.get('apellidos'),
                            fecha_nacimiento=form.cleaned_data.get('fecha_nacimiento'),
                            nacionalidad=form.cleaned_data.get('nacionalidad', 'Chilena')
                        )
                        logger.info(f"Perfil Persona Natural creado para {usuario.username} (ID: {persona_natural.pk})")

                        # --- Lógica para CV, asociada a persona_natural ---
                        cv_file = request.FILES.get('cv_archivo') # Obtén el objeto UploadedFile del formulario
                        if cv_file:
                            try:
                                file_extension = os.path.splitext(cv_file.name)[1]
                                # Usar un UUID para el nombre del archivo para evitar colisiones
                                safe_username = usuario.username.replace('/', '_').replace('\\', '_')
                                cv_filename_in_gcs = f'cvs/{safe_username}_CV_{uuid.uuid4().hex}{file_extension}'
                                
                                # Guarda el archivo en GCS usando default_storage. Esto devuelve la ruta relativa.
                                cv_gcs_relative_path = default_storage.save(cv_filename_in_gcs, cv_file)
                                
                                # Crea la instancia de CV asociada a la persona_natural
                                CV.objects.create(
                                    persona=persona_natural, # Asociado a la instancia de PersonaNatural
                                    archivo_cv=cv_gcs_relative_path, # ASIGNAR LA RUTA RELATIVA AL CHARFIELD
                                    processing_status=EstadoDocumento.PENDIENTE, # Establecer estado inicial
                                    rejection_reason=None, # Limpiar razón de rechazo
                                    datos_analizados_ia={}, # Limpiar datos de IA
                                    last_processed_at=timezone.now() # Fecha de última actualización/procesamiento
                                )
                                messages.info(request, _('CV subido exitosamente y en proceso de análisis.'))
                                logger.info(f"CV subido en registro para {usuario.username}: {cv_gcs_relative_path}")
                            except Exception as e:
                                logger.error(f"Error al subir CV durante el registro para {usuario.username}: {e}", exc_info=True)
                                messages.warning(request, _('Hubo un problema al subir tu CV. Puedes subirlo después en tu perfil.'))
                        else:
                            logger.info(f"No se proporcionó CV para {usuario.username}.")
                            # Si no se proporciona CV, aún así crea la instancia para que el usuario pueda subirlo después
                            CV.objects.create(persona=persona_natural) # Crea una instancia vacía
                            logger.info(f"Instancia de CV vacía creada para {usuario.username}.")

                        # --- Lógica para Certificado de Antecedentes, asociada a persona_natural ---
                        certificado_file = request.FILES.get('certificado_pdf') # Obtén el objeto UploadedFile del formulario
                        if certificado_file:
                            try:
                                file_extension = os.path.splitext(certificado_file.name)[1]
                                # Usar un UUID para el nombre del archivo para evitar colisiones
                                safe_username = usuario.username.replace('/', '_').replace('\\', '_')
                                certificado_filename_in_gcs = f'certificados/{safe_username}_CERT_{uuid.uuid4().hex}{file_extension}'

                                # Guarda el archivo en GCS usando default_storage. Esto devuelve la ruta relativa.
                                certificado_gcs_relative_path = default_storage.save(certificado_filename_in_gcs, certificado_file)
                                
                                # Crea la instancia de CertificadoAntecedentes asociada a la persona_natural
                                CertificadoAntecedentes.objects.create(
                                    persona=persona_natural, # Asociado a la instancia de PersonaNatural
                                    archivo_certificado=certificado_gcs_relative_path, # ASIGNAR LA RUTA RELATIVA AL CHARFIELD
                                    processing_status=EstadoDocumento.PENDIENTE, # Establecer estado inicial
                                    rejection_reason=None, # Limpiar razón de rechazo
                                    datos_analizados_ia={}, # Limpiar datos de IA
                                    last_processed_at=timezone.now() # Fecha de última actualización/procesamiento
                                )
                                messages.info(request, _('Certificado de antecedentes subido y pendiente de verificación.'))
                                logger.info(f"Certificado subido en registro para {usuario.username}: {certificado_gcs_relative_path}")
                            except Exception as e:
                                logger.error(f"Error al subir Certificado durante el registro para {usuario.username}: {e}", exc_info=True)
                                messages.warning(request, _('Hubo un problema al subir tu Certificado de Antecedentes. Puedes subirlo después en tu perfil.')
                                )
                        else:
                            logger.info(f"No se proporcionó certificado para {usuario.username}.")
                            # Si no se proporciona certificado, aún así crea la instancia
                            CertificadoAntecedentes.objects.create(persona=persona_natural) # Crea una instancia vacía
                            logger.info(f"Instancia de CertificadoAntecedentes vacía creada para {usuario.username}.")
                            
                    elif tipo_usuario == 'empresa':
                        # Crea la Empresa, enlazándola al usuario recién creado
                        empresa = Empresa.objects.create(
                            usuario=usuario, # Pasa la instancia de usuario recién creada
                            nombre_empresa=form.cleaned_data.get('nombre_empresa'),
                            razon_social=form.cleaned_data.get('razon_social'),
                            giro=form.cleaned_data.get('giro')
                        )
                        logger.info(f"Perfil Empresa creado para {usuario.username} (ID: {empresa.pk})")

                # Si todo dentro de la transacción atómica fue exitoso
                login(request, usuario) # Loguear al usuario automáticamente
                messages.success(request, _("¡Registro exitoso! Tu cuenta ha sido creada y has iniciado sesión."))
                return redirect(reverse('miperfil')) # Redirige al perfil del usuario

            except IntegrityError as e:
                logger.error(f"IntegrityError durante el registro para {rut}: {e}", exc_info=True)
                messages.error(request, _("Error de registro: Este RUT o correo electrónico ya está en uso. Si el problema persiste, contacta a soporte."))
                return render(request, 'gestionOfertas/registro.html', {
                    'form': form,
                    'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY  # ← AÑADIR ESTO
                })
            except ValidationError as e:
                logger.warning(f"ValidationError durante el registro para {rut}: {e.message}", exc_info=True)
                messages.error(request, f"Error de validación: {e.message}")
                return render(request, 'gestionOfertas/registro.html', {
                    'form': form,
                    'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY  # ← AÑADIR ESTO
                })
            except Exception as e:
                logger.exception(f"Error inesperado durante el registro de usuario {rut}: {e}")
                messages.error(request, _("Ocurrió un error inesperado durante el registro. Por favor, inténtalo de nuevo."))
                return render(request, 'gestionOfertas/registro.html', {
                    'form': form,
                    'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY  # ← AÑADIR ESTO
                })
        else:
            logger.warning(f"Formulario de registro NO VÁLIDO. Errores: {form.errors.as_json()}")
            messages.error(request, _('Por favor, corrige los errores en el formulario.'))
            for field, errors in form.errors.items():
                for error in errors:
                    field_label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"Error en '{field_label}': {error}")
    else:
        form = RegistroForm()
    
    # ← CAMBIO PRINCIPAL: Pasar la API key al contexto del template
    return render(request, 'gestionOfertas/registro.html', {
        'form': form,
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    })

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
    template_name = 'registration/password_reset_form.html'
    email_template_name = 'registration/password_reset_email.html'
    subject_template_name = 'registration/password_reset_subject.txt'
    success_url = reverse_lazy('password_reset_done')


from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from .models import OfertaTrabajo, Categoria

def ofertas_urgentes_view(request):
    hoy = timezone.now().date()

    # Base queryset: solo ofertas urgentes, activas y dentro del plazo
    queryset = OfertaTrabajo.objects.filter(
        urgente=True,
        esta_activa=True
    ).filter(
        Q(fecha_cierre__gte=hoy) | Q(fecha_cierre__isnull=True)
    ).select_related('creador', 'empresa', 'categoria')

    # Filtros GET
    q = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria')
    tipo_contrato = request.GET.get('tipo_contrato')
    tipo_oferta = request.GET.get('tipo_oferta')

    if q:
        queryset = queryset.filter(
            Q(nombre__icontains=q) |
            Q(descripcion__icontains=q) |
            Q(empresa__nombre__icontains=q) |
            Q(creador__first_name__icontains=q) |
            Q(creador__last_name__icontains=q)
        )

    if categoria_id:
        try:
            queryset = queryset.filter(categoria_id=int(categoria_id))
        except (ValueError, TypeError):
            pass

    if tipo_contrato and tipo_contrato in dict(OfertaTrabajo.TIPO_CONTRATO_CHOICES):
        queryset = queryset.filter(tipo_contrato=tipo_contrato)

    if tipo_oferta:
        if tipo_oferta == 'empleo':
            queryset = queryset.filter(es_servicio=False)
        elif tipo_oferta == 'servicio':
            queryset = queryset.filter(es_servicio=True)

    queryset = queryset.order_by('-fecha_publicacion')

    # Paginación
    paginator = Paginator(queryset, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'ofertas': page_obj,
        'categorias': Categoria.objects.all(),
        'tipos_contrato': OfertaTrabajo.TIPO_CONTRATO_CHOICES,
        'total_ofertas_urgentes': OfertaTrabajo.objects.filter(
            urgente=True,
            esta_activa=True,
            fecha_cierre__gte=hoy
        ).count(),
        'current_search': q,
        'current_categoria': categoria_id or '',
        'current_tipo_contrato': tipo_contrato or '',
        'current_tipo_oferta': tipo_oferta or '',
    }

    return render(request, 'gestionOfertas/ofertas_urgentes.html', context)




def inicio(request):
    # Obtener parámetros de búsqueda válidos según el modelo
    busqueda = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    tipo_contrato = request.GET.get('tipo_contrato', '')
    salario_min = request.GET.get('salario_min', '')
    salario_max = request.GET.get('salario_max', '')
    
    # Obtener ofertas activas y vigentes
    hoy = timezone.now().date()
    ofertas = OfertaTrabajo.objects.filter(
        esta_activa=True
    ).filter(
        Q(fecha_cierre__gte=hoy) | Q(fecha_cierre__isnull=True)
    ).order_by('-fecha_publicacion')
    
    # Aplicar filtro de búsqueda por texto
    if busqueda:
        ofertas = ofertas.filter(
            Q(nombre__icontains=busqueda) |
            Q(descripcion__icontains=busqueda) |
            Q(empresa__nombre_empresa__icontains=busqueda)
        ).distinct()
    
    # Aplicar filtro por categoría
    if categoria_id:
        ofertas = ofertas.filter(categoria_id=categoria_id)
    
    # Aplicar filtro por tipo de contrato (según choices del modelo)
    if tipo_contrato:
        tipos_validos = [choice[0] for choice in OfertaTrabajo.TIPO_CONTRATO_CHOICES]
        if tipo_contrato in tipos_validos:
            ofertas = ofertas.filter(tipo_contrato=tipo_contrato)
    
    # Aplicar filtros por salario (si es numérico)
    if salario_min:
        try:
            # Asumiendo que el salario se almacena como texto, necesitarías una lógica especial
            # Esta es una implementación básica que deberías adaptar
            ofertas = [oferta for oferta in ofertas if float(salario_min) <= float(oferta.salario or 0)]
        except (ValueError, TypeError):
            pass
    
    if salario_max:
        try:
            ofertas = [oferta for oferta in ofertas if float(salario_max) >= float(oferta.salario or float('inf'))]
        except (ValueError, TypeError):
            pass
    
    # Preparar contexto para la plantilla
    context = {
        'ofertas': ofertas,
        'categorias': Categoria.objects.filter(activa=True),
        'busqueda_actual': busqueda,
        'categoria_actual': categoria_id,
        'tipo_contrato_actual': tipo_contrato,
        'salario_min_actual': salario_min,
        'salario_max_actual': salario_max,
        # Eliminados los filtros que no existen en el modelo
    }
    
    return render(request, 'gestionOfertas/Inicio.html', context)



@login_required
def crear_oferta(request):
    if request.method == 'POST':
        form = OfertaTrabajoForm(request.POST, user=request.user)
        
        if form.is_valid():
            try:
                oferta = form.save(commit=False)
                oferta.creador = request.user
                
                # Asignar empresa si el usuario es una empresa
                if hasattr(request.user, 'empresa'):
                    oferta.empresa = request.user.empresa
                # --- ÚNICA MODIFICACIÓN AQUÍ ---
                # Queremos que TODAS las ofertas creadas aquí (ofertas de trabajo)
                # permitan ver postulantes, por lo tanto, NO son servicios.
                oferta.es_servicio = False 
                # --- FIN ÚNICA MODIFICACIÓN ---
                
                # Procesar ubicación si se proporcionó
                if form.cleaned_data.get('latitud') and form.cleaned_data.get('longitud'):
                    # Si no hay dirección pero hay coordenadas, hacer geocodificación inversa
                    if not oferta.direccion:
                        try:
                            gmaps = googlemaps.Client(key=settings.GOOGLE_MAPS_API_KEY)
                            reverse_geocode = gmaps.reverse_geocode(
                                (form.cleaned_data['latitud'], form.cleaned_data['longitud'])
                            )
                            if reverse_geocode:
                                oferta.direccion = reverse_geocode[0]['formatted_address']
                        except (googlemaps.exceptions.ApiError, googlemaps.exceptions.HTTPError) as e:
                            messages.warning(
                                request, 
                                _('La ubicación se guardó pero no pudimos obtener la dirección completa.')
                            )
                            print(f"Error en geocodificación inversa: {e}")
                
                # Guardar la oferta
                oferta.save()
                form.save_m2m()  # Para guardar relaciones many-to-many si las hay
                
                # Notificación si es urgente
                if oferta.urgente:
                    notificar_oferta_urgente(oferta)
                
                # Mensaje de éxito
                msg = _('¡Oferta de empleo creada con éxito!') if hasattr(request.user, 'empresa') \
                    else _('¡Servicio publicado correctamente!')
                messages.success(request, msg)
                
                return redirect('mis_ofertas')
                
            except Exception as e:
                messages.error(
                    request, 
                    _('Ocurrió un error al guardar la oferta. Por favor intenta nuevamente.')
                )
                print(f"Error al guardar oferta: {e}")
        else:
            messages.warning(
                request, 
                _('Por favor corrige los errores en el formulario.')
            )
    else:
        form = OfertaTrabajoForm(user=request.user)

    context = {
        'form': form,
        'es_empresa': hasattr(request.user, 'empresa'),
        'es_persona': hasattr(request.user, 'personanatural'),
        'google_maps_api_key': settings.GOOGLE_MAPS_API_KEY
    }

    return render(request, 'gestionOfertas/crear_oferta.html', context)

@login_required
def mis_ofertas(request):
    usuario = request.user
    # MODIFICACIÓN: Usamos prefetch_related para cargar eficientemente
    # todas las postulaciones y los datos de los postulantes asociados a cada oferta.
    # Esto evita hacer múltiples consultas a la base de datos desde la plantilla.
    ofertas = OfertaTrabajo.objects.filter(creador=usuario).select_related(
        'categoria', 'empresa'
    ).prefetch_related(
        'postulaciones_recibidas', 
        'postulaciones_recibidas__persona'
    )

    # El contexto ahora es más completo, pero la plantilla lo manejará fácilmente.
    # Añadimos la variable 'es_empresa' para usarla en la plantilla.
    context = {
        'ofertas': ofertas,
        'es_empresa': hasattr(usuario, 'empresa')
    }
    return render(request, 'gestionOfertas/mis_ofertas.html', context)

@login_required
def postulantes_por_oferta(request, oferta_id):
    usuario = request.user
    oferta = get_object_or_404(OfertaTrabajo, id=oferta_id, creador=usuario)

    postulaciones = oferta.postulaciones_recibidas.select_related('persona', 'persona__usuario')

    context = {
        'oferta': oferta,
        'postulaciones': postulaciones,
    }
    return render(request, 'gestionOfertas/postulantes_oferta.html', context)

@login_required
def editar_oferta(request, oferta_id):
    """
    Vista para editar una oferta de trabajo existente.
    """
    # Obtener la oferta asegurando que pertenece al usuario logueado
    oferta = get_object_or_404(OfertaTrabajo, id=oferta_id, creador=request.user)
    
    if request.method == 'POST':
        # El formulario ya debe manejar la ubicación directamente de los campos ocultos
        form = EditarOfertaTrabajoForm(request.POST, request.FILES, instance=oferta, user=request.user)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Aquí simplemente guardamos la oferta.
                    # Los campos 'latitud', 'longitud' y 'direccion'
                    # ya deberían estar en form.cleaned_data y se guardarán
                    # directamente con form.save()
                    if oferta.urgente:
                        notificar_oferta_urgente(oferta)

                    oferta_actualizada = form.save(commit=True) # Guardamos directamente, ya que la dirección viene del form
                    
                    # form.save_m2m() es importante para relaciones many-to-many
                    # si tu formulario las maneja.
                    form.save_m2m() 
                    
                    messages.success(request, '¡Oferta actualizada correctamente!')
                    return redirect('mis_ofertas')
                    
            except Exception as e:
                # Captura cualquier error que ocurra durante el guardado
                messages.error(
                    request, 
                    'Ocurrió un error al actualizar la oferta. Por favor intenta nuevamente.'
                )
                print(f"Error al actualizar oferta: {e}")
        else:
            # Si el formulario no es válido, se renderiza la página con los errores del formulario
            messages.error(
                request, 
                'Por favor, corrige los errores en el formulario.'
            )
            print("Errores del formulario:", form.errors) # Para depuración
    else:
        # Inicializar el formulario con la instancia de la oferta
        form = EditarOfertaTrabajoForm(instance=oferta, user=request.user)
    
    context = {
        'form': form,
        'oferta': oferta,
        'GOOGLE_MAPS_API_KEY': settings.GOOGLE_MAPS_API_KEY,
        'es_empresa': hasattr(request.user, 'empresa'),
        'es_persona': hasattr(request.user, 'personanatural')
    }
    
    return render(request, 'gestionOfertas/editar_oferta.html', context)

# --- VISTA DE EDICIÓN DE PERFIL CON GEOCODIFICACIÓN PARA USUARIO ---
# @login_required
# def editar_perfil(request):
#     usuario = request.user
    
#     # Redirección para usuarios de tipo empresa (mantener igual)
#     if usuario.tipo_usuario == 'empresa':
#         messages.info(request, _('Actualmente, la edición completa del perfil de empresa no está disponible a través de esta página.'))
#         return redirect('miperfil')

#     # Obtener o crear la instancia de PersonaNatural
#     persona_natural = get_object_or_404(PersonaNatural, usuario=usuario)

#     # Obtener o crear las instancias de CV y Certificado (mantener igual)
#     cv_instance, cv_created = CV.objects.get_or_create(persona=persona_natural)
#     certificado_instance, cert_created = CertificadoAntecedentes.objects.get_or_create(persona=persona_natural)

#     if request.method == 'POST':
#         # Instanciar AMBOS formularios con los datos del POST y las instancias existentes
#         # Los archivos (request.FILES) van al formulario que los maneja (PersonaNaturalPerfilForm)
#         usuario_form = UsuarioPerfilForm(request.POST, instance=usuario)
#         persona_natural_form = PersonaNaturalPerfilForm(request.POST, request.FILES, instance=persona_natural)

#         # Validar AMBOS formularios
#         if usuario_form.is_valid() and persona_natural_form.is_valid():
#             try:
#                 with transaction.atomic(): # Asegura que todas las operaciones son atómicas

#                     # 1. Guardar el formulario de Usuario
#                     # Esto actualizará correo, telefono, direccion, latitud, longitud en el modelo Usuario
#                     usuario_form.save()
#                     logger.info(f"Vista editar_perfil: Usuario {usuario.username} guardado con lat={usuario.latitud}, lng={usuario.longitud}")

#                     # 2. Guardar el formulario de PersonaNatural
#                     # Esto actualizará nombres, apellidos, fecha_nacimiento, nacionalidad en el modelo PersonaNatural
#                     persona_natural_form.save()
#                     logger.info(f"Vista editar_perfil: PersonaNatural {persona_natural.nombres} {persona_natural.apellidos} guardado.")

#                     # --- Lógica para CV (mantener casi idéntica a tu original) ---
#                     cv_file = request.FILES.get('cv_archivo')
#                     if cv_file:
#                         if cv_instance.archivo_cv:
#                             old_cv_path = cv_instance.archivo_cv.name # Usar .name para la ruta
#                             if default_storage.exists(old_cv_path):
#                                 try:
#                                     default_storage.delete(old_cv_path)
#                                     logger.info(f"CV anterior '{old_cv_path}' borrado exitosamente.")
#                                 except Exception as e:
#                                     logger.error(f"Error al borrar CV anterior: {e}")

#                         file_extension = os.path.splitext(cv_file.name)[1]
#                         safe_username = usuario.username.replace('/', '_').replace('\\', '_')
#                         cv_filename_in_gcs = f'cvs/{safe_username}_CV_{uuid.uuid4().hex}{file_extension}'
                        
#                         try:
#                             cv_gcs_relative_path = default_storage.save(cv_filename_in_gcs, cv_file)
#                             logger.info(f"Nuevo CV subido: '{cv_gcs_relative_path}'")
                            
#                             cv_instance.archivo_cv = cv_gcs_relative_path
#                             cv_instance.processing_status = EstadoDocumento.PENDIENTE
#                             cv_instance.rejection_reason = None
#                             cv_instance.datos_analizados_ia = {}
#                             cv_instance.last_processed_at = timezone.now()
#                             cv_instance.save()
                            
#                             messages.success(request, _('CV subido correctamente y en proceso de análisis.'))
#                         except Exception as e:
#                             messages.error(request, _(f'Error al subir el CV: {e}'))
#                             logger.error(f"Error al subir CV: {e}", exc_info=True)

#                     # --- Lógica para Certificado (mantener casi idéntica a tu original) ---
#                     certificado_file = request.FILES.get('certificado_pdf')
#                     if certificado_file:
#                         if certificado_instance.archivo_certificado:
#                             old_cert_path = certificado_instance.archivo_certificado.name # Usar .name para la ruta
#                             if default_storage.exists(old_cert_path):
#                                 try:
#                                     default_storage.delete(old_cert_path)
#                                     logger.info(f"Certificado anterior '{old_cert_path}' borrado exitosamente.")
#                                 except Exception as e:
#                                     logger.error(f"Error al borrar certificado anterior: {e}")

#                         file_extension = os.path.splitext(certificado_file.name)[1]
#                         safe_username = usuario.username.replace('/', '_').replace('\\', '_')
#                         cert_filename_in_gcs = f'certificados/{safe_username}_CERT_{uuid.uuid4().hex}{file_extension}'

#                         try:
#                             cert_gcs_relative_path = default_storage.save(cert_filename_in_gcs, certificado_file)
#                             logger.info(f"Nuevo certificado subido: '{cert_gcs_relative_path}'")
                            
#                             certificado_instance.archivo_certificado = cert_gcs_relative_path
#                             certificado_instance.processing_status = EstadoDocumento.PENDIENTE
#                             certificado_instance.rejection_reason = None
#                             certificado_instance.datos_analizados_ia = {}
#                             certificado_instance.last_processed_at = timezone.now()
#                             certificado_instance.save()

#                             messages.success(request, _('Certificado subido correctamente y en proceso de análisis.'))
#                         except Exception as e:
#                             messages.error(request, _(f'Error al subir el certificado: {e}'))
#                             logger.error(f"Error al subir certificado: {e}", exc_info=True)

#                     messages.success(request, _('Perfil actualizado correctamente.'))
                    
#                     # Logging de coordenadas guardadas para debugging
#                     logger.info(f"Perfil actualizado para usuario {usuario.username}: "
#                                 f"lat={usuario.latitud}, lng={usuario.longitud}, dir='{usuario.direccion}'")
                    
#                     return redirect('miperfil')
                    
#             except IntegrityError as e:
#                 logger.error(f"IntegrityError al actualizar perfil: {e}", exc_info=True)
#                 messages.error(request, _("Error: Es posible que el correo ya esté en uso o haya un problema de datos duplicados."))
#             except ValidationError as e:
#                 logger.warning(f"ValidationError al actualizar perfil: {e}")
#                 messages.error(request, f"Error de validación: {e}")
#             except Exception as e:
#                 logger.exception(f"Error inesperado al actualizar perfil: {e}")
#                 messages.error(request, _("Error inesperado. Por favor, inténtalo de nuevo."))
#         else:
#             # Si uno o ambos formularios no son válidos, se muestran los errores
#             messages.error(request, _('Error al actualizar el perfil. Revisa los campos.'))
#             # Combinar errores de ambos formularios para mostrarlos al usuario
#             for form_name, form_obj in {'Usuario': usuario_form, 'Persona Natural': persona_natural_form}.items():
#                 if form_obj.errors:
#                     logger.warning(f"Errores en {form_name} Form: {form_obj.errors.as_json()}")
#                     for field, errors in form_obj.errors.items():
#                         for error in errors:
#                             field_label = form_obj.fields[field].label if field in form_obj.fields else field
#                             messages.error(request, f"Error en '{field_label}' ({form_name}): {error}")
#     else:
#         # Petición GET: Instanciar los formularios con los datos actuales
#         usuario_form = UsuarioPerfilForm(instance=usuario)
#         persona_natural_form = PersonaNaturalPerfilForm(instance=persona_natural)

#     # Asegurar que las coordenadas estén disponibles en el contexto (para JS del mapa)
#     context = {
#         'usuario_form': usuario_form, # Pasar el formulario de usuario
#         'persona_natural_form': persona_natural_form, # Pasar el formulario de persona natural
#         'persona_natural': persona_natural, # Aun útil para la lógica en template
#         'cv': cv_instance, # Aun útil para la lógica en template
#         'certificado': certificado_instance, # Aun útil para la lógica en template
#         'google_map_api_key': settings.GOOGLE_MAPS_API_KEY,
#         'MEDIA_URL': default_storage.base_url if hasattr(default_storage, 'base_url') else '/media/',
#         # Agregar valores seguros para debugging o para inicializar JS
#         'initial_lat': usuario.latitud if usuario.latitud is not None else -33.4489, # Coordenada por defecto (Santiago)
#         'initial_lng': usuario.longitud if usuario.longitud is not None else -70.6693,
#         'initial_address': usuario.direccion if usuario.direccion else '',
#     }
#     return render(request, 'gestionOfertas/editar_perfil.html', context)

from django.core.serializers.json import DjangoJSONEncoder

def mapa_ofertas_trabajo(request):
    """
    Vista para mostrar el mapa con todas las ofertas de trabajo activas
    y que no hayan vencido.
    """
    hoy = timezone.now().date()
    
    # Filtrar ofertas activas, con coordenadas válidas y fecha de cierre válida
    ofertas = OfertaTrabajo.objects.filter(
        esta_activa=True,
        latitud__isnull=False,
        longitud__isnull=False
    ).filter(
        Q(fecha_cierre__gte=hoy) | Q(fecha_cierre__isnull=True)
    ).select_related('categoria', 'empresa', 'creador').order_by('-fecha_publicacion')

    # Preparar datos para el mapa
    ofertas_data = []
    for oferta in ofertas:
        # Determinar el tipo de publicador
        if oferta.empresa:
            publicador = oferta.empresa.nombre_empresa
            tipo_publicador = "Empresa"
        else:
            publicador = f"{oferta.creador} {oferta.creador}".strip()
            if not publicador:
                publicador = oferta.creador.username
            tipo_publicador = "Persona Natural"

        # Determinar el tipo de oferta
        tipo_oferta = "Servicio" if oferta.es_servicio else "Empleo"

        # Preparar descripción corta para el popup
        descripcion_corta = oferta.descripcion[:100] + "..." if len(oferta.descripcion) > 100 else oferta.descripcion

        ofertas_data.append({
            'id': oferta.id,
            'nombre': oferta.nombre,
            'descripcion': descripcion_corta,
            'descripcion_completa': oferta.descripcion,
            'direccion': oferta.direccion,
            'latitud': float(oferta.latitud),
            'longitud': float(oferta.longitud),
            'categoria': oferta.categoria.nombre_categoria if oferta.categoria else 'Sin categoría',
            'salario': oferta.salario,
            'tipo_contrato': oferta.get_tipo_contrato_display() if oferta.tipo_contrato else '',
            'publicador': publicador,
            'tipo_publicador': tipo_publicador,
            'tipo_oferta': tipo_oferta,
            'urgente': oferta.urgente,
            'fecha_publicacion': oferta.fecha_publicacion.strftime('%d/%m/%Y'),
            'fecha_cierre': oferta.fecha_cierre.strftime('%d/%m/%Y') if oferta.fecha_cierre else 'Sin fecha límite'
        })

    context = {
        'ofertas_json': ofertas_data,
        'google_maps_api_key': getattr(settings, 'GOOGLE_MAPS_API_KEY', ''),
        'total_ofertas': len(ofertas_data)
    }

    return render(request, 'gestionOfertas/mapa.html', context)

def api_ofertas_mapa(request):
    """
    API endpoint para obtener ofertas en formato JSON (opcional)
    """
    ofertas = OfertaTrabajo.objects.filter(
        esta_activa=True,
        latitud__isnull=False,
        longitud__isnull=False
    ).select_related('categoria', 'empresa', 'creador')
    
    ofertas_data = []
    for oferta in ofertas:
        if oferta.empresa:
            publicador = oferta.empresa.nombre
            tipo_publicador = "Empresa"
        else:
            publicador = f"{oferta.creador.first_name} {oferta.creador.last_name}".strip()
            if not publicador:
                publicador = oferta.creador.username
            tipo_publicador = "Persona Natural"
        
        tipo_oferta = "Servicio" if oferta.es_servicio else "Empleo"
        
        ofertas_data.append({
            'id': oferta.id,
            'nombre': oferta.nombre,
            'descripcion': oferta.descripcion[:100] + "..." if len(oferta.descripcion) > 100 else oferta.descripcion,
            'direccion': oferta.direccion,
            'latitud': float(oferta.latitud),
            'longitud': float(oferta.longitud),
            'categoria': oferta.categoria.nombre if oferta.categoria else 'Sin categoría',
            'salario': oferta.salario,
            'publicador': publicador,
            'tipo_publicador': tipo_publicador,
            'tipo_oferta': tipo_oferta,
            'urgente': oferta.urgente,
        })
    
    return JsonResponse({'ofertas': ofertas_data})
    
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

    ofertas_creadas = usuario.ofertas_creadas.order_by('-fecha_publicacion')

    if usuario.tipo_usuario == 'empresa':
        todas_las_postulaciones = Postulacion.objects.filter(
            oferta__creador=usuario
        ).select_related('persona', 'oferta')
    else:
        todas_las_postulaciones = Postulacion.objects.filter(
            persona=perfil
        ).select_related('oferta', 'oferta__creador')

    postulaciones_filtradas = todas_las_postulaciones.filter(estado='filtrado').select_related('oferta')

    muestras_trabajo = MuestraTrabajo.objects.filter(usuario=usuario)
    muestras_agrupadas = agrupar_muestras(list(muestras_trabajo), 3)

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
        'muestras_trabajo': muestras_trabajo,
        'muestras_agrupadas': muestras_agrupadas,
    }

    return render(request, 'gestionOfertas/miperfil.html', context)


import locale # Nueva importación
import datetime # Nueva importación, aunque timezone.now() ya devuelve datetime

# Bloque try-except para configurar el locale de forma segura
# Esto es necesario para que strftime pueda obtener los nombres de los meses en español.
try:
    # Intenta configurar el locale para español en sistemas Unix/Linux
    locale.setlocale(locale.LC_TIME, 'es_ES.UTF-8')
except locale.Error:
    try:
        # Intenta configurar el locale para español en sistemas Windows
        locale.setlocale(locale.LC_TIME, 'Spanish_Spain.1252')
    except locale.Error:
        # Si ninguno funciona, se utilizará el locale por defecto del sistema
        print("Advertencia: No se pudo configurar el locale para español. Los nombres de los meses podrían no ser correctos.")


@login_required
@require_POST
def cambiar_estado_postulacion(request, postulacion_id):
    with transaction.atomic():
        try:
            postulacion = get_object_or_404(
                Postulacion,
                id=postulacion_id,
                oferta__creador=request.user
            )

            estado_original = postulacion.estado
            nuevo_estado = request.POST.get('nuevo_estado')
            estados_validos = ['pendiente', 'filtrado', 'match', 'contratado', 'rechazado', 'finalizado']

            if nuevo_estado not in estados_validos:
                messages.error(request, "Estado no válido.")
                return redirect('miperfil')

            postulacion.estado = nuevo_estado
            postulacion.save()

            messages.success(request, f"Estado de la postulación actualizado a '{nuevo_estado}'.")

            # Datos del contratante
            es_empresa = bool(postulacion.oferta.empresa)

            if es_empresa:
                contratante_nombre = postulacion.oferta.empresa.nombre_empresa
                razon_social = postulacion.oferta.empresa.razon_social
                giro = postulacion.oferta.empresa.giro
                contratante_correo = postulacion.oferta.empresa.usuario.correo
            else:
                persona = postulacion.oferta.creador.personanatural
                contratante_nombre = f"{persona.nombres} {persona.apellidos}"
                razon_social = "Persona Natural"
                giro = "Independiente"
                contratante_correo = postulacion.oferta.creador.correo

            # Si fue contratado por primera vez
            if nuevo_estado == 'contratado' and estado_original != 'contratado':
                try:
                    fecha_contratacion_formateada = postulacion.fecha_contratacion.strftime("%d de %B de %Y")
                    contexto = {
                        'postulacion': postulacion,
                        'postulante': postulacion.persona,
                        'oferta': postulacion.oferta,
                        'contratante_nombre': contratante_nombre,
                        'razon_social': razon_social,
                        'giro': giro,
                        'fecha_actual': timezone.now().strftime("%d-%m-%Y"),
                        'url_sitio': request.build_absolute_uri('/'),
                        'fecha_contratacion_formateada': fecha_contratacion_formateada,
                        'es_empresa': es_empresa,
                    }

                    # PDF
                    template_pdf = get_template('gestionOfertas/pdfs/carta_confirmacion_contratacion.html')
                    html_pdf = template_pdf.render(contexto)
                    result_file = io.BytesIO()
                    pisa_status = pisa.CreatePDF(html_pdf, dest=result_file, encoding='utf-8')
                    if pisa_status.err:
                        raise Exception("Error al generar el PDF.")

                    # --------- Correo al Postulante ----------
                    html_postulante = render_to_string('gestionOfertas/emails/confirmacion_contratacion.html', contexto)
                    text_postulante = strip_tags(html_postulante)

                    email_postulante = EmailMultiAlternatives(
                        subject=f"¡Felicitaciones! Has sido contratado/a para {postulacion.oferta.nombre}",
                        body=text_postulante,
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[postulacion.persona.usuario.correo]
                    )
                    email_postulante.attach_alternative(html_postulante, "text/html")
                    email_postulante.attach(
                        f"Confirmacion_Contratacion_{postulacion.persona.usuario.username}_{postulacion.oferta.id}.pdf",
                        result_file.getvalue(),
                        'application/pdf'
                    )
                    email_postulante.send()

                    # --------- Correo al Contratante ----------
                    try:
                        html_contratante = render_to_string('gestionOfertas/emails/confirmacion_contratacion_para_contratante.html', contexto)
                        text_contratante = strip_tags(html_contratante)

                        email_contratante = EmailMultiAlternatives(
                            subject=f"Has contratado a {postulacion.persona.nombres} {postulacion.persona.apellidos} para '{postulacion.oferta.nombre}'",
                            body=text_contratante,
                            from_email=settings.DEFAULT_FROM_EMAIL,
                            to=[contratante_correo]
                        )
                        email_contratante.attach_alternative(html_contratante, "text/html")
                        email_contratante.attach(
                            f"Contrato_{postulacion.persona.usuario.username}_{postulacion.oferta.id}.pdf",
                            result_file.getvalue(),
                            'application/pdf'
                        )
                        email_contratante.send()

                        messages.info(request, "Correos de confirmación enviados con éxito.")

                    except Exception as e:
                        logging.getLogger(__name__).error(f"Error al enviar el correo al contratante: {e}", exc_info=True)
                        messages.warning(request, "Se contrató correctamente, pero hubo un error al notificar al contratante.")

                except Exception as e:
                    messages.error(request, f"Error al enviar los correos: {e}")
                    logging.getLogger(__name__).exception("Error al enviar correos de contratación")

        except Postulacion.DoesNotExist:
            messages.error(request, "La postulación no existe o no tienes permiso para modificarla.")
        except Exception as e:
            messages.error(request, f"Ocurrió un error inesperado: {e}")

    return redirect('miperfil')

@login_required
def actualizar_modo_urgente(request):
    if request.method == 'POST':
        persona = request.user.personanatural
        persona.modo_urgente = 'modo_urgente' in request.POST
        persona.recibir_ofertas_urgentes = 'recibir_ofertas_urgentes' in request.POST
        persona.save()
        messages.success(request, "Tus preferencias de urgencia han sido actualizadas.")
    return redirect('miperfil')  # Redirige al perfil (ajusta si es necesario)

@login_required
def editar_perfil(request):
    usuario = request.user
    persona_natural = get_object_or_404(PersonaNatural, usuario=usuario)

    logger.info(f"DEBUG_GEOLOC: Tipo de usuario.latitud: {type(usuario.latitud)}")
    logger.info(f"DEBUG_GEOLOC: Valor directo de usuario.latitud: {usuario.latitud}")
    logger.info(f"DEBUG_GEOLOC: Tipo de usuario.longitud: {type(usuario.longitud)}")
    logger.info(f"DEBUG_GEOLOC: Valor directo de usuario.longitud: {usuario.longitud}")

    # --- NO DEBERÍA HABER CONVERSIÓN MANUAL A STRING AQUÍ ---
    # Si usuario.latitud es None, initial_lat será None.
    initial_lat = usuario.latitud if usuario.latitud is not None else None
    initial_lng = usuario.longitud if usuario.longitud is not None else None
    initial_address = usuario.direccion if usuario.direccion is not None else ''

    logger.info(f"DEBUG_CONTEXT_PREP: Latitud en contexto (pre-render): {initial_lat}")
    logger.info(f"DEBUG_CONTEXT_PREP: Longitud en contexto (pre-render): {initial_lng}")
    logger.info(f"DEBUG_CONTEXT_PREP: Dirección en contexto: {initial_address}")

    cv_instance, _ = CV.objects.get_or_create(persona=persona_natural)
    certificado_instance, _ = CertificadoAntecedentes.objects.get_or_create(persona=persona_natural)

    if request.method == 'POST':
        usuario_form = UsuarioPerfilForm(request.POST, instance=usuario)
        persona_natural_form = PersonaNaturalPerfilForm(request.POST, request.FILES, instance=persona_natural)

        logger.info(f"POST request for user: {usuario.username}")
        logger.info(f"UsuarioForm valid: {usuario_form.is_valid()}, errors: {usuario_form.errors}")
        logger.info(f"PersonaNaturalForm valid: {persona_natural_form.is_valid()}, errors: {persona_natural_form.errors}")

        if usuario_form.is_valid() and persona_natural_form.is_valid():
            try:
                with transaction.atomic():
                    usuario_form.save()
                    persona_natural_form.save() # Guarda los campos del modelo PersonaNatural

                    # --- Lógica para CV ---
                    cv_file = request.FILES.get('cv_archivo')
                    if cv_file:
                        # PASO 1: BORRAR EL CV ANTERIOR SI EXISTE EN GCS
                        # Si cv_instance.archivo_cv existe (no es None) Y tiene un nombre (no está vacío)
                        if cv_instance.archivo_cv and cv_instance.archivo_cv.name: 
                            old_cv_path = cv_instance.archivo_cv.name # <--- CORRECCIÓN AQUÍ: Acceder a .name
                            if default_storage.exists(old_cv_path):
                                try:
                                    default_storage.delete(old_cv_path)
                                    logger.info(f"DEBUG_UPLOAD: CV anterior '{old_cv_path}' borrado exitosamente de GCS.")
                                except Exception as e:
                                    logger.error(f"ERROR_UPLOAD: No se pudo borrar CV anterior '{old_cv_path}': {e}")
                            else:
                                logger.warning(f"DEBUG_UPLOAD: CV anterior '{old_cv_path}' no encontrado en GCS para borrar.")

                        # PASO 2: GENERAR UN NUEVO NOMBRE DE ARCHIVO ÚNICO CON UUID y el RUT del usuario
                        file_extension = os.path.splitext(cv_file.name)[1]
                        # Asegúrate de que el nombre de usuario (RUT) sea seguro para usar en una ruta de archivo
                        # Asumo que usuario.username ya es el RUT en el formato que necesitas (ej. 12345678-K)
                        # Si tu username puede tener puntos, y quieres quitarlos para el nombre del archivo:
                        safe_username = usuario.username.replace('/', '_').replace('\\', '_').replace('.', '') 
                        
                        cv_filename_in_gcs = f'cvs/{safe_username}_CV_{uuid.uuid4().hex}{file_extension}'
                        
                        logger.info(f"DEBUG_UPLOAD: Intentando guardar nuevo CV: '{cv_filename_in_gcs}'")
                        logger.info(f"DEBUG_UPLOAD: Tamaño del archivo CV: {cv_file.size} bytes")

                        try:
                            # PASO 3: Sube el nuevo archivo a GCS. default_storage.save() devuelve la ruta relativa.
                            # Aquí, el FieldFile está siendo manejado correctamente
                            cv_gcs_relative_path = default_storage.save(cv_filename_in_gcs, cv_file)
                            logger.info(f"DEBUG_UPLOAD: default_storage.save para CV devolvió la ruta: '{cv_gcs_relative_path}'")
                            
                            # PASO 4: Actualiza la instancia del modelo CV con la NUEVA RUTA ÚNICA y el estado
                            # Cuando asignas una cadena de texto a un FileField, este la usa como su 'name'
                            cv_instance.archivo_cv = cv_gcs_relative_path 
                            cv_instance.processing_status = EstadoDocumento.PENDIENTE 
                            cv_instance.rejection_reason = None 
                            cv_instance.datos_analizados_ia = {} 
                            cv_instance.last_processed_at = timezone.now() 
                            cv_instance.save()
                            
                            messages.success(request, 'CV subido correctamente y en proceso de análisis por IA.')
                            logger.info(f"CV para usuario {usuario.username} subido y actualizado.")

                        except Exception as e:
                            messages.error(request, f'Error al subir el CV: {e}')
                            logger.exception("Error al subir CV a GCS.")

                    # --- Lógica para Certificado de Antecedentes ---
                    certificado_file = request.FILES.get('certificado_pdf')
                    if certificado_file:
                        # PASO 1: BORRAR EL CERTIFICADO ANTERIOR SI EXISTE EN GCS
                        # Si certificado_instance.archivo_certificado existe (no es None) Y tiene un nombre
                        if certificado_instance.archivo_certificado and certificado_instance.archivo_certificado.name:
                            old_certificado_path = certificado_instance.archivo_certificado.name # <--- CORRECCIÓN AQUÍ
                            if default_storage.exists(old_certificado_path):
                                try:
                                    default_storage.delete(old_certificado_path)
                                    logger.info(f"DEBUG_UPLOAD: Certificado anterior '{old_certificado_path}' borrado exitosamente de GCS.")
                                except Exception as e:
                                    logger.error(f"ERROR_UPLOAD: No se pudo borrar Certificado anterior '{old_certificado_path}': {e}")
                            else:
                                logger.warning(f"DEBUG_UPLOAD: Certificado anterior '{old_certificado_path}' no encontrado en GCS para borrar.")

                        # PASO 2: GENERAR UN NUEVO NOMBRE DE ARCHIVO ÚNICO CON UUID y el RUT del usuario
                        file_extension = os.path.splitext(certificado_file.name)[1]
                        safe_username = usuario.username.replace('/', '_').replace('\\', '_').replace('.', '') 

                        certificado_filename_in_gcs = f'certificados/{safe_username}_CERT_{uuid.uuid4().hex}{file_extension}'

                        logger.info(f"DEBUG_UPLOAD: Intentando guardar nuevo Certificado: '{certificado_filename_in_gcs}'")
                        logger.info(f"DEBUG_UPLOAD: Tamaño del archivo Certificado: {certificado_file.size} bytes")

                        try:
                            # PASO 3: Sube el nuevo archivo a GCS. default_storage.save() devuelve la ruta relativa.
                            certificado_gcs_relative_path = default_storage.save(certificado_filename_in_gcs, certificado_file)
                            logger.info(f"DEBUG_UPLOAD: default_storage.save para Certificado devolvió la ruta: '{certificado_gcs_relative_path}'")
                            
                            # PASO 4: Actualiza la instancia del modelo Certificado con la NUEVA RUTA ÚNICA y el estado
                            certificado_instance.archivo_certificado = certificado_gcs_relative_path
                            certificado_instance.processing_status = EstadoDocumento.PENDIENTE 
                            certificado_instance.rejection_reason = None 
                            certificado_instance.datos_analizados_ia = {} 
                            certificado_instance.last_processed_at = timezone.now() 
                            certificado_instance.save() 

                            messages.success(request, 'Certificado de antecedentes subido correctamente y en proceso de análisis por IA.')
                            logger.info(f"Certificado para usuario {usuario.username} subido y actualizado.")

                        except Exception as e:
                            messages.error(request, f'Error al subir el Certificado de Antecedentes: {e}')
                            logger.exception("Error al subir Certificado de Antecedentes a GCS.")
                    
                    messages.success(request, 'Perfil actualizado correctamente.')
                    return redirect('miperfil') 

            except Exception as e:
                messages.error(request, f'Ocurrió un error al guardar tu perfil: {e}')
                logger.exception("Error al guardar perfil de usuario.")
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')

    else: # GET request
        usuario_form = UsuarioPerfilForm(instance=usuario)
        persona_natural_form = PersonaNaturalPerfilForm(instance=persona_natural)

    # Prepara los valores iniciales para el mapa (sin cambios)
    initial_lat = usuario.latitud if usuario.latitud is not None else None
    initial_lng = usuario.longitud if usuario.longitud is not None else None
    initial_address = usuario.direccion if usuario.direccion is not None else ''

    context = {
        'usuario_form': usuario_form,
        'persona_natural_form': persona_natural_form,
        'cv': cv_instance, 
        'certificado': certificado_instance, 
        'google_map_api_key': settings.GOOGLE_MAPS_API_KEY,
        'initial_lat': initial_lat,
        'initial_lng': initial_lng,
        'initial_address': initial_address,
        'MEDIA_URL': default_storage.base_url if hasattr(default_storage, 'base_url') else '/media/'
    }
    return render(request, 'gestionOfertas/editar_perfil.html', context)

def base(request):
    return render(request, 'gestionOfertas/base.html')

# Añadir vista de logout
def salir(request):
    logout(request)
    messages.info(request, 'Has cerrado sesión.')
    return redirect('inicio')

#DETALLE DE LA OFERTA PUBLICADA
def detalle_oferta(request, oferta_id):
    oferta = get_object_or_404(
        OfertaTrabajo.objects.select_related('empresa', 'categoria'),
        id=oferta_id,
        esta_activa=True  # Opcional: filtrar solo ofertas activas
    )
    
    context = {
        'oferta': oferta,
        'es_urgente': oferta.es_urgente(),  # Si tienes un método para determinar urgencia
        'meta_title': f"{oferta.nombre} - {oferta.empresa.nombre_empresa}" if oferta.empresa else oferta.nombre,
        'meta_description': f"Oferta de trabajo: {oferta.nombre}. {oferta.descripcion[:160]}...",
    }
    
    return render(request, 'gestionOfertas/detalle_oferta.html', context)


from django.utils import timezone

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
            'year': timezone.now().year,
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
        return redirect('mis_postulaciones_persona')
    
    except Exception as e:
        messages.error(request, f"Ha ocurrido un error al procesar tu postulación: {str(e)}")
        return redirect('detalle_oferta', oferta_id=oferta_id)



@login_required
def mis_postulaciones_persona(request):
    usuario = request.user

    # Asegurarse que solo accedan personas naturales
    if usuario.tipo_usuario != 'persona':
        return redirect('inicio')  # o lanzar un 403

    perfil = usuario.get_profile()

    todas_las_postulaciones = Postulacion.objects.filter(
        persona=perfil
    ).select_related('oferta', 'oferta__creador')

    context = {
        'usuario': usuario,
        'perfil': perfil,
        'todas_las_postulaciones': todas_las_postulaciones,
        'tiene_todas_las_postulaciones': todas_las_postulaciones.exists(),
    }

    return render(request, 'gestionOfertas/mis_postulaciones_persona.html', context)


@login_required
def historial_valoraciones(request, usuario_id):
    usuario_perfil = get_object_or_404(Usuario, id=usuario_id)
    
    # Verificar permisos (solo el usuario o admin puede ver su historial)
    if not (request.user == usuario_perfil or request.user.is_staff):
        messages.error(request, "No tienes permiso para ver este historial.")
        return redirect('inicio')

    # Valoraciones recibidas
    valoraciones_recibidas = Valoracion.objects.filter(
        receptor=usuario_perfil
    ).order_by('-fecha_creacion').select_related('emisor', 'postulacion')

    # Postulaciones pendientes de valoración
    postulaciones_pendientes = []
    if request.user == usuario_perfil:  # Solo mostrar si es el propio usuario
        
        # Preparamos una consulta base para postulaciones finalizadas
        postulaciones_finalizadas = Postulacion.objects.filter(estado='finalizado')

        if usuario_perfil.tipo_usuario == 'empresa':
            # La lógica para empresa ya era correcta: solo puede crear ofertas.
            postulaciones = postulaciones_finalizadas.filter(
                oferta__creador=usuario_perfil
            )
        
        elif usuario_perfil.tipo_usuario == 'persona':
            # --- AQUÍ ESTÁ LA CORRECCIÓN ---
            # Buscamos postulaciones donde la persona es el POSTULANTE O el CREADOR de la oferta.
            # Asumo que el modelo Postulacion tiene un campo 'persona' que apunta a PersonaNatural
            # y PersonaNatural tiene un campo 'usuario' que apunta a Usuario.
            postulaciones = postulaciones_finalizadas.filter(
                Q(persona__usuario=usuario_perfil) | Q(oferta__creador=usuario_perfil)
            ).distinct() # .distinct() para evitar duplicados si una persona se postula a su propia oferta (caso borde)

        else:
            postulaciones = Postulacion.objects.none() # Manera más limpia de devolver un queryset vacío

        # El resto de tu lógica para verificar si ya existe una valoración es correcta y no necesita cambios.
        for postulacion in postulaciones.select_related('persona', 'oferta', 'oferta__creador'):
            if not Valoracion.objects.filter(postulacion=postulacion, emisor=request.user).exists():
                postulaciones_pendientes.append(postulacion)

    # Manejar POST para valoraciones desde el modal
    if request.method == 'POST':
        form = ValoracionForm(request.POST)
        if form.is_valid():
            postulacion_id = request.POST.get('postulacion_id')
            postulacion = get_object_or_404(Postulacion, id=postulacion_id)
            
            puede_valorar, receptor = postulacion.puede_valorar(request.user)
            if not puede_valorar:
                return JsonResponse({'success': False, 'error': 'No tienes permiso para valorar esta postulación'})

            valoracion = form.save(commit=False)
            valoracion.emisor = request.user
            valoracion.receptor = receptor
            valoracion.postulacion = postulacion
            valoracion.save()
            
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'errors': form.errors.as_json()})

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


@login_required
def ver_perfil_publico(request, usuario_id):
    try:
        usuario = Usuario.objects.get(id=usuario_id)
    except Usuario.DoesNotExist:
        messages.error(request, "El usuario solicitado no existe.")
        return redirect('home')

    if request.user.id == usuario.id:
        return redirect('miperfil')

    perfil = usuario.get_profile()
    muestras_trabajo = usuario.muestras_trabajo.all().order_by('-fecha_subida')
    muestras_agrupadas = agrupar_muestras(list(muestras_trabajo), 3)

    return render(request, 'gestionOfertas/miperfil_publico.html', {
        'usuario': usuario,
        'perfil': perfil,
        'valoracion_promedio': usuario.valoracion_promedio,
        'cantidad_valoraciones': usuario.cantidad_valoraciones,
        'valoraciones_recibidas': Valoracion.objects.filter(receptor=usuario)[:5],
        'ofertas_creadas': usuario.ofertas_creadas.filter(esta_activa=True),
        'muestras_trabajo': muestras_trabajo,
        'muestras_agrupadas': muestras_agrupadas,
    })



@login_required
@require_POST
def subir_muestra_trabajo(request):
    archivo = request.FILES.get('archivo')
    titulo = request.POST.get('titulo')
    descripcion = request.POST.get('descripcion')

    if archivo and titulo:
        MuestraTrabajo.objects.create(
            usuario=request.user,
            archivo=archivo,
            titulo=titulo,
            descripcion=descripcion or ''
        )
        messages.success(request, "Muestra subida correctamente.")
    else:
        messages.error(request, "Faltan datos requeridos.")

    return redirect('miperfil')

@login_required
def eliminar_muestra_trabajo(request, muestra_id):
    muestra = get_object_or_404(MuestraTrabajo, id=muestra_id, usuario=request.user)
    muestra.delete()
    return redirect('miperfil')

def agrupar_muestras(lista, tamaño=3):
    return [lista[i:i + tamaño] for i in range(0, len(lista), tamaño)]




logger = logging.getLogger(__name__)

# Esta función es CRUCIAL y DEBE ESTAR EN ESTE ARCHIVO o importarse correctamente.
def get_gcs_relative_path_from_full_url(gcs_url):
    """
    Extrae la ruta relativa del objeto en GCS (ej. 'cvs/nombre.pdf')
    desde una URL completa (https:// o gs://).
    """
    if not gcs_url:
        return None
    
    # Asegúrate de que GS_MEDIA_BUCKET_NAME esté definido en settings.py
    bucket_name = getattr(settings, 'GS_MEDIA_BUCKET_NAME', None) 
    if not bucket_name:
        logger.error("GS_MEDIA_BUCKET_NAME no está definido en settings. No se puede procesar la URL de GCS.")
        return None

    # Caso 1: URL https://storage.googleapis.com/<bucket>/path/to/file
    if gcs_url.startswith('https://storage.googleapis.com/'):
        # Ejemplo: https://storage.googleapis.com/matchjob/cvs/12345678-9_MiCV.pdf
        # Queremos 'cvs/12345678-9_MiCV.pdf'
        expected_prefix = f'https://storage.googleapis.com/{bucket_name}/'
        if gcs_url.startswith(expected_prefix):
            return gcs_url[len(expected_prefix):]
        else:
            logger.warning(f"URL HTTPS de GCS no coincide con el bucket esperado '{bucket_name}': {gcs_url}")
            return None
    
    # Caso 2: URL gs://bucket-name/path/to/file
    if gcs_url.startswith('gs://'):
        # Ejemplo: gs://matchjob/cvs/12345678-9_MiCV.pdf
        # Queremos 'cvs/12345678-9_MiCV.pdf'
        expected_prefix = f'gs://{bucket_name}/'
        if gcs_url.startswith(expected_prefix):
            return gcs_url[len(expected_prefix):]
        else:
            logger.warning(f"URL GS de GCS no coincide con el bucket esperado '{bucket_name}': {gcs_url}")
            return None 

    # Si la URL no tiene ninguno de los formatos esperados
    logger.error(f"Formato de URL GCS inesperado: {gcs_url}. No se pudo extraer la ruta relativa.")
    return None


# Función auxiliar para parsear y guardar datos de CV
def process_cv_data(persona, payload):
    logger.info(f"Procesando datos de CV para RUT: {persona.usuario.username}")
    
    cv, created = CV.objects.get_or_create(persona=persona)

    # Actualizar la URL de GCS si viene en el payload
    if 'file_gcs_url' in payload:
        gcs_url_from_cf = payload['file_gcs_url']
        
        # ¡CAMBIO CRUCIAL AQUÍ! Usa la función auxiliar
        relative_path = get_gcs_relative_path_from_full_url(gcs_url_from_cf)
        
        if relative_path:
            # Asigna la ruta relativa al atributo .name del FileField
            # Esto NO sube el archivo, solo le dice al FileField dónde está en GCS
            cv.archivo_cv.name = relative_path 
            logger.info(f"DEBUG_CF_PROCESS: URL de CV recibida de CF ('{gcs_url_from_cf}') asignada como ruta relativa: '{cv.archivo_cv.name}'")
        else:
            logger.error(f"DEBUG_CF_PROCESS: No se pudo determinar la ruta relativa para el CV de CF: '{gcs_url_from_cf}'. El archivo CV no será actualizado en el modelo.")
    else:
        logger.warning(f"DEBUG_CF_PROCESS: Payload de CF para CV no contiene 'file_gcs_url'. No se actualiza el archivo_cv en el modelo.")

    # Guardar el JSON completo de la IA directamente en datos_analizados_ia
    cv.datos_analizados_ia = payload.get('extracted_data', {})
    
    # Actualizar estado de procesamiento y razón de rechazo
    cv.processing_status = payload.get('processing_status', EstadoDocumento.ERROR) 
    cv.rejection_reason = payload.get('rejection_reason')
    cv.last_processed_at = timezone.now()

    try:
        cv.full_clean() 
        cv.save() # Aquí se guarda la instancia de CV con la nueva ruta relativa
        logger.info(f"CV de {persona.usuario.username} actualizado/creado con estado: {cv.processing_status}. Ruta FileField final guardada: {cv.archivo_cv.name}") 
        return True, "Datos de CV guardados/actualizados correctamente."
    except Exception as e:
        logger.error(f"Error al guardar CV de {persona.usuario.username}: {e}", exc_info=True)
        # Si falla el guardado, asegúrate de que el estado refleje el error
        cv.processing_status = EstadoDocumento.ERROR
        cv.rejection_reason = f"Error interno del servidor al guardar CV: {e}"
        # Solo guarda los campos de estado y razón, para evitar reintentar con el mismo problema que causó la excepción.
        cv.save(update_fields=['processing_status', 'rejection_reason', 'last_processed_at'])
        return False, f"Error al guardar los datos del CV: {e}"

# Función auxiliar para parsear y guardar datos de Certificado de Antecedentes
def process_certificate_data(persona, payload):
    logger.info(f"Procesando datos de Certificado de Antecedentes para RUT: {persona.usuario.username}")

    certificado, created = CertificadoAntecedentes.objects.get_or_create(persona=persona)

    # Actualizar la URL de GCS si viene en el payload
    if 'file_gcs_url' in payload:
        gcs_url_from_cf = payload['file_gcs_url']
        
        # ¡CAMBIO CRUCIAL AQUÍ! Usa la función auxiliar
        relative_path = get_gcs_relative_path_from_full_url(gcs_url_from_cf)
        
        if relative_path:
            certificado.archivo_certificado.name = relative_path
            logger.info(f"DEBUG_CF_PROCESS: URL de Certificado recibida de CF ('{gcs_url_from_cf}') asignada como ruta relativa: '{certificado.archivo_certificado.name}'")
        else:
            logger.error(f"DEBUG_CF_PROCESS: No se pudo determinar la ruta relativa para el Certificado de CF: '{gcs_url_from_cf}'. El archivo del certificado no será actualizado en el modelo.")
    else:
        logger.warning(f"DEBUG_CF_PROCESS: Payload de CF para Certificado no contiene 'file_gcs_url'. No se actualiza el archivo_certificado en el modelo.")

    # Guardar el JSON completo de la IA
    certificado.datos_analizados_ia = payload.get('extracted_data', {})
    
    # Actualizar estado de procesamiento y razón de rechazo
    certificado.processing_status = payload.get('processing_status', EstadoDocumento.ERROR)
    certificado.rejection_reason = payload.get('rejection_reason')
    certificado.last_processed_at = timezone.now()

    try:
        certificado.full_clean()
        certificado.save()
        logger.info(f"Certificado de {persona.usuario.username} actualizado/creado con estado: {certificado.processing_status}. Ruta FileField final guardada: {certificado.archivo_certificado.name}")
        return True, "Datos de certificado guardados/actualizados correctamente."
    except Exception as e:
        logger.error(f"Error al guardar Certificado de {persona.usuario.username}: {e}", exc_info=True)
        # Si falla el guardado, asegúrate de que el estado refleje el error
        certificado.processing_status = EstadoDocumento.ERROR
        certificado.rejection_reason = f"Error interno del servidor al guardar Certificado: {e}"
        # Solo guarda los campos de estado y razón, para evitar reintentar con el mismo problema que causó la excepción.
        certificado.save(update_fields=['processing_status', 'rejection_reason', 'last_processed_at'])
        return False, f"Error al guardar los datos del certificado: {e}"


@csrf_exempt 
@require_POST 
def receive_document_data(request):
    logger.info("Solicitud recibida en receive_document_data")
    try:
        data = json.loads(request.body)
        logger.debug(f"Payload recibido: {data}")

        rut = data.get('rut')
        document_type = data.get('document_type') # 'cv' o 'certificate'
        
        if not rut:
            logger.error("Falta 'rut' en el payload.")
            return JsonResponse({'status': 'error', 'message': 'Falta el RUT del usuario.'}, status=400)
        
        if not document_type:
            logger.error("Falta 'document_type' en el payload.")
            return JsonResponse({'status': 'error', 'message': 'Falta el tipo de documento.'}, status=400)

        # Buscar el usuario y su PersonaNatural.
        try:
            usuario = Usuario.objects.get(username=rut)
            persona = get_object_or_404(PersonaNatural, usuario=usuario)
        except Usuario.DoesNotExist:
            logger.error(f"Usuario con RUT {rut} no encontrado.")
            return JsonResponse({'status': 'error', 'message': f'Usuario con RUT {rut} no encontrado.'}, status=404)
        except PersonaNatural.DoesNotExist:
            logger.error(f"PersonaNatural para usuario con RUT {rut} no encontrada.")
            return JsonResponse({'status': 'error', 'message': f'Persona Natural para el usuario {rut} no encontrada.'}, status=404)
        
        success = False
        message = ""

        with transaction.atomic(): 
            if document_type == 'cv':
                success, message = process_cv_data(persona, data)
            elif document_type == 'CERTIFICADO_ANTECEDENTES': # Asegúrate de que el string coincida con lo que envía la CF
                success, message = process_certificate_data(persona, data)
            else:
                logger.error(f"Tipo de documento no válido: {document_type}")
                return JsonResponse({'status': 'error', 'message': 'Tipo de documento no válido.'}, status=400)
        
        if success:
            return JsonResponse({'status': 'success', 'message': message}, status=200)
        else:
            return JsonResponse({'status': 'error', 'message': message}, status=500)

    except json.JSONDecodeError:
        logger.error("Error al decodificar JSON.")
        return JsonResponse({'status': 'error', 'message': 'Solicitud JSON inválida.'}, status=400)
    except Exception as e:
        logger.exception("Error inesperado en receive_document_data:") 
        return JsonResponse({'status': 'error', 'message': f'Error interno del servidor: {e}'}, status=500)
