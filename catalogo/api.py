from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from core.api import ProtegidoViewSet

from .models import Ambiente, Ficha, Programa, Sede
from .serializers import AmbienteSerializer, FichaSerializer, ProgramaSerializer, SedeSerializer


class LecturaOStaff(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.is_staff


class CatalogoViewSet(ProtegidoViewSet):
    permission_classes = [IsAuthenticated, LecturaOStaff]


class SedeViewSet(CatalogoViewSet):
    queryset = Sede.objects.all()
    serializer_class = SedeSerializer


class ProgramaViewSet(CatalogoViewSet):
    queryset = Programa.objects.all()
    serializer_class = ProgramaSerializer


class FichaViewSet(CatalogoViewSet):
    queryset = Ficha.objects.select_related("programa", "sede")
    serializer_class = FichaSerializer


class AmbienteViewSet(CatalogoViewSet):
    queryset = Ambiente.objects.select_related("sede")
    serializer_class = AmbienteSerializer
