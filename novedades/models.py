from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models
from django.urls import reverse

from core.archivos import (
    EXTENSIONES_EVIDENCIA,
    TamanoMaximo,
    describir_archivo,
    extension,
    ruta_con_uuid,
    validar_firma,
)


def ruta_evidencia(instancia, nombre):
    return ruta_con_uuid("evidencias", nombre)


class Novedad(models.Model):
    class Tipo(models.TextChoices):
        ACADEMICA = "ACAD", "Académica"
        DISCIPLINARIA = "DISC", "Disciplinaria"
        AMBIENTE = "AMBI", "Ambiente"

    ESTILOS = {
        Tipo.ACADEMICA: ("bx-book-open", "primary"),
        Tipo.DISCIPLINARIA: ("bx-shield-x", "danger"),
        Tipo.AMBIENTE: ("bx-building", "warning"),
    }

    tipo = models.CharField(max_length=4, choices=Tipo.choices)
    aprendiz = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="novedades", on_delete=models.PROTECT)
    ambiente = models.ForeignKey("catalogo.Ambiente", null=True, blank=True, on_delete=models.SET_NULL)
    descripcion = models.TextField("descripción")
    creado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="creadas",
        null=True,
        on_delete=models.SET_NULL,
        verbose_name="registrada por",
    )
    creado_en = models.DateTimeField("fecha de registro", auto_now_add=True)
    archivo = models.FileField(
        "evidencia",
        upload_to=ruta_evidencia,
        validators=[
            FileExtensionValidator(EXTENSIONES_EVIDENCIA),
            TamanoMaximo("EVIDENCIA_MAX_MB"),
            validar_firma,
        ],
    )

    class Meta:
        ordering = ["-creado_en"]
        verbose_name = "novedad"
        verbose_name_plural = "novedades"

    def __str__(self):
        return f"{self.get_tipo_display()} - {self.aprendiz}"

    def get_absolute_url(self):
        return reverse("novedades:detalle", args=[self.pk])

    @property
    def icono_tipo(self):
        return self.ESTILOS[self.tipo][0]

    @property
    def color_tipo(self):
        return self.ESTILOS[self.tipo][1]

    @property
    def tipo_archivo(self):
        return describir_archivo(self.archivo.name)

    @property
    def nombre_descarga(self):
        return f"novedad-{self.aprendiz.tipo_doc}{self.aprendiz.numero_documento}{extension(self.archivo.name)}"
