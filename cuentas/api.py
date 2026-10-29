from rest_framework.permissions import IsAdminUser

from core.api import ProtegidoViewSet

from .models import Usuario
from .serializers import UsuarioSerializer


class UsuarioViewSet(ProtegidoViewSet):
    queryset = Usuario.objects.order_by("username")
    serializer_class = UsuarioSerializer
    permission_classes = [IsAdminUser]
