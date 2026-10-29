from django.urls import reverse
from rest_framework import serializers

from cuentas.models import Usuario

from .models import Novedad
from .permisos import aprendices_asignables


class NovedadSerializer(serializers.ModelSerializer):
    aprendiz = serializers.PrimaryKeyRelatedField(queryset=Usuario.objects.none())
    aprendiz_nombre = serializers.CharField(source="aprendiz.get_full_name", read_only=True)
    archivo_url = serializers.SerializerMethodField()

    class Meta:
        model = Novedad
        fields = [
            "id", "tipo", "aprendiz", "aprendiz_nombre", "ambiente", "descripcion",
            "archivo", "archivo_url", "creado_por", "creado_en",
        ]
        read_only_fields = ["creado_por", "creado_en"]
        extra_kwargs = {"archivo": {"write_only": True}}

    def get_fields(self):
        campos = super().get_fields()
        request = self.context.get("request")
        if request:
            campos["aprendiz"].queryset = aprendices_asignables(request.user)
        return campos

    def get_archivo_url(self, novedad):
        ruta = reverse("novedades:evidencia", args=[novedad.pk])
        return self.context["request"].build_absolute_uri(ruta)
