# gestionOfertas/urls.py

from django.urls import path

from gestionOfertas.forms import CustomPasswordResetForm
from django.contrib.auth import views as auth_views
from . import views
from django.conf import settings # <--- ¡Asegúrate de que esta línea esté aquí!
from django.conf.urls.static import static # <--- ¡Asegúrate de que esta línea esté aquí!



urlpatterns = [
    path('', views.inicio , name='inicio'),
    path('miperfil/', views.mi_perfil, name='miperfil'),
    path('perfil/<int:usuario_id>/', views.ver_perfil_publico, name='ver_perfil_publico'),
    path('base/', views.base, name='base'),
    path('iniciar_sesion/', views.iniciar_sesion, name='iniciar_sesion'),
    path('registro/', views.registro, name='registro'),
    path('salir/', views.salir, name='salir'),
    #path('demo-valoracion/<int:postulacion_id>/', views.demo_valoracion, name='demo_valoracion'),
    path('valoracion/<int:postulacion_id>/', views.historial_valoraciones, name='procesar_valoracion'),
    path('perfil/<int:usuario_id>/valoraciones/', views.historial_valoraciones, name='historial_valoraciones'),
    path('oferta/<int:oferta_id>/', views.detalle_oferta, name='detalle_oferta'),
    path('perfil/editar/', views.editar_perfil, name='editar_perfil'),
    path('mis_ofertas/', views.mis_ofertas, name='mis_ofertas'),
    path('ofertas/<int:oferta_id>/postulantes/', views.postulantes_por_oferta, name='postulantes_por_oferta'), #ultimo añadido
    path('crear_oferta/', views.crear_oferta, name='crear_oferta'),
    path('editar-oferta/<int:oferta_id>/', views.editar_oferta, name='editar_oferta'),
    path('eliminar-oferta/<int:oferta_id>/', views.eliminar_oferta, name='eliminar_oferta'),
    path('oferta/<int:oferta_id>/postular/', views.realizar_postulacion, name='realizar_postulacion'),
    path('mis-postulaciones/', views.mis_postulaciones_persona, name='mis_postulaciones_persona'),
    path('cambiar_estado_postulacion/<int:postulacion_id>/', views.cambiar_estado_postulacion, name='cambiar_estado_postulacion'),
    path('ranking/', views.ranking_usuarios, name='ranking'),
    path('mapa/', views.mapa_ofertas_trabajo, name='mapa'),
    path('api/ofertas-mapa/', views.api_ofertas_mapa, name='api_ofertas_mapa'),
    path('perfil/modo-urgente/', views.actualizar_modo_urgente, name='actualizar_modo_urgente'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('ofertas-urgentes/', views.ofertas_urgentes_view, name='ofertas_urgentes'),
    path('perfil/subir-muestra/', views.subir_muestra_trabajo, name='subir_muestra_trabajo'),
    path('muestra/eliminar/<int:muestra_id>/', views.eliminar_muestra_trabajo, name='eliminar_muestra_trabajo'),
    path('api/cv-data-receiver/', views.receive_cv_data, name='receive_cv_data'),

    # path('ofertas/<int:pk>/editar/', views.editar_oferta, name='editar_oferta'),
    # path('ofertas/<int:pk>/', views.detalle_oferta, name='detalle_oferta'),
    # path('ofertas/', views.listar_ofertas, name='listar_ofertas'),
]

# **¡IMPORTANTE!** Esto solo sirve archivos estáticos en desarrollo (cuando DEBUG=True).
# En producción, Cloud Run/GCS se encargarán de ellos.
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)  # <-- Añade esta línea

    # Si también sirves archivos de medios (uploaded files) en desarrollo:
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)