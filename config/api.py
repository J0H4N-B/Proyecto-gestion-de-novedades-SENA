from rest_framework import routers

from catalogo.api import AmbienteViewSet, FichaViewSet, ProgramaViewSet, SedeViewSet
from cuentas.api import UsuarioViewSet
from novedades.api import NovedadViewSet

router = routers.DefaultRouter()
router.register("sedes", SedeViewSet)
router.register("programas", ProgramaViewSet)
router.register("fichas", FichaViewSet)
router.register("ambientes", AmbienteViewSet)
router.register("usuarios", UsuarioViewSet)
router.register("novedades", NovedadViewSet, basename="novedad")
