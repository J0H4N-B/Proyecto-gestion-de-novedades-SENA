import shutil
import tempfile
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from catalogo.models import Ambiente, Ficha, Programa, Sede
from cuentas.models import Usuario

PDF = b"%PDF-1.4\n" + b"0" * 50
PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50
CLAVE = "clave-segura-2026"
MEDIA = tempfile.mkdtemp()


def pdf(nombre="evidencia.pdf", contenido=PDF):
    return SimpleUploadedFile(nombre, contenido, content_type="application/pdf")


def imagen(nombre="foto.png", formato="PNG", tamano=(800, 600)):
    salida = BytesIO()
    Image.new("RGB", tamano, "#3366cc").save(salida, formato)
    return SimpleUploadedFile(nombre, salida.getvalue())


@override_settings(MEDIA_ROOT=MEDIA)
class BaseTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.sede = Sede.objects.create(codigo="S1", nombre="Soacha", direccion="Calle 1")
        cls.otra_sede = Sede.objects.create(codigo="S2", nombre="Bogotá", direccion="Calle 2")
        programa = Programa.objects.create(nombre="Análisis y Desarrollo de Software")
        cls.ficha = Ficha.objects.create(codigo="2900001", programa=programa, sede=cls.sede, jornada="diurno")
        cls.ficha_otra = Ficha.objects.create(codigo="2900002", programa=programa, sede=cls.otra_sede, jornada="diurno")
        cls.ambiente = Ambiente.objects.create(codigo="A-101", ubicacion="Bloque A", sede=cls.sede)
        cls.ana = cls.usuario("ana", Usuario.Rol.APRENDIZ, "1001", ficha=cls.ficha)
        cls.beto = cls.usuario("beto", Usuario.Rol.APRENDIZ, "1002", ficha=cls.ficha)
        cls.lejano = cls.usuario("lejano", Usuario.Rol.APRENDIZ, "1003", ficha=cls.ficha_otra)
        cls.instructor = cls.usuario("instructor", Usuario.Rol.INSTRUCTOR, "2001")
        cls.otro_instructor = cls.usuario("instructor2", Usuario.Rol.INSTRUCTOR, "2002")
        cls.coordinador = cls.usuario("coordinador", Usuario.Rol.COORDINADOR, "3001", sede=cls.sede)
        cls.admin = Usuario.objects.create_superuser("admin", "a@x.co", CLAVE, numero_documento="9000")

    @classmethod
    def usuario(cls, username, rol, documento, **extra):
        return Usuario.objects.create_user(
            username, f"{username}@x.co", CLAVE, rol=rol, numero_documento=documento,
            first_name=username.capitalize(), **extra,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)
