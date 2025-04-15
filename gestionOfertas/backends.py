from django.contrib.auth.backends import BaseBackend
from gestionOfertas.models import Usuario
from django.contrib.auth.hashers import check_password

class AutenticacionPorRUTBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            user = Usuario.objects.get(username=username)  # Aquí usás el RUT como username
            if check_password(password, user.password):	
                return user
        except Usuario.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Usuario.objects.get(pk=user_id)
        except Usuario.DoesNotExist:
            return None
