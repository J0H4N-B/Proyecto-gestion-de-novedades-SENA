from rest_framework import viewsets
from rest_framework.permissions import SAFE_METHODS, BasePermission, IsAuthenticated

from .permisos import novedades_visibles
from .serializers import NovedadSerializer


class LecturaOGestor(BasePermission):
    def has_permission(self, request, view):
        return request.method in SAFE_METHODS or request.user.es_gestor


class NovedadViewSet(viewsets.ModelViewSet):
    serializer_class = NovedadSerializer
    permission_classes = [IsAuthenticated, LecturaOGestor]

    def get_queryset(self):
        return novedades_visibles(self.request.user)

    def perform_create(self, serializer):
        serializer.save(creado_por=self.request.user)
