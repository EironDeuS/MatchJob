from django.shortcuts import render
from .models import PersonaNatural, OfertaTrabajo, Categoria
from django.db.models import Q  # Para búsquedas avanzadas


# Vista para la página de inicio
def inicio(request):
    # Obtener parámetros de filtrado del request
    busqueda = request.GET.get('q', '')
    categoria_id = request.GET.get('categoria', '')
    
    # Consulta base - todas las ofertas activas
    ofertas = OfertaTrabajo.objects.all()
    
    # Aplicar filtro de búsqueda si existe
    if busqueda:
        ofertas = ofertas.filter(
            Q(nombre__icontains=busqueda) | 
            Q(descripcion__icontains=busqueda)
        )
    
    # Aplicar filtro por categoría si existe
    if categoria_id:
        ofertas = ofertas.filter(categoria_id=categoria_id)
    
    context = {
        'ofertas': ofertas,
        'categorias': Categoria.objects.all(),
        'busqueda_actual': busqueda,
        'categoria_actual': categoria_id if categoria_id else ''
    }
    return render(request, 'gestionOfertas/inicio.html', context)

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
