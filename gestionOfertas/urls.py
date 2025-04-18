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
    path('oferta/<int:oferta_id>/', views.detalle_oferta, name='detalle_oferta'),
    path('crear_oferta/', views.crear_oferta, name='crear_oferta'),
]