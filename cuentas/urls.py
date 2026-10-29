from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = "cuentas"

urlpatterns = [
    path("ingresar/", views.IngresarView.as_view(), name="ingresar"),
    path("salir/", LogoutView.as_view(), name="salir"),
    path("registro/", views.RegistroView.as_view(), name="registro"),
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
    path("clave/", views.ClaveView.as_view(), name="clave"),
    path("clave/lista/", views.ClaveListaView.as_view(), name="clave_lista"),
    path("foto/<int:pk>/", views.FotoView.as_view(), name="foto"),
]
