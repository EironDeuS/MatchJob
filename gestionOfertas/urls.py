# gestionOfertas/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('miperfil/', views.mis_datos, name='miperfil'),
    path('base/', views.base, name='base'),
]
