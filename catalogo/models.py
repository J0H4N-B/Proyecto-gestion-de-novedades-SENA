from django.db import models


class Sede(models.Model):
    codigo = models.CharField("código", max_length=100, unique=True)
    nombre = models.CharField(max_length=100)
    direccion = models.CharField("dirección", max_length=255)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Programa(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    class Meta:
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Ficha(models.Model):
    class Jornada(models.TextChoices):
        DIURNO = "diurno", "Diurno"
        NOCTURNO = "nocturno", "Nocturno"

    codigo = models.CharField("código", max_length=50, unique=True)
    programa = models.ForeignKey(Programa, on_delete=models.PROTECT)
    sede = models.ForeignKey(Sede, on_delete=models.PROTECT)
    jornada = models.CharField(max_length=10, choices=Jornada.choices)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return self.codigo


class Ambiente(models.Model):
    class Estado(models.TextChoices):
        ACTIVO = "AC", "Activo"
        INACTIVO = "IN", "Inactivo"

    codigo = models.CharField("código", max_length=100, unique=True)
    estado = models.CharField(max_length=2, choices=Estado.choices, default=Estado.ACTIVO)
    ubicacion = models.CharField("ubicación", max_length=255)
    sede = models.ForeignKey(Sede, on_delete=models.PROTECT)

    class Meta:
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.codigo} - {self.sede.nombre}"
