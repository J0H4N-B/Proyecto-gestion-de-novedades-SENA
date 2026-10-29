import random
import struct
import unicodedata
import zlib
from datetime import timedelta

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from catalogo.models import Ambiente, Ficha, Programa, Sede
from cuentas.models import Usuario
from novedades.models import Novedad

DOMINIO = "demo.novedades.local"
CLAVE = "Demo-Novedades-2026"

NOMBRES = [
    "Valentina", "Santiago", "Camila", "Juan David", "Laura", "Andrés", "Daniela", "Sebastián",
    "Mariana", "Felipe", "Natalia", "Carlos", "Paula", "Mateo", "Luisa", "Esteban", "Sofía",
    "Nicolás", "Ximena", "Julián", "Karen", "Brayan", "Yuliana", "Cristian",
]
APELLIDOS = [
    "Rojas", "Moreno", "Quintero", "Pardo", "Cárdenas", "Ospina", "Beltrán", "Cifuentes",
    "Rincón", "Gaitán", "Salamanca", "Triana", "Bermúdez", "Acosta", "Mahecha", "Pinzón",
    "Ardila", "Castañeda", "Forero", "Londoño", "Suárez", "Barrera", "Niño", "Bustos",
]
PROGRAMAS = [
    "Análisis y Desarrollo de Software",
    "Gestión Contable y Financiera",
    "Producción Multimedia",
    "Cocina Profesional",
]
SEDES = [
    ("DEMO-SOA", "Soacha", "Carrera 7 # 30-12, Soacha"),
    ("DEMO-BOG", "Bogotá - Centro", "Calle 13 # 8-45, Bogotá"),
]
DESCRIPCIONES = {
    Novedad.Tipo.ACADEMICA: [
        "No entregó la evidencia de la guía de aprendizaje en la fecha acordada.",
        "Tres inasistencias consecutivas sin justificación a la formación técnica.",
        "Solicita aplazamiento de la evaluación por incapacidad médica.",
        "Bajo desempeño en el proyecto formativo; se acuerda plan de mejoramiento.",
        "Reporta dificultades de conectividad para entregar actividades virtuales.",
    ],
    Novedad.Tipo.DISCIPLINARIA: [
        "Llegó tarde de forma reiterada durante la semana y alteró el inicio de la clase.",
        "Uso del celular durante la evaluación después de ser advertido.",
        "Discusión con un compañero en el ambiente; se hizo llamado de atención verbal.",
        "No porta el uniforme requerido para el taller práctico.",
    ],
    Novedad.Tipo.AMBIENTE: [
        "Dos equipos de cómputo no encienden y no se puede completar la práctica.",
        "Goteras en el techo cerca de los tableros; riesgo para los equipos.",
        "El aire acondicionado no funciona y la temperatura supera lo tolerable.",
        "Faltan sillas para el total de aprendices de la ficha.",
        "La cerradura de la puerta está dañada y el ambiente no se puede asegurar.",
    ],
}


def sin_acentos(texto):
    return unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()


def crear_png(tono, ancho=160, alto=100):
    filas = b"".join(
        b"\x00" + bytes((tono[0] * y // alto, tono[1], tono[2] * (alto - y) // alto)) * ancho
        for y in range(alto)
    )

    def trozo(tipo, datos):
        cuerpo = tipo + datos
        return struct.pack(">I", len(datos)) + cuerpo + struct.pack(">I", zlib.crc32(cuerpo))

    cabecera = struct.pack(">IIBBBBB", ancho, alto, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + trozo(b"IHDR", cabecera)
        + trozo(b"IDAT", zlib.compress(filas))
        + trozo(b"IEND", b"")
    )


def crear_pdf(texto):
    texto = sin_acentos(texto).replace("\\", "").replace("(", "[").replace(")", "]")
    flujo = f"BT /F1 12 Tf 50 750 Td ({texto[:90]}) Tj ET".encode()
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(flujo) + flujo + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    pdf = b"%PDF-1.4\n"
    posiciones = []
    for n, objeto in enumerate(objetos, start=1):
        posiciones.append(len(pdf))
        pdf += b"%d 0 obj\n" % n + objeto + b"\nendobj\n"
    inicio_xref = len(pdf)
    pdf += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objetos) + 1)
    pdf += b"".join(b"%010d 00000 n \n" % p for p in posiciones)
    pdf += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objetos) + 1, inicio_xref)
    return pdf


