import os
import uuid
from functools import partial
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models.signals import post_delete, post_save, pre_save
from django.http import FileResponse, Http404
from django.utils import timezone
from django.utils.deconstruct import deconstructible
from PIL import Image, ImageOps

Image.MAX_IMAGE_PIXELS = 40_000_000

EXTENSIONES_EVIDENCIA = ["pdf", "png", "jpg", "jpeg"]
EXTENSIONES_FOTO = ["png", "jpg", "jpeg", "webp"]

FIRMAS = {
    ".pdf": (b"%PDF-",),
    ".png": (b"\x89PNG\r\n\x1a\n",),
    ".jpg": (b"\xff\xd8\xff",),
    ".jpeg": (b"\xff\xd8\xff",),
}

TIPOS_ARCHIVO = {
    ".pdf": {"etiqueta": "Documento PDF", "icono": "bxs-file-pdf", "color": "danger", "es_imagen": False},
    ".png": {"etiqueta": "Imagen PNG", "icono": "bxs-file-png", "color": "info", "es_imagen": True},
    ".jpg": {"etiqueta": "Imagen JPG", "icono": "bxs-file-jpg", "color": "info", "es_imagen": True},
    ".jpeg": {"etiqueta": "Imagen JPEG", "icono": "bxs-file-jpg", "color": "info", "es_imagen": True},
}
TIPO_DESCONOCIDO = {"etiqueta": "Archivo", "icono": "bxs-file", "color": "secondary", "es_imagen": False}


def extension(nombre):
    return os.path.splitext(nombre)[1].lower()


def describir_archivo(nombre):
    return TIPOS_ARCHIVO.get(extension(nombre), TIPO_DESCONOCIDO)


def ruta_con_uuid(carpeta, nombre, ext=None):
    return f"{carpeta}/{timezone.now():%Y/%m}/{uuid.uuid4().hex}{ext or extension(nombre)}"


@deconstructible
class TamanoMaximo:
    def __init__(self, ajuste):
        self.ajuste = ajuste

    def __call__(self, archivo):
        if getattr(archivo, "_committed", False):
            return
        limite = getattr(settings, self.ajuste)
        if archivo.size > limite * 1024 * 1024:
            raise ValidationError(f"El archivo no puede pesar más de {limite} MB.")

    def __eq__(self, otro):
        return isinstance(otro, TamanoMaximo) and self.ajuste == otro.ajuste


def validar_firma(archivo):
    if getattr(archivo, "_committed", False):
        return
    inicio = archivo.read(8)
    archivo.seek(0)
    if not any(inicio.startswith(firma) for firma in FIRMAS.get(extension(archivo.name), ())):
        raise ValidationError("El contenido del archivo no corresponde a su extensión.")


def normalizar_imagen(archivo, lado=320):
    try:
        with Image.open(archivo) as imagen:
            imagen = ImageOps.exif_transpose(imagen).convert("RGB")
            imagen = ImageOps.fit(imagen, (lado, lado), Image.Resampling.LANCZOS)
            salida = BytesIO()
            imagen.save(salida, "JPEG", quality=85, optimize=True)
    except (OSError, Image.DecompressionBombError) as error:
        raise ValidationError("No se pudo procesar la imagen.") from error
    return ContentFile(salida.getvalue(), name="foto.jpg")


def respuesta_archivo(campo, nombre, inline=False):
    try:
        archivo = campo.storage.open(campo.name, "rb")
    except FileNotFoundError:
        raise Http404
    respuesta = FileResponse(archivo, as_attachment=not inline, filename=nombre)
    if inline:
        respuesta["Content-Security-Policy"] = "default-src 'none'; sandbox"
        respuesta["Cache-Control"] = "private, max-age=86400"
    return respuesta


def limpiar_archivos_huerfanos(modelo, campo):
    marca = f"_{campo}_anterior"
    uid = f"{modelo._meta.label_lower}.{campo}"

    def recordar(sender, instance, update_fields=None, **kwargs):
        setattr(instance, marca, None)
        if not instance.pk or (update_fields is not None and campo not in update_fields):
            return
        anterior = sender.objects.filter(pk=instance.pk).values_list(campo, flat=True).first()
        if anterior and anterior != getattr(instance, campo).name:
            setattr(instance, marca, anterior)

    def borrar_anterior(sender, instance, **kwargs):
        anterior = getattr(instance, marca, None)
        if anterior:
            transaction.on_commit(partial(getattr(instance, campo).storage.delete, anterior))

    def borrar(sender, instance, **kwargs):
        archivo = getattr(instance, campo)
        if archivo:
            transaction.on_commit(partial(archivo.storage.delete, archivo.name))

    pre_save.connect(recordar, sender=modelo, weak=False, dispatch_uid=f"{uid}.recordar")
    post_save.connect(borrar_anterior, sender=modelo, weak=False, dispatch_uid=f"{uid}.anterior")
    post_delete.connect(borrar, sender=modelo, weak=False, dispatch_uid=f"{uid}.borrar")
