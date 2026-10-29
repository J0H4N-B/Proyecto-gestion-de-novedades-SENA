from pathlib import Path

from axes.models import AccessAttempt
from django.contrib.auth.models import AbstractUser
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

from core.archivos import EXTENSIONES_FOTO, TamanoMaximo, normalizar_imagen, ruta_con_uuid


def ruta_foto(instancia, nombre):
    return ruta_con_uuid("fotos", nombre, ".jpg")


class Usuario(AbstractUser):
    class TipoDoc(models.TextChoices):
        TI = "TI", "Tarjeta de identidad"
        CC = "CC", "Cédula de ciudadanía"
        CE = "CE", "Cédula de extranjería"
        PPT = "PPT", "Permiso de protección especial"

    class Rol(models.TextChoices):
        APRENDIZ = "aprendiz", "Aprendiz"
        INSTRUCTOR = "instructor", "Instructor"
        COORDINADOR = "coordinador", "Coordinador"

    tipo_doc = models.CharField("tipo de documento", max_length=3, choices=TipoDoc.choices, default=TipoDoc.CC)
    numero_documento = models.CharField("número de documento", max_length=12)
    telefono = models.CharField("teléfono", max_length=30, blank=True)
    rol = models.CharField(max_length=12, choices=Rol.choices, default=Rol.APRENDIZ)
    sede = models.ForeignKey("catalogo.Sede", null=True, blank=True, on_delete=models.SET_NULL)
    ficha = models.ForeignKey("catalogo.Ficha", null=True, blank=True, on_delete=models.SET_NULL)
    foto = models.ImageField(
        "foto de perfil",
        upload_to=ruta_foto,
        blank=True,
        validators=[FileExtensionValidator(EXTENSIONES_FOTO), TamanoMaximo("FOTO_MAX_MB")],
    )

    REQUIRED_FIELDS = ["email", "numero_documento"]

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["tipo_doc", "numero_documento"],
                name="documento_unico",
                violation_error_message="Ya existe una cuenta con ese tipo y número de documento.",
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.username

    @property
    def es_gestor(self):
        return self.is_superuser or self.rol in (self.Rol.INSTRUCTOR, self.Rol.COORDINADOR)

    @property
    def iniciales(self):
        return f"{self.first_name[:1]}{self.last_name[:1]}".upper() or self.username[:2].upper()

    @property
    def foto_url(self):
        if not self.foto:
            return ""
        return f"{reverse('cuentas:foto', args=[self.pk])}?v={Path(self.foto.name).stem[:8]}"

    def save(self, *args, **kwargs):
        if not kwargs.get("update_fields"):
            if self.ficha_id:
                self.sede_id = self.ficha.sede_id
            if self.foto and not self.foto._committed:
                self.foto = normalizar_imagen(self.foto)
        super().save(*args, **kwargs)


class AccesoBloqueado(AccessAttempt):
    class Meta:
        proxy = True
        verbose_name = "usuario bloqueado"
        verbose_name_plural = "usuarios bloqueados"
