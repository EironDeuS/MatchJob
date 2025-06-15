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

def registro(request):
    # Redirigir si el usuario ya está autenticado
    if request.user.is_authenticated:
        messages.info(request, "Ya has iniciado sesión. No puedes registrarte de nuevo.")
        return redirect('miperfil') 

    if request.method == 'POST':
        form = RegistroForm(request.POST, request.FILES)
        logger.debug(f"POST recibido. request.FILES: {request.FILES}")

        if form.is_valid():
            logger.debug("Formulario VÁLIDO.")
            rut = form.cleaned_data['username'] # El RUT es el username

            try:
                # --- Usar una transacción atómica para asegurar que todo se guarda o nada ---
                with transaction.atomic():
                    # 1. Crear y guardar el usuario
                    # form.save() usa el método `save` que definiste en tu RegistroForm
                    # Este método crea la instancia de Usuario y la guarda en la BD.
                    usuario = form.save(commit=True) 
                    logger.info(f"Usuario creado: {usuario.username} (ID: {usuario.pk})")

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
                                cv_filename_in_gcs = f'cvs/{usuario.username}_CV_{uuid.uuid4().hex}{file_extension}'
                                
                                # Guarda el archivo en GCS usando default_storage. Esto devuelve la ruta relativa.
                                cv_gcs_relative_path = default_storage.save(cv_filename_in_gcs, cv_file)
                                
                                # Crea la instancia de CV asociada a la persona_natural
                                CV.objects.create(
                                    persona=persona_natural, # Asociado a la instancia de PersonaNatural
                                    archivo_cv=cv_gcs_relative_path # ASIGNAR LA RUTA RELATIVA AL FileField
                                )
                                messages.info(request, 'CV subido exitosamente y en proceso de análisis.')
                                logger.info(f"CV subido en registro para {usuario.username}: {cv_gcs_relative_path}")
                            except Exception as e:
                                logger.error(f"Error al subir CV durante el registro para {usuario.username}: {e}", exc_info=True)
                                messages.warning(request, 'Hubo un problema al subir tu CV. Puedes subirlo después en tu perfil.')
                        else:
                            logger.info(f"No se proporcionó CV para {usuario.username}.")

                        # --- Lógica para Certificado de Antecedentes, asociada a persona_natural ---
                        certificado_file = request.FILES.get('certificado_pdf') # Obtén el objeto UploadedFile del formulario
                        if certificado_file:
                            try:
                                file_extension = os.path.splitext(certificado_file.name)[1]
                                # Usar un UUID para el nombre del archivo para evitar colisiones
                                certificado_filename_in_gcs = f'certificados/{usuario.username}_CERT_{uuid.uuid4().hex}{file_extension}'

                                # Guarda el archivo en GCS usando default_storage. Esto devuelve la ruta relativa.
                                certificado_gcs_relative_path = default_storage.save(certificado_filename_in_gcs, certificado_file)
                                
                                # Crea la instancia de CertificadoAntecedentes asociada a la persona_natural
                                CertificadoAntecedentes.objects.create(
                                    persona=persona_natural, # Asociado a la instancia de PersonaNatural
                                    certificado_archivo=certificado_gcs_relative_path, # ASIGNAR LA RUTA RELATIVA AL FileField
                                    esta_verificado=False # Por defecto, no verificado
                                )
                                messages.info(request, 'Certificado de antecedentes subido y pendiente de verificación.')
                                logger.info(f"Certificado subido en registro para {usuario.username}: {certificado_gcs_relative_path}")
                            except Exception as e:
                                logger.error(f"Error al subir Certificado durante el registro para {usuario.username}: {e}", exc_info=True)
                                messages.warning(request, 'Hubo un problema al subir tu Certificado de Antecedentes. Puedes subirlo después en tu perfil.')
                        else:
                            logger.info(f"No se proporcionó certificado para {usuario.username}.")
                        
                    elif tipo_usuario == 'empresa':
                        # Validar RUT de empresa antes de crear la instancia
                        # Esto es una redundancia si ya lo tienes en clean(), pero no está de más
                        # si quieres una validación explícita aquí también (aunque clean() es mejor).
                        # Asegúrate de que `validar_rut_empresa` esté importada o definida.
                        # Asumiendo que `validar_rut_empresa` está en el ámbito o importado.
                        
                        # Descomenta y ajusta si necesitas re-validar aquí, sino, confía en form.clean()
                        # resultado_rut_empresa = validar_rut_empresa(rut)
                        # if not resultado_rut_empresa['valida']:
                        #     messages.error(request, f"❌ El RUT ingresado no es válido como empresa: {resultado_rut_empresa.get('mensaje')}")
                        #     raise ValidationError("RUT de empresa inválido.") # Forzamos la transacción a fallar

                        # Crea la Empresa, enlazándola al usuario recién creado
                        empresa = Empresa.objects.create(
                            usuario=usuario, # Pasa la instancia de usuario recién creada
                            nombre_empresa=form.cleaned_data.get('nombre_empresa'),
                            razon_social=form.cleaned_data.get('razon_social'),
                            giro=form.cleaned_data.get('giro')
                        )
                        logger.info(f"Perfil Empresa creado para {usuario.username} (ID: {empresa.pk})")
                        # Si las empresas también suben archivos, la lógica iría aquí,
                        # asociada a la instancia 'empresa'.

                # Si todo dentro de la transacción atómica fue exitoso
                login(request, usuario) # Loguear al usuario automáticamente
                messages.success(request, "¡Registro exitoso! Tu cuenta ha sido creada y has iniciado sesión.")
                return redirect(reverse('miperfil')) # Redirige al perfil del usuario

            except IntegrityError as e:
                # Este error se captura si hay una violación de restricción de DB (ej. OneToOneField duplicado)
                # que no fue capturada por la validación del formulario.
                logger.error(f"IntegrityError durante el registro para {rut}: {e}", exc_info=True)
                messages.error(request, "Error de registro: Este RUT o correo electrónico ya está en uso. Si el problema persiste, contacta a soporte.")
                # No necesitamos borrar el usuario aquí, ya que transaction.atomic() lo revierte
                # si el error ocurre dentro del bloque 'with'. Si el error ocurre antes de `usuario = form.save()`,
                # el usuario nunca fue creado.
                return render(request, 'gestionOfertas/registro.html', {'form': form})
            except ValidationError as e:
                # Captura las ValidationError lanzadas por tus validaciones o las del form
                logger.warning(f"ValidationError durante el registro para {rut}: {e.message}", exc_info=True)
                messages.error(request, f"Error de validación: {e.message}")
                # Asegúrate de que los errores se muestren en el formulario si es necesario
                # for message in e.messages: messages.error(request, message) # Si ValidationError tiene múltiples mensajes
                return render(request, 'gestionOfertas/registro.html', {'form': form})
            except Exception as e:
                # Captura cualquier otro error inesperado
                logger.exception(f"Error inesperado durante el registro de usuario {rut}: {e}")
                messages.error(request, "Ocurrió un error inesperado durante el registro. Por favor, inténtalo de nuevo.")
                # Aquí, si el error ocurrió después de `usuario = form.save()` pero fuera de la transacción,
                # o si la transacción falló por una razón inesperada, el usuario no debería persistir.
                # transaction.atomic() debería manejar esto.
                return render(request, 'gestionOfertas/registro.html', {'form': form})
        else:
            # Si el formulario no es válido, los errores se mostrarán automáticamente en la plantilla
            # o puedes iterar sobre ellos para mostrarlos con messages.error
            logger.warning(f"Formulario de registro NO VÁLIDO. Errores: {form.errors.as_json()}")
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
            # Iterar y mostrar errores específicos del formulario
            for field, errors in form.errors.items():
                for error in errors:
                    # Usar .label para un mensaje más amigable
                    field_label = form.fields[field].label if field in form.fields else field
                    messages.error(request, f"Error en '{field_label}': {error}")
    else:
        form = RegistroForm()
    
    return render(request, 'gestionOfertas/registro.html', {'form': form})

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

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils.translation import gettext as _
from django.conf import settings
import googlemaps
from django.db import transaction
from .forms import OfertaTrabajoForm

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
            postulacion.save() # Esto debería actualizar fecha_contratacion si el estado cambia a 'contratado'

            messages.success(request, f"Estado de la postulación actualizado a '{nuevo_estado}'.")

            # --- Lógica de Contratación (Envío de Correo y PDF adjunto) ---
            if nuevo_estado == 'contratado' and estado_original != 'contratado':
                try:
                    # Formatear la fecha de contratación directamente en Python
                    # %d: día del mes como número decimal
                    # %B: Nombre completo del mes (localizado)
                    # %Y: Año con siglo como número decimal
                    fecha_contratacion_formateada = postulacion.fecha_contratacion.strftime("%d de %B de %Y")
                    print(f"DEBUG: Fecha de contratación formateada en Python: {fecha_contratacion_formateada}") # Debug para verificar

                    # 1. Preparar datos para el template del correo Y el PDF
                    contexto = {
                        'postulacion': postulacion,
                        'postulante': postulacion.persona, 
                        'oferta': postulacion.oferta,
                        'empresa': postulacion.oferta.empresa, 
                        'fecha_actual': timezone.now().strftime("%d-%m-%Y"), 
                        'url_sitio': request.build_absolute_uri('/'),
                        'fecha_contratacion_formateada': fecha_contratacion_formateada, # ¡Nuevo campo para el template!
                    }

                    # 2. Renderizar el template HTML del correo (el cuerpo del email)
                    html_content = render_to_string('gestionOfertas/emails/confirmacion_contratacion.html', contexto)
                    text_content = strip_tags(html_content)

                    # 3. Generar el PDF
                    template_pdf = get_template('gestionOfertas/pdfs/carta_confirmacion_contratacion.html')
                    html_pdf = template_pdf.render(contexto)

                    result_file = io.BytesIO()

                    pisa_status = pisa.CreatePDF(
                        html_pdf,
                        dest=result_file,
                        encoding='utf-8' 
                    )

                    if pisa_status.err:
                        raise Exception(f"Error al generar el documento PDF: {pisa_status.err}")

                    # 4. Configurar y enviar el correo electrónico con el PDF adjunto
                    email = EmailMultiAlternatives(
                        subject=f"¡Felicitaciones! Has sido contratado/a para {postulacion.oferta.nombre}",
                        body=text_content, 
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        to=[postulacion.persona.usuario.correo] 
                    )
                    email.attach_alternative(html_content, "text/html")

                    email.attach(
                        f"Confirmacion_Contratacion_{postulacion.persona.usuario.username}_{postulacion.oferta.id}.pdf",
                        result_file.getvalue(), 
                        'application/pdf' 
                    )

                    email.send() 

                    messages.info(request, "Correo de confirmación de contratación con documento adjunto enviado.")

                except Exception as e:
                    messages.error(request, f"Error al procesar la confirmación de contratación: {e}")
                    logging.getLogger(__name__).exception("Error en la lógica de contratación:")

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

    if request.method == 'POST':
        form = EditarPerfilPersonaForm(
            request.POST,
            request.FILES,
            instance=persona_natural,
            usuario_actual=usuario
        )
        if form.is_valid():
            form.save() # Guarda los campos de PersonaNatural

            usuario.correo = form.cleaned_data.get('correo')
            usuario.telefono = form.cleaned_data.get('telefono')
            usuario.direccion = form.cleaned_data.get('direccion')
            usuario.save()

            # --- Lógica para CV ---
            cv_file = request.FILES.get('cv_archivo')
            if cv_file:
                cv_instance, created = CV.objects.get_or_create(persona=persona_natural)
                
                # PASO 1: BORRAR EL CV ANTERIOR SI EXISTE EN GCS
                if cv_instance.archivo_cv and cv_instance.archivo_cv.name:
                    old_cv_path = cv_instance.archivo_cv.name
                    if default_storage.exists(old_cv_path): # Verificar si el archivo existe en GCS
                        try:
                            default_storage.delete(old_cv_path)
                            logger.info(f"DEBUG_UPLOAD: CV anterior '{old_cv_path}' borrado exitosamente de GCS.")
                        except Exception as e:
                            logger.error(f"Error al borrar CV anterior '{old_cv_path}': {e}", exc_info=True)
                    else:
                        logger.warning(f"DEBUG_UPLOAD: CV anterior '{old_cv_path}' no encontrado en GCS para borrar. Posiblemente ya borrado o ruta incorrecta.")

                # PASO 2: GENERAR UN NUEVO NOMBRE DE ARCHIVO ÚNICO CON UUID
                file_extension = os.path.splitext(cv_file.name)[1]
                cv_filename_in_gcs = f'cvs/{usuario.username}_CV_{uuid.uuid4().hex}{file_extension}' # <-- VOLVEMOS A USAR UUID
                
                logger.info(f"DEBUG_UPLOAD: Intentando guardar nuevo CV: '{cv_filename_in_gcs}'")
                logger.info(f"DEBUG_UPLOAD: Tamaño del archivo CV: {cv_file.size} bytes")
                
                try:
                    # PASO 3: Sube el nuevo archivo a GCS
                    cv_gcs_relative_path = default_storage.save(cv_filename_in_gcs, cv_file)
                    logger.info(f"DEBUG_UPLOAD: default_storage.save para CV devolvió la ruta: '{cv_gcs_relative_path}'")
                    
                    # PASO 4: Actualiza la instancia del modelo CV con la NUEVA RUTA ÚNICA
                    cv_instance.archivo_cv.name = cv_gcs_relative_path
                    cv_instance.save() # Guarda la instancia del modelo, que ahora tiene la ruta correcta.
                    
                    messages.success(request, 'CV subido correctamente y en proceso de análisis por IA.')
                    logger.info(f"CV para usuario {usuario.username} subido correctamente.")
                except Exception as e:
                    messages.error(request, f'Error al subir el CV: {e}')
                    logger.error(f"Error al subir CV para {usuario.username}: {e}", exc_info=True)

            # --- Lógica para Certificado de Antecedentes ---
            certificado_file = request.FILES.get('certificado_pdf')
            if certificado_file:
                certificado_instance, created = CertificadoAntecedentes.objects.get_or_create(persona=persona_natural)
                
                # PASO 1: BORRAR EL CERTIFICADO ANTERIOR SI EXISTE EN GCS
                if certificado_instance.certificado_archivo and certificado_instance.certificado_archivo.name:
                    old_certificado_path = certificado_instance.certificado_archivo.name
                    if default_storage.exists(old_certificado_path): 
                        try:
                            default_storage.delete(old_certificado_path)
                            logger.info(f"DEBUG_UPLOAD: Certificado anterior '{old_certificado_path}' borrado exitosamente de GCS.")
                        except Exception as e:
                            logger.error(f"Error al borrar Certificado anterior '{old_certificado_path}': {e}", exc_info=True)
                    else:
                        logger.warning(f"DEBUG_UPLOAD: Certificado anterior '{old_certificado_path}' no encontrado en GCS para borrar. Posiblemente ya borrado o ruta incorrecta.")

                # PASO 2: GENERAR UN NUEVO NOMBRE DE ARCHIVO ÚNICO CON UUID
                file_extension = os.path.splitext(certificado_file.name)[1]
                certificado_filename_in_gcs = f'certificados/{usuario.username}_CERT_{uuid.uuid4().hex}{file_extension}' # <-- VOLVEMOS A USAR UUID

                logger.info(f"DEBUG_UPLOAD: Intentando guardar nuevo Certificado: '{certificado_filename_in_gcs}'")
                logger.info(f"DEBUG_UPLOAD: Tamaño del archivo Certificado: {certificado_file.size} bytes")

                try:
                    # PASO 3: Sube el nuevo archivo a GCS
                    certificado_gcs_relative_path = default_storage.save(certificado_filename_in_gcs, certificado_file)
                    logger.info(f"DEBUG_UPLOAD: default_storage.save para Certificado devolvió la ruta: '{certificado_gcs_relative_path}'")
                    
                    # PASO 4: Actualiza la instancia del modelo Certificado con la NUEVA RUTA ÚNICA
                    certificado_instance.certificado_archivo.name = certificado_gcs_relative_path
                    certificado_instance.esta_verificado = False
                    certificado_instance.save()

                    messages.success(request, 'Certificado de antecedentes subido correctamente y en proceso de análisis por IA.')
                    logger.info(f"Nuevo Certificado para usuario {usuario.username} subido a GCS: {certificado_gcs_relative_path}")
                except Exception as e:
                    messages.error(request, f'Error al subir el certificado: {e}')
                    logger.error(f"Error al subir certificado para {usuario.username}: {e}", exc_info=True)

            messages.success(request, 'Perfil actualizado correctamente.')
            return redirect('miperfil')
        else:
            messages.error(request, 'Error al actualizar el perfil. Por favor, revisa los campos.')
            logger.warning(f"Errores en EditarPerfilPersonaForm para {usuario.username}: {form.errors.as_json()}")
    else:
        form = EditarPerfilPersonaForm(
            instance=persona_natural,
            usuario_actual=usuario
        )

    cv_existente = getattr(persona_natural, 'cv', None)
    certificado_existente = getattr(persona_natural, 'certificado_antecedentes', None)

    context = {
        'form': form,
        'persona_natural': persona_natural,
        'cv': cv_existente,
        'certificado': certificado_existente,
        'MEDIA_URL': settings.MEDIA_URL
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
        if usuario_perfil.tipo_usuario == 'empresa':
            postulaciones = Postulacion.objects.filter(
                oferta__creador=usuario_perfil,
                estado='finalizado'
            ).select_related('persona', 'oferta')
        elif usuario_perfil.tipo_usuario == 'persona':
            postulaciones = usuario_perfil.personanatural.postulaciones.filter(
                estado='finalizado'
            ).select_related('oferta', 'oferta__creador')
        else:
            postulaciones = []

        for postulacion in postulaciones:
            # Verificar si ya existe una valoración para esta postulación
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

import json
import datetime
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

# Configurar el logger
logger = logging.getLogger(__name__)

# Función auxiliar para formatear el RUT como se guarda en la DB
def format_rut_for_db_lookup(rut_sin_guion):
    """
    Formatea un RUT sin guion (ej. '187847419') a un RUT con guion (ej. '18784741-9')
    asumiendo que el último dígito es el verificador.
    """
    if len(rut_sin_guion) > 1:
        return rut_sin_guion[:-1] + '-' + rut_sin_guion[-1].upper()
    return rut_sin_guion # O manejar un error si el RUT es demasiado corto


@csrf_exempt
@require_POST
def receive_cv_data(request):
    """
    Vista para recibir y procesar los datos del CV de la Cloud Function.
    """
    logger.info("--------------------------------------------------")
    logger.info(f"[{datetime.datetime.now()}] Solicitud POST recibida en /api/cv-data-receiver/")
    logger.info(f"Método de solicitud: {request.method}")

    try:
        request_body_str = request.body.decode('utf-8')
        logger.info(f"Cuerpo de la solicitud POST recibido (RAW): {request_body_str[:500]}...")

        data = json.loads(request_body_str) # JSON principal que viene de la IA
        logger.info("Cuerpo de la solicitud POST recibido (JSON Parsed).")

        # Extraer los campos clave que la IA DEBE ENVIAR
        user_rut_raw = data.get('user_rut') # Usar 'user_rut' como identificador único
        cv_gcs_url = data.get('cv_gcs_url') # Esto es "static/cvs/..."
        extracted_cv_data = data.get('extracted_data') # Este es el JSON grande con toda la info del CV

        if not user_rut_raw or not cv_gcs_url or not extracted_cv_data:
            logger.error(f"Datos incompletos en el JSON de la IA. user_rut={user_rut_raw}, cv_gcs_url={cv_gcs_url}, extracted_data_present={bool(extracted_cv_data)}")
            return JsonResponse({'error': 'Missing required data (user_rut, cv_gcs_url, or extracted_data)'}, status=400)

        # --- APLICAR EL FORMATO CORRECTO AL RUT PARA LA BÚSQUEDA EN LA DB ---
        user_rut_for_db = format_rut_for_db_lookup(user_rut_raw)
        logger.info(f"RUT recibido (sin guion): {user_rut_raw}, RUT formateado para DB: {user_rut_for_db}")

        # --- CORRECCIÓN CLAVE PARA ELIMINAR 'static/static/' ---
        # Si la URL de GCS ya viene con 'static/', la eliminamos para evitar la doble prefijación
        # ya que el almacenamiento configurado en settings.py (STORAGES["default"]["OPTIONS"]["location"] = 'static')
        # ya añade 'static/' a la URL base.
        clean_cv_gcs_url = cv_gcs_url
        if cv_gcs_url and cv_gcs_url.startswith('static/'):
            clean_cv_gcs_url = cv_gcs_url[len('static/'):]
            logger.info(f"URL de GCS limpiada: de '{cv_gcs_url}' a '{clean_cv_gcs_url}'")
        # --- FIN DE LA CORRECCIÓN CLAVE ---

        # Buscar la PersonaNatural por el RUT formateado para la DB (tu lógica original)
        try:
            persona_natural = PersonaNatural.objects.get(usuario__username=user_rut_for_db)
            logger.info(f"PersonaNatural encontrada para el RUT: {user_rut_for_db}")
        except PersonaNatural.DoesNotExist:
            logger.error(f"PersonaNatural con RUT {user_rut_for_db} (formateado) no encontrada.")
            return JsonResponse({'error': f'PersonaNatural con RUT {user_rut_raw} no encontrada.'}, status=404)
        except Usuario.DoesNotExist: # Se mantiene tu bloque original para Usuario.DoesNotExist
            logger.error(f"Usuario con username (RUT) {user_rut_for_db} no encontrado para la PersonaNatural.")
            return JsonResponse({'error': f'Usuario con RUT {user_rut_raw} no encontrado.'}, status=404)

        # Usamos transaction.atomic() para asegurar que la operación es atómica:
        # o se guarda todo el CV o no se guarda nada si hay un error.
        with transaction.atomic():
            # Crear o actualizar la entrada principal del CV.
            # Los campos `nombre_completo`, `email_contacto`, `resumen_profesional`
            # se asignan al *modelo CV*, NO al modelo PersonaNatural o Usuario.
            cv_instance, created = CV.objects.update_or_create(
                persona=persona_natural, # Vincula el CV a la PersonaNatural
                defaults={
                    'archivo_cv': clean_cv_gcs_url, # <--- ¡USAR LA URL LIMPIA AQUÍ!
                    'datos_analizados_ia': extracted_cv_data, # Aquí se guarda TODO el JSON extraído
                    # Campos de resumen que se guardan en el modelo CV, NO en el perfil del usuario:
                    'nombre_completo': extracted_cv_data.get('datos_personales', {}).get('nombre_completo'),
                    'email_contacto': extracted_cv_data.get('datos_personales', {}).get('email'),
                    'resumen_profesional': extracted_cv_data.get('resumen_ejecutivo', '')
                }
            )

            if created:
                logger.info(f"Nuevo CV principal creado para {user_rut_for_db} con datos de IA.")
            else:
                logger.info(f"CV principal actualizado para {user_rut_for_db} con datos de IA.")

            # --- SE HA ELIMINADO LA LÓGICA DE ACTUALIZACIÓN DIRECTA DE DATOS EN
            #     LOS MODELOS `PersonaNatural` Y `Usuario` AQUÍ.
            #     Estos campos (nombres, apellidos, fecha_nacimiento, correo, telefono)
            #     NO se sobrescriben con la información del CV.
            #     Si necesitas detallar la experiencia, educación, etc.,
            #     debes hacerlo creando/actualizando modelos relacionados que apunten a `cv_instance`
            #     (o a `persona_natural` si lo modelaste así, pero que representen los datos del CV
            #     y no los datos maestros del perfil del usuario).

            # Ejemplo (comentado) de cómo podrías procesar los detalles del CV
            # en modelos relacionados al CV, si los tienes definidos:
            # from tu_app.models import ExperienciaLaboral, Educacion, HabilidadCV, IdiomaCV # Importa tus modelos de CV detallados si existen

            # # Opcional: Borrar datos previos del CV para evitar duplicados si es una actualización
            # # y si quieres una única versión de los detalles del CV
            # ExperienciaLaboral.objects.filter(cv=cv_instance).delete()
            # Educacion.objects.filter(cv=cv_instance).delete()
            # # etc.

            # # Procesar experiencia laboral (ejemplo)
            # for exp_data in extracted_cv_data.get('experiencia_laboral', []):
            #     # Crea una nueva instancia de ExperienciaLaboral vinculada a este CV
            #     ExperienciaLaboral.objects.create(
            #         cv=cv_instance, # Asegúrate de vincularlo al modelo CV
            #         puesto=exp_data.get('puesto'),
            #         empresa=exp_data.get('empresa'),
            #         ciudad=exp_data.get('ciudad'),
            #         pais=exp_data.get('pais'),
            #         fecha_inicio=exp_data.get('fecha_inicio'), # Asegúrate de que el formato de fecha sea correcto (YYYY-MM-DD)
            #         fecha_fin=exp_data.get('fecha_fin'),
            #         actualmente_aqui=exp_data.get('actualmente_aqui'),
            #         descripcion_logros_responsabilidades=exp_data.get('descripcion_logros_responsabilidades'),
            #         # ... otros campos ...
            #     )

            # # Repite la lógica para Educacion, Habilidades, Idiomas, etc.
            # # Siempre vinculando las instancias creadas a `cv_instance`.

            logger.info("Datos del CV procesados y guardados en JSONField (y posiblemente modelos detallados asociados al CV).")
            logger.info("--------------------------------------------------")
            return JsonResponse({'status': 'success', 'message': 'CV data processed and saved successfully'}, status=200)

    except json.JSONDecodeError as e:
        logger.error(f"Error: JSON inválido recibido. Detalles: {e}")
        # Intentar loguear el cuerpo completo si es un JSON inválido y no muy grande
        request_body_for_log = request_body_str if len(request_body_str) < 1000 else request_body_str[:1000] + "..."
        logger.error(f"Cuerpo de la solicitud (sin JSON válido): {request_body_for_log}")
        return JsonResponse({'error': 'Invalid JSON format', 'details': str(e)}, status=400)
    except Exception as e:
        # Intenta obtener el RUT para el log de errores inesperados
        # Es necesario asegurar que 'data' esté definido antes de intentar acceder a ella
        user_rut_for_log = data.get('user_rut', 'N/A') if 'data' in locals() else 'N/A'
        logger.exception(f"Error inesperado al procesar y guardar datos del CV para user_rut: {user_rut_for_log}. Detalles: {e}")
        return JsonResponse({'error': f'Internal Server Error: {str(e)}'}, status=500)
    
@login_required
@require_POST
def subir_certificado_antecedentes(request):
    """
    Vista para que un usuario suba su certificado de antecedentes.
    Si ya existe uno, lo reemplaza.
    Guarda el archivo en GCS y crea/actualiza una entrada en CertificadoAntecedentes.
    """
    if not request.user.is_authenticated:
        messages.error(request, "Debes iniciar sesión para subir un certificado.")
        return redirect('iniciar_sesion')

    archivo_certificado = request.FILES.get('certificado_pdf')

    if not archivo_certificado:
        messages.error(request, "No se ha seleccionado ningún archivo PDF.")
        return redirect('miperfil')

    if not archivo_certificado.name.lower().endswith('.pdf'):
        messages.error(request, "El archivo debe ser un PDF.")
        return redirect('miperfil')

    try:
        with transaction.atomic(): # Esto asegura que si algo falla, no se queden datos a medio camino
            # 1. Intentar obtener el certificado existente
            existing_certificado = None
            try:
                existing_certificado = CertificadoAntecedentes.objects.get(usuario=request.user)
            except CertificadoAntecedentes.DoesNotExist:
                pass # No hay certificado existente, se creará uno nuevo
            except CertificadoAntecedentes.MultipleObjectsReturned:
                # Esto no debería ocurrir con OneToOneField, pero es una buena práctica de log
                logger.error(f"Múltiples CertificadoAntecedentes encontrados para el usuario {request.user.username}. Esto indica un problema con la DB.")
                # Aquí podrías decidir si eliminar todos y crear uno nuevo, o solo el más reciente.
                # Para simplificar, vamos a eliminar el que se encuentre primero si esto ocurriera.
                CertificadoAntecedentes.objects.filter(usuario=request.user).delete()
                existing_certificado = None


            # 2. Si existe un certificado anterior, borrarlo (esto también borrará el archivo de GCS)
            if existing_certificado:
                # El método delete de CertificadoAntecedentes se encargará de borrar el archivo de GCS
                existing_certificado.delete() 
                logger.info(f"Certificado anterior de {request.user.username} eliminado de DB y GCS.")

            # 3. Generar un nombre de archivo único para GCS
            # Usamos el RUT del usuario en el nombre del archivo.
            user_rut = request.user.username.replace('.', '').replace('-', '') # Limpia el RUT
            timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
            # Usa una carpeta dedicada para certificados
            gcs_file_name = f"certificados/{user_rut}_{timestamp}_{archivo_certificado.name.replace(' ', '_')}"

            # 4. Guardar el nuevo archivo en GCS
            path_in_gcs = default_storage.save(gcs_file_name, archivo_certificado)
            gcs_url = default_storage.url(path_in_gcs) 
            logger.info(f"Nuevo certificado PDF {gcs_url} subido a GCS por {request.user.username}.")

            # 5. Crear (o recrear, si se borró el anterior) una nueva instancia de CertificadoAntecedentes
            certificado = CertificadoAntecedentes.objects.create(
                usuario=request.user,
                certificado_url=gcs_url,
                # datos_extraidos y esta_verificado se actualizarán por la Cloud Function
            )
            messages.success(request, "Certificado subido correctamente. El anterior ha sido reemplazado y el nuevo será procesado en breve.")
            logger.info(f"Nueva instancia de CertificadoAntecedentes creada para {request.user.username}. ID: {certificado.id}")

    except Exception as e:
        logger.error(f"Error al subir/reemplazar certificado para {request.user.username}: {e}", exc_info=True)
        messages.error(request, f"Hubo un error al subir el certificado: {e}")

    return redirect('miperfil')

# ... (receive_certificado_data - esta vista permanece igual) ...

@require_POST
def receive_certificado_data(request):
    """
    Endpoint que recibe datos de la Cloud Function después de procesar un certificado.
    Busca el certificado por su URL en GCS y actualiza los campos.
    """
    # En producción, añadir una clave API o token para seguridad
    if not settings.DEBUG: 
        # Implementar alguna forma de autenticación/validación aquí
        # (ej. token en el header, API key, IP whitelist)
        pass

    try:
        data = json.loads(request.body)
        certificado_gcs_url = data.get('certificado_gcs_url')
        extracted_data = data.get('extracted_data')
        user_rut = data.get('user_rut') # El RUT del usuario que subió el certificado

        if not certificado_gcs_url or not user_rut:
            logger.error(f"Datos incompletos recibidos para certificado: URL: {certificado_gcs_url}, RUT: {user_rut}")
            return JsonResponse({'error': 'Missing certificate_gcs_url or user_rut'}, status=400)

        try:
            usuario_instance = Usuario.objects.get(username=user_rut)
        except Usuario.DoesNotExist:
            logger.error(f"Usuario con RUT {user_rut} no encontrado para el certificado {certificado_gcs_url}.")
            return JsonResponse({'error': 'User not found for provided RUT'}, status=404)

        try:
            # Buscar el certificado usando OneToOneField:
            # Dado que es OneToOne, el usuario *tiene* un certificado, o no lo tiene.
            # No necesitamos buscar por URL si ya tenemos el usuario, pero es más seguro.
            certificado_instance = CertificadoAntecedentes.objects.get(
                usuario=usuario_instance,
                certificado_url=certificado_gcs_url # Esto valida que es el certificado correcto
            )
        except CertificadoAntecedentes.DoesNotExist:
            logger.error(f"CertificadoAntecedentes con URL {certificado_gcs_url} para usuario {user_rut} no encontrado en la DB para actualizar.")
            return JsonResponse({'error': 'CertificadoAntecedentes instance not found for update'}, status=404)
        except CertificadoAntecedentes.MultipleObjectsReturned:
            # Esto solo ocurriría si el OneToOneField se rompe, lo cual no debería pasar.
            logger.error(f"Múltiples CertificadoAntecedentes encontrados para usuario {user_rut}. Corregir OneToOneField.")
            return JsonResponse({'error': 'Multiple CertificadoAntecedentes instances found'}, status=500)


        certificado_instance.datos_extraidos = extracted_data
        certificado_instance.esta_verificado = True
        certificado_instance.save()

        logger.info(f"Certificado de {user_rut} (ID: {certificado_instance.id}) actualizado con datos de IA.")
        return JsonResponse({'status': 'success', 'message': 'Certificado data processed and saved successfully'}, status=200)

    except json.JSONDecodeError as e:
        logger.error(f"Error: JSON inválido recibido en receive_certificado_data. Detalles: {e}")
        return JsonResponse({'error': 'Invalid JSON format', 'details': str(e)}, status=400)
    except Exception as e:
        user_rut_for_log = data.get('user_rut', 'N/A') if 'data' in locals() else 'N/A'
        logger.exception(f"Error inesperado al procesar y guardar datos del certificado para user_rut: {user_rut_for_log}. Detalles: {e}")
        return JsonResponse({'error': f'Internal Server Error: {str(e)}'}, status=500)
