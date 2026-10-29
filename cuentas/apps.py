from django.apps import AppConfig


class CuentasConfig(AppConfig):
    name = "cuentas"

    def ready(self):
        from core.archivos import limpiar_archivos_huerfanos

        limpiar_archivos_huerfanos(self.get_model("Usuario"), "foto")
