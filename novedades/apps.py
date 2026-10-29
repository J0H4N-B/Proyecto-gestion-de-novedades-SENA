from django.apps import AppConfig


class NovedadesConfig(AppConfig):
    name = "novedades"

    def ready(self):
        from core.archivos import limpiar_archivos_huerfanos

        limpiar_archivos_huerfanos(self.get_model("Novedad"), "archivo")
