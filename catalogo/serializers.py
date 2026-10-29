from rest_framework import serializers

from .models import Ambiente, Ficha, Programa, Sede


class SedeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Sede
        fields = ["id", "codigo", "nombre", "direccion"]


class ProgramaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Programa
        fields = ["id", "nombre"]


class FichaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ficha
        fields = ["id", "codigo", "programa", "sede", "jornada"]


class AmbienteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ambiente
        fields = ["id", "codigo", "estado", "ubicacion", "sede"]
