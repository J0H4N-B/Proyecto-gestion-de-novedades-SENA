from django.conf import settings
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils import timezone

from .models import AccesoBloqueado, Usuario

campos_centro = ("tipo_doc", "numero_documento", "telefono", "rol", "sede", "ficha", "foto")


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "rol", "sede", "ficha", "is_active")
    list_filter = ("rol", "sede", "is_active")
    search_fields = ("username", "first_name", "last_name", "numero_documento")
    fieldsets = UserAdmin.fieldsets + (("Datos del centro", {"fields": campos_centro}),)
    add_fieldsets = UserAdmin.add_fieldsets + (("Datos del centro", {"fields": campos_centro}),)


@admin.register(AccesoBloqueado)
class AccesoBloqueadoAdmin(admin.ModelAdmin):
    list_display = ("usuario", "direccion_ip", "intentos", "ultimo_intento", "bloqueado_hasta")
    search_fields = ("username", "ip_address")
    ordering = ("-attempt_time",)
    actions = ["desbloquear"]

    def get_queryset(self, request):
        desde = timezone.now() - settings.AXES_COOLOFF_TIME
        return super().get_queryset(request).filter(
            failures_since_start__gte=settings.AXES_FAILURE_LIMIT, attempt_time__gte=desde
        )

    def get_actions(self, request):
        acciones = super().get_actions(request)
        acciones.pop("delete_selected", None)
        return acciones

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description="Usuario", ordering="username")
    def usuario(self, acceso):
        return acceso.username

    @admin.display(description="Dirección IP", ordering="ip_address")
    def direccion_ip(self, acceso):
        return acceso.ip_address

    @admin.display(description="Intentos fallidos", ordering="failures_since_start")
    def intentos(self, acceso):
        return acceso.failures_since_start

    @admin.display(description="Último intento", ordering="attempt_time")
    def ultimo_intento(self, acceso):
        return acceso.attempt_time

    @admin.display(description="Bloqueado hasta")
    def bloqueado_hasta(self, acceso):
        return acceso.attempt_time + settings.AXES_COOLOFF_TIME

    @admin.action(description="Desbloquear los usuarios seleccionados", permissions=["delete"])
    def desbloquear(self, request, queryset):
        for acceso in queryset:
            self.log_change(request, acceso, "Desbloqueado desde el administrador")
        cantidad = queryset.count()
        queryset.delete()
        self.message_user(request, f"Se desbloquearon {cantidad} accesos. Ya pueden volver a ingresar.")
