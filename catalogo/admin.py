from django.contrib import admin

from .models import Ambiente, Ficha, Programa, Sede


@admin.register(Sede)
class SedeAdmin(admin.ModelAdmin):
    list_display = ("codigo", "nombre", "direccion")
    search_fields = ("codigo", "nombre")


@admin.register(Programa)
class ProgramaAdmin(admin.ModelAdmin):
    search_fields = ("nombre",)


@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    list_display = ("codigo", "programa", "sede", "jornada")
    list_filter = ("sede", "jornada")
    search_fields = ("codigo", "programa__nombre")


@admin.register(Ambiente)
class AmbienteAdmin(admin.ModelAdmin):
    list_display = ("codigo", "ubicacion", "sede", "estado")
    list_filter = ("sede", "estado")
    search_fields = ("codigo", "ubicacion")
