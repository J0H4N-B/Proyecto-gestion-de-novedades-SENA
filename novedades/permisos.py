from cuentas.models import Usuario

from .models import Novedad


def novedades_visibles(usuario):
    novedades = Novedad.objects.select_related("aprendiz__ficha", "ambiente", "creado_por")
    if usuario.is_superuser:
        return novedades
    if usuario.rol == Usuario.Rol.COORDINADOR:
        return novedades.filter(aprendiz__sede_id=usuario.sede_id) if usuario.sede_id else novedades.none()
    if usuario.rol == Usuario.Rol.INSTRUCTOR:
        return novedades.filter(creado_por=usuario)
    return novedades.filter(aprendiz=usuario)


def aprendices_asignables(usuario):
    aprendices = Usuario.objects.filter(rol=Usuario.Rol.APRENDIZ, is_active=True)
    if usuario.is_superuser or usuario.rol == Usuario.Rol.INSTRUCTOR:
        return aprendices
    if usuario.rol == Usuario.Rol.COORDINADOR and usuario.sede_id:
        return aprendices.filter(sede_id=usuario.sede_id)
    return aprendices.none()