class Command(BaseCommand):
    help = "Carga sedes, fichas, usuarios y novedades de ejemplo para probar la aplicación."

    def add_arguments(self, parser):
        parser.add_argument("--novedades", type=int, default=45)
        parser.add_argument("--limpiar", action="store_true")

    def handle(self, *args, **opciones):
        if not settings.DEBUG:
            raise CommandError("Los datos demo usan contraseñas conocidas; solo se cargan con DJANGO_DEBUG=1.")
        if opciones["limpiar"]:
            self.limpiar()
            self.stdout.write("Datos demo anteriores eliminados.")
        if Novedad.objects.filter(aprendiz__email__endswith=f"@{DOMINIO}").exists():
            self.stdout.write("Ya hay datos demo cargados. Usa --limpiar para regenerarlos.")
            return
        with transaction.atomic():
            self.cargar(random.Random(2026), opciones["novedades"])

    def limpiar(self):
        demo = Usuario.objects.filter(email__endswith=f"@{DOMINIO}")
        Novedad.objects.filter(aprendiz__in=demo).delete()
        demo.delete()
        Ficha.objects.filter(codigo__startswith="DEMO-").delete()
        Ambiente.objects.filter(codigo__startswith="DEMO-").delete()
        Sede.objects.filter(codigo__startswith="DEMO-").delete()

    def avatar(self, indice):
        tono = ((indice * 53) % 160 + 60, (indice * 97) % 160 + 60, (indice * 31) % 160 + 60)
        return ContentFile(crear_png(tono, 200, 200), name="avatar.png")

    def usuario(self, username, nombre, apellido, rol, indice, **extra):
        if indice % 2 == 0:
            extra["foto"] = self.avatar(indice)
        return Usuario.objects.create_user(
            username, f"{username}@{DOMINIO}", CLAVE, first_name=nombre, last_name=apellido,
            rol=rol, numero_documento=str(1010000000 + indice * 1237),
            telefono=f"3{indice % 10}{(indice * 7919) % 10**8:08d}", **extra,
        )

    def cargar(self, azar, cantidad):
        sedes = [Sede.objects.create(codigo=c, nombre=n, direccion=d) for c, n, d in SEDES]
        programas = [Programa.objects.get_or_create(nombre=n)[0] for n in PROGRAMAS]

        fichas = []
        for i, sede in enumerate(sedes):
            for j in range(3):
                fichas.append(Ficha.objects.create(
                    codigo=f"DEMO-{i + 1}0{j + 1}", programa=programas[(i * 3 + j) % len(programas)],
                    sede=sede, jornada="diurno" if j < 2 else "nocturno",
                ))

        ambientes = {sede.pk: [] for sede in sedes}
        for sede in sedes:
            for n in range(1, 6):
                ambientes[sede.pk].append(Ambiente.objects.create(
                    codigo=f"DEMO-{sede.codigo[-3:]}-{100 + n}", sede=sede,
                    ubicacion=f"Bloque {'AB'[n % 2]}, piso {1 + n // 3}",
                    estado=Ambiente.Estado.INACTIVO if n == 5 else Ambiente.Estado.ACTIVO,
                ))

        administrador = Usuario.objects.create_superuser(
            "demo_admin", f"demo_admin@{DOMINIO}", CLAVE, first_name="Administrador", last_name="Demo",
            numero_documento="1010000001", foto=self.avatar(0),
        )
        coordinadores = {
            sede.pk: self.usuario(f"demo_coord_{sin_acentos(sede.nombre.split()[0]).lower()}", "Marcela", apellido,
                                  Usuario.Rol.COORDINADOR, 10 + i, sede=sede)
            for i, (sede, apellido) in enumerate(zip(sedes, ["Vargas", "Peñaloza"]))
        }
        instructores = [
            self.usuario(f"demo_instructor{n + 1}", NOMBRES[n], APELLIDOS[n + 4], Usuario.Rol.INSTRUCTOR,
                         20 + n, sede=sedes[n % 2])
            for n in range(4)
        ]
        aprendices = [
            self.usuario(f"demo_aprendiz{n + 1:02d}", NOMBRES[n], APELLIDOS[(n * 5) % len(APELLIDOS)],
                         Usuario.Rol.APRENDIZ, 100 + n, ficha=fichas[n % len(fichas)])
            for n in range(24)
        ]

        ahora = timezone.now()
        for n in range(cantidad):
            aprendiz = azar.choice(aprendices)
            tipo = azar.choices(list(Novedad.Tipo), weights=[5, 3, 3])[0]
            ambiente = None
            if tipo == Novedad.Tipo.AMBIENTE or azar.random() < 0.3:
                ambiente = azar.choice(ambientes[aprendiz.sede_id][:4])
            autor = coordinadores[aprendiz.sede_id] if azar.random() < 0.3 else azar.choice(instructores)
            descripcion = azar.choice(DESCRIPCIONES[tipo])
            if n % 3:
                archivo = ContentFile(crear_pdf(f"Evidencia - {tipo.label} - {aprendiz}"), name="evidencia.pdf")
            else:
                archivo = ContentFile(
                    crear_png((azar.randint(60, 255), azar.randint(60, 255), azar.randint(60, 255))),
                    name="foto.png",
                )
            novedad = Novedad.objects.create(
                tipo=tipo, aprendiz=aprendiz, ambiente=ambiente, descripcion=descripcion,
                creado_por=autor, archivo=archivo,
            )
            Novedad.objects.filter(pk=novedad.pk).update(
                creado_en=ahora - timedelta(days=azar.randint(0, 90), hours=azar.randint(0, 9))
            )

        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(sedes)} sedes, {len(fichas)} fichas, {len(aprendices)} aprendices y {cantidad} novedades."
        ))
        self.stdout.write(f"\nContraseña de todos los usuarios demo: {CLAVE}\n")
        self.stdout.write("Usuarios para probar cada rol:")
        for rol, usuario in [
            ("Superusuario", administrador),
            ("Coordinador (Soacha)", coordinadores[sedes[0].pk]),
            ("Coordinador (Bogotá)", coordinadores[sedes[1].pk]),
            ("Instructor", instructores[0]),
            ("Instructor", instructores[1]),
            ("Aprendiz", aprendices[0]),
            ("Aprendiz", aprendices[1]),
        ]:
            self.stdout.write(f"  {rol:<22} {usuario.username}")
