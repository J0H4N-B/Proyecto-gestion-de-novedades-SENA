from django.urls import path

from . import views

app_name = "novedades"

urlpatterns = [
    path("", views.NovedadListView.as_view(), name="lista"),
    path("novedades/tabla/", views.NovedadTablaView.as_view(), name="tabla"),
    path("novedades/nueva/", views.NovedadCreateView.as_view(), name="crear"),
    path("novedades/<int:pk>/", views.NovedadDetailView.as_view(), name="detalle"),
    path("novedades/<int:pk>/editar/", views.NovedadUpdateView.as_view(), name="editar"),
    path("novedades/<int:pk>/eliminar/", views.NovedadDeleteView.as_view(), name="eliminar"),
    path("novedades/<int:pk>/evidencia/", views.EvidenciaView.as_view(), name="evidencia"),
]
