# gestionOfertas/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('', views.inicio , name='inicio'),
    path('miperfil/', views.mi_perfil, name='miperfil'),
    path('base/', views.base, name='base'),
    path('iniciar_sesion/', views.iniciar_sesion, name='iniciar_sesion'),
    path('registro/', views.registro, name='registro'),
    path('salir/', views.salir, name='salir'),
    path('demo-valoracion/<int:postulacion_id>/', views.demo_valoracion, name='demo_valoracion'),
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
    # path('ofertas/<int:pk>/editar/', views.editar_oferta, name='editar_oferta'),
    # path('ofertas/<int:pk>/', views.detalle_oferta, name='detalle_oferta'),
    # path('ofertas/', views.listar_ofertas, name='listar_ofertas'),
]