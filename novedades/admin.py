from django.contrib import admin

from .models import Novedad


@admin.register(Novedad)
class NovedadAdmin(admin.ModelAdmin):
    list_display = ("tipo", "aprendiz", "ambiente", "creado_por", "creado_en")
    list_filter = ("tipo", "creado_en")
    search_fields = ("aprendiz__first_name", "aprendiz__last_name", "aprendiz__numero_documento")
    list_select_related = ("aprendiz", "ambiente__sede", "creado_por")
    raw_id_fields = ("aprendiz", "creado_por")
