from django.db.models import ProtectedError
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError


class ProtegidoViewSet(viewsets.ModelViewSet):
    def perform_destroy(self, instance):
        try:
            instance.delete()
        except ProtectedError:
            raise ValidationError("No se puede eliminar: tiene registros asociados.")
