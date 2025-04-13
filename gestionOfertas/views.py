from django.shortcuts import render

# Vista para la página de inicio
def inicio(request):
    return render(request, 'gestionOfertas/inicio.html')

# Vista para la página Mis Datos
def mis_datos(request):
    return render(request, 'gestionOfertas/miperfil.html')

# Vista para la página Mis Datos
def base(request):
    return render(request, 'gestionOfertas/base.html')
