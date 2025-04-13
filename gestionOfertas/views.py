from django.shortcuts import render
from .models import PersonaNatural
from .models import OfertaTrabajo, Categoria
from django.db.models import Q
from django.core.paginator import Paginator

# Vista para la página de inicio
def inicio(request):
    return render(request, 'gestionOfertas/inicio.html')

# Vista para la página Mis Datos
def mi_perfil(request):
    try:
        # Obtener el primer registro de PersonaNatural
        persona = PersonaNatural.objects.first()
        
        # Verificar si existe al menos un registro
        if not persona:
            raise PersonaNatural.DoesNotExist
            
        return render(request, 'gestionOfertas/miperfil.html', {'persona': persona})
        
    except PersonaNatural.DoesNotExist:
        # Datos de ejemplo por si la tabla está vacía
        datos_ejemplo = 0
        return render(request, 'gestionOfertas/miperfil.html', {'persona': datos_ejemplo})


# Vista para la página Mis Datos
def base(request):
    return render(request, 'gestionOfertas/base.html')
