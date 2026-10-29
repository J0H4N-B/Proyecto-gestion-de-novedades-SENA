from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import CommandError, call_command
from django.test import SimpleTestCase, override_settings

from cuentas.models import Usuario
from novedades.models import Novedad

from .archivos import describir_archivo, extension, normalizar_imagen
from .testing import BaseTest, pdf


class ArchivosTest(SimpleTestCase):
    def test_describe_tipos_conocidos_y_desconocidos(self):
        self.assertEqual(describir_archivo("a/b/c.PDF")["icono"], "bxs-file-pdf")
        self.assertTrue(describir_archivo("x.jpeg")["es_imagen"])
        self.assertEqual(describir_archivo("x.zip")["etiqueta"], "Archivo")
        self.assertEqual(extension("Informe.Final.PDF"), ".pdf")

    def test_imagen_corrupta_se_rechaza(self):
        with self.assertRaises(ValidationError):
            normalizar_imagen(SimpleUploadedFile("x.png", b"basura"))


@override_settings(DEBUG=True)
class DemoTest(BaseTest):
    def cargar(self, *args):
        with self.captureOnCommitCallbacks(execute=True):
            call_command("cargar_demo", *args, verbosity=0)

    def demo(self):
        return Novedad.objects.filter(aprendiz__email__endswith="demo.novedades.local")

    def test_carga_y_es_idempotente(self):
        self.cargar("--novedades", "12")
        self.assertEqual(self.demo().count(), 12)
        self.cargar("--novedades", "12")
        self.assertEqual(self.demo().count(), 12)

    def test_incluye_superusuario_con_foto(self):
        self.cargar("--novedades", "3")
        admin = Usuario.objects.get(username="demo_admin")
        self.assertTrue(admin.is_superuser and admin.is_staff)
        self.assertTrue(admin.check_password("Demo-Novedades-2026"))
        self.assertTrue(admin.foto)

    def test_archivos_demo_pasan_las_validaciones(self):
        self.cargar("--novedades", "6")
        for novedad in self.demo():
            novedad.full_clean()

    def test_limpiar_borra_solo_lo_demo(self):
        propia = Novedad.objects.create(
            tipo="ACAD", aprendiz=self.ana, descripcion="x", creado_por=self.instructor, archivo=pdf()
        )
        self.cargar("--novedades", "6")
        self.cargar("--limpiar", "--novedades", "3")
        self.assertEqual(Novedad.objects.count(), 4)
        self.assertTrue(Novedad.objects.filter(pk=propia.pk).exists())
        self.assertEqual(Usuario.objects.filter(username="demo_admin").count(), 1)

    def test_se_niega_fuera_de_desarrollo(self):
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command("cargar_demo", verbosity=0)
