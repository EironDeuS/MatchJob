# gestionOfertas/urls.py

from django.urls import path

from gestionOfertas.forms import CustomPasswordResetForm
from django.contrib.auth import views as auth_views
from . import views

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
    path('crear_oferta/', views.crear_oferta, name='crear_oferta'),
    path('editar-oferta/<int:oferta_id>/', views.editar_oferta, name='editar_oferta'),
    path('eliminar-oferta/<int:oferta_id>/', views.eliminar_oferta, name='eliminar_oferta'),
    path('oferta/<int:oferta_id>/postular/', views.realizar_postulacion, name='realizar_postulacion'),
    path('cambiar_estado_postulacion/<int:postulacion_id>/', views.cambiar_estado_postulacion, name='cambiar_estado_postulacion'),
    path('ranking/', views.ranking_usuarios, name='ranking'),
    path('mapa/', views.mapa, name='mapa'),
    path('perfil/modo-urgente/', views.actualizar_modo_urgente, name='actualizar_modo_urgente'),
    path('password_reset/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('password_reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('ofertas-urgentes/', views.OfertasUrgentesView.as_view(), name='ofertas_urgentes'),
    
    # path('ofertas/<int:pk>/editar/', views.editar_oferta, name='editar_oferta'),
    # path('ofertas/<int:pk>/', views.detalle_oferta, name='detalle_oferta'),
    # path('ofertas/', views.listar_ofertas, name='listar_ofertas'),
]