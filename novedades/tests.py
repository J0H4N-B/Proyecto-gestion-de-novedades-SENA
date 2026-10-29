import re
from pathlib import Path

from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient

from core.testing import PDF, PNG, BaseTest, pdf
from cuentas.models import Usuario

from .models import Novedad


class NovedadTestCase(BaseTest):
    def novedad(self, aprendiz=None, creado_por=None, archivo=None, tipo="ACAD"):
        with self.captureOnCommitCallbacks(execute=True):
            return Novedad.objects.create(
                tipo=tipo, aprendiz=aprendiz or self.ana, descripcion="Inasistencia",
                creado_por=creado_por or self.instructor, archivo=archivo or pdf(),
            )

    def tabla(self, **parametros):
        respuesta = self.client.get(reverse("novedades:tabla"), {"draw": 3, "start": 0, "length": 15, **parametros})
        self.assertEqual(respuesta.status_code, 200)
        return respuesta.json()

    def urls_en(self, datos):
        return {url for fila in datos["data"] for url in re.findall(r'href="(/novedades/\d+/)"', fila[2])}


class TablaTest(NovedadTestCase):
    def test_aprendiz_solo_ve_las_suyas(self):
        propia = self.novedad(self.ana)
        ajena = self.novedad(self.beto)
        self.client.force_login(self.ana)
        self.assertEqual(self.urls_en(self.tabla()), {propia.get_absolute_url()})
        self.assertEqual(self.client.get(ajena.get_absolute_url()).status_code, 404)

    def test_instructor_solo_ve_las_que_registro(self):
        propia = self.novedad(creado_por=self.instructor)
        ajena = self.novedad(creado_por=self.otro_instructor)
        self.client.force_login(self.instructor)
        self.assertEqual(self.urls_en(self.tabla()), {propia.get_absolute_url()})
        self.assertEqual(self.client.get(reverse("novedades:editar", args=[ajena.pk])).status_code, 404)

    def test_coordinador_ve_su_sede(self):
        de_sede = self.novedad(self.ana)
        de_otra = self.novedad(self.lejano)
        self.client.force_login(self.coordinador)
        self.assertEqual(self.urls_en(self.tabla()), {de_sede.get_absolute_url()})
        self.assertEqual(self.client.get(de_otra.get_absolute_url()).status_code, 404)

    def test_coordinador_sin_sede_no_ve_nada(self):
        self.novedad()
        self.client.force_login(self.usuario("sinsede", Usuario.Rol.COORDINADOR, "3002"))
        self.assertEqual(self.tabla()["recordsTotal"], 0)

    def test_superusuario_ve_todo(self):
        self.novedad(self.ana)
        self.novedad(self.lejano)
        self.client.force_login(self.admin)
        self.assertEqual(self.tabla()["recordsTotal"], 2)

    def test_anonimo_redirige(self):
        self.assertEqual(self.client.get(reverse("novedades:tabla")).status_code, 302)

    def test_protocolo_datatables_y_paginacion(self):
        for _ in range(16):
            self.novedad()
        self.client.force_login(self.admin)
        primera = self.tabla(length=10)
        self.assertEqual((primera["draw"], primera["recordsTotal"], primera["recordsFiltered"]), (3, 16, 16))
        self.assertEqual(len(primera["data"]), 10)
        self.assertEqual(len(self.tabla(length=10, start=10)["data"]), 6)
        self.assertEqual(len(primera["data"][0]), 8)

    def test_busqueda_y_filtro_por_tipo(self):
        self.novedad(self.ana, tipo="ACAD")
        self.novedad(self.beto, tipo="DISC")
        self.client.force_login(self.admin)
        self.assertEqual(self.tabla(**{"search[value]": "beto"})["recordsFiltered"], 1)
        self.assertEqual(self.tabla(**{"search[value]": "1001"})["recordsFiltered"], 1)
        self.assertEqual(self.tabla(tipo="DISC")["recordsFiltered"], 1)
        self.assertEqual(self.tabla(tipo="INVALIDO")["recordsFiltered"], 2)
        self.assertEqual(self.tabla(tipo="AMBI")["recordsFiltered"], 0)

    def test_orden_por_columna(self):
        self.novedad(self.ana, tipo="ACAD")
        self.novedad(self.beto, tipo="DISC")
        self.client.force_login(self.admin)
        asc = self.tabla(**{"order[0][column]": 1, "order[0][dir]": "asc"})
        desc = self.tabla(**{"order[0][column]": 1, "order[0][dir]": "desc"})
        self.assertIn("Académica", asc["data"][0][1])
        self.assertIn("Disciplinaria", desc["data"][0][1])

    def test_parametros_raros_no_rompen(self):
        self.novedad()
        self.client.force_login(self.admin)
        datos = self.tabla(length="abc", start="-5", draw="x", **{"order[0][column]": 99})
        self.assertEqual(datos["recordsTotal"], 1)
        self.assertEqual(len(self.tabla(length=100000)["data"]), 1)
        self.assertEqual(self.tabla(length=-1)["recordsFiltered"], 1)

    def test_escapa_el_contenido_del_usuario(self):
        peligroso = self.usuario("xss", Usuario.Rol.APRENDIZ, "7001", ficha=self.ficha)
        peligroso.first_name = "<script>alert(1)</script>"
        peligroso.save()
        self.novedad(peligroso)
        self.client.force_login(self.admin)
        fila = self.tabla()["data"][0]
        self.assertNotIn("<script>", fila[2])
        self.assertIn("&lt;script&gt;", fila[2])


class PaginasTest(NovedadTestCase):
    def test_lista_muestra_indicadores_por_tipo(self):
        self.novedad(tipo="ACAD")
        self.novedad(tipo="ACAD")
        self.novedad(tipo="DISC")
        self.client.force_login(self.admin)
        respuesta = self.client.get(reverse("novedades:lista"))
        cantidades = {i["valor"]: i["cantidad"] for i in respuesta.context["indicadores"]}
        self.assertEqual(cantidades, {"": 3, "ACAD": 2, "DISC": 1, "AMBI": 0})
        for texto in ("dataTables.bootstrap5.min.js", "boxicons.min.css", "bootstrap.min.css", "lista.js"):
            self.assertContains(respuesta, texto)

    def test_aprendiz_no_ve_botones_de_gestion(self):
        novedad = self.novedad()
        self.client.force_login(self.ana)
        self.assertNotContains(self.client.get(reverse("novedades:lista")), "Registrar novedad")
        self.assertNotContains(self.client.get(novedad.get_absolute_url()), "Eliminar")

    def test_detalle_indica_el_tipo_de_archivo_pdf(self):
        novedad = self.novedad()
        self.client.force_login(self.instructor)
        respuesta = self.client.get(novedad.get_absolute_url())
        self.assertContains(respuesta, "Documento PDF")
        self.assertContains(respuesta, "bxs-file-pdf")
        self.assertContains(respuesta, "novedad-CC1001.pdf")
        self.assertNotContains(respuesta, "?ver=1")

    def test_detalle_de_imagen_muestra_vista_previa(self):
        novedad = self.novedad(archivo=SimpleUploadedFile("foto.png", PNG))
        self.client.force_login(self.instructor)
        respuesta = self.client.get(novedad.get_absolute_url())
        self.assertContains(respuesta, "Imagen PNG")
        self.assertContains(respuesta, "bxs-file-png")
        self.assertContains(respuesta, "?ver=1")

    def test_sidebar_muestra_nombre_rol_y_enlaces(self):
        self.client.force_login(self.coordinador)
        respuesta = self.client.get(reverse("novedades:lista"))
        self.assertContains(respuesta, "Coordinador · Soacha")
        self.assertContains(respuesta, "Nueva novedad")
        self.assertNotContains(respuesta, "Administración")

    def test_aprendiz_no_crea_ni_edita(self):
        novedad = self.novedad()
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("novedades:crear")).status_code, 403)
        self.assertEqual(self.client.get(reverse("novedades:editar", args=[novedad.pk])).status_code, 403)
        self.assertEqual(self.client.post(reverse("novedades:eliminar", args=[novedad.pk])).status_code, 403)

    def test_confirmacion_de_borrado(self):
        novedad = self.novedad()
        self.client.force_login(self.instructor)
        self.assertContains(self.client.get(reverse("novedades:eliminar", args=[novedad.pk])), "¿Eliminar esta novedad?")

    def test_paginas_de_error_usan_el_diseno_de_la_app(self):
        self.client.force_login(self.ana)
        self.assertContains(self.client.get("/novedades/999999/"), "No encontramos esa página", status_code=404)
        self.assertContains(self.client.get(reverse("novedades:crear")), "No tienes permiso para esto", status_code=403)
        self.client.logout()
        self.assertContains(self.client.get("/no-existe/"), "No encontramos esa página", status_code=404)


class ArchivosTest(NovedadTestCase):
    def datos(self, archivo):
        return {"tipo": "ACAD", "aprendiz": self.ana.pk, "descripcion": "Llegó tarde", "archivo": archivo}

    def crear(self, archivo):
        self.client.force_login(self.instructor)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("novedades:crear"), self.datos(archivo))

    def test_crea_con_nombre_aleatorio(self):
        respuesta = self.crear(pdf("../../etc/passwd.pdf"))
        novedad = Novedad.objects.get()
        self.assertRedirects(respuesta, novedad.get_absolute_url())
        self.assertEqual(novedad.creado_por, self.instructor)
        self.assertRegex(novedad.archivo.name, r"^evidencias/\d{4}/\d{2}/[0-9a-f]{32}\.pdf$")
        self.assertTrue(Path(novedad.archivo.path).is_file())

    def test_rechaza_extension(self):
        self.assertEqual(self.crear(SimpleUploadedFile("virus.exe", PDF)).status_code, 200)
        self.assertEqual(Novedad.objects.count(), 0)

    def test_rechaza_contenido_falso(self):
        respuesta = self.crear(pdf("falso.pdf", b"<script>alert(1)</script>"))
        self.assertContains(respuesta, "no corresponde a su extensión")
        self.assertEqual(Novedad.objects.count(), 0)

    def test_rechaza_archivo_grande(self):
        respuesta = self.crear(pdf("grande.pdf", PDF + b"0" * (5 * 1024 * 1024)))
        self.assertContains(respuesta, "no puede pesar más de 5 MB")
        self.assertEqual(Novedad.objects.count(), 0)

    def test_acepta_png(self):
        self.crear(SimpleUploadedFile("foto.png", PNG))
        self.assertEqual(Novedad.objects.count(), 1)

    def test_descarga_lleva_tipo_y_numero_de_documento_del_aprendiz(self):
        novedad = self.novedad()
        self.client.force_login(self.ana)
        respuesta = self.client.get(reverse("novedades:evidencia", args=[novedad.pk]))
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(b"".join(respuesta.streaming_content), PDF)
        self.assertIn('filename="novedad-CC1001.pdf"', respuesta["Content-Disposition"])
        self.assertTrue(respuesta["Content-Disposition"].startswith("attachment"))

    def test_nombre_usa_el_tipo_de_documento_real(self):
        ti = self.usuario("menor", Usuario.Rol.APRENDIZ, "99887766", ficha=self.ficha, tipo_doc="TI")
        novedad = self.novedad(ti, archivo=SimpleUploadedFile("a.jpeg", b"\xff\xd8\xff" + b"0" * 20))
        self.assertEqual(novedad.nombre_descarga, "novedad-TI99887766.jpeg")

    def test_vista_previa_solo_para_imagenes(self):
        imagen = self.novedad(archivo=SimpleUploadedFile("foto.png", PNG))
        documento = self.novedad()
        self.client.force_login(self.admin)
        previa = self.client.get(reverse("novedades:evidencia", args=[imagen.pk]) + "?ver=1")
        self.assertTrue(previa["Content-Disposition"].startswith("inline"))
        self.assertEqual(previa["Content-Type"], "image/png")
        self.assertIn("sandbox", previa["Content-Security-Policy"])
        forzado = self.client.get(reverse("novedades:evidencia", args=[documento.pk]) + "?ver=1")
        self.assertTrue(forzado["Content-Disposition"].startswith("attachment"))

    def test_descarga_ajena_es_404(self):
        novedad = self.novedad(self.ana)
        self.client.force_login(self.beto)
        self.assertEqual(self.client.get(reverse("novedades:evidencia", args=[novedad.pk])).status_code, 404)

    def test_descarga_anonima_redirige(self):
        self.assertEqual(self.client.get(reverse("novedades:evidencia", args=[self.novedad().pk])).status_code, 302)

    def test_archivo_perdido_en_disco_es_404(self):
        novedad = self.novedad()
        Path(novedad.archivo.path).unlink()
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("novedades:evidencia", args=[novedad.pk])).status_code, 404)

    def test_eliminar_borra_el_archivo(self):
        novedad = self.novedad()
        ruta = Path(novedad.archivo.path)
        self.client.force_login(self.instructor)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("novedades:eliminar", args=[novedad.pk]))
        self.assertFalse(ruta.exists())

    def test_reemplazar_borra_el_anterior(self):
        novedad = self.novedad()
        anterior = Path(novedad.archivo.path)
        self.client.force_login(self.instructor)
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("novedades:editar", args=[novedad.pk]), self.datos(SimpleUploadedFile("nueva.png", PNG)))
        novedad.refresh_from_db()
        self.assertFalse(anterior.exists())
        self.assertTrue(Path(novedad.archivo.path).is_file())

    def test_editar_sin_cambiar_archivo_lo_conserva(self):
        novedad = self.novedad()
        ruta = Path(novedad.archivo.path)
        self.client.force_login(self.instructor)
        datos = {"tipo": "DISC", "aprendiz": self.ana.pk, "descripcion": "Cambio"}
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.client.post(reverse("novedades:editar", args=[novedad.pk]), datos)
        self.assertRedirects(respuesta, novedad.get_absolute_url())
        novedad.refresh_from_db()
        self.assertEqual(novedad.tipo, "DISC")
        self.assertEqual(Path(novedad.archivo.path), ruta)
        self.assertTrue(ruta.exists())


class FormularioTest(NovedadTestCase):
    def test_coordinador_no_asigna_aprendices_de_otra_sede(self):
        self.client.force_login(self.coordinador)
        datos = {"tipo": "ACAD", "aprendiz": self.lejano.pk, "descripcion": "x", "archivo": pdf()}
        self.assertEqual(self.client.post(reverse("novedades:crear"), datos).status_code, 200)
        self.assertEqual(Novedad.objects.count(), 0)

    def test_ambiente_inactivo_no_se_ofrece(self):
        from catalogo.models import Ambiente

        inactivo = Ambiente.objects.create(codigo="A-999", ubicacion="X", sede=self.sede, estado="IN")
        self.client.force_login(self.instructor)
        form = self.client.get(reverse("novedades:crear")).context["form"]
        self.assertNotIn(inactivo, form.fields["ambiente"].queryset)
        self.assertIn(self.ambiente, form.fields["ambiente"].queryset)

    def test_campos_con_estilo_bootstrap(self):
        self.client.force_login(self.instructor)
        respuesta = self.client.get(reverse("novedades:crear"))
        self.assertContains(respuesta, 'class="form-select"')
        self.assertContains(respuesta, 'class="form-control"')

    def test_errores_se_marcan_en_rojo(self):
        self.client.force_login(self.instructor)
        respuesta = self.client.post(reverse("novedades:crear"), {"tipo": "ACAD"})
        self.assertContains(respuesta, "is-invalid")

    def test_aprendiz_con_novedades_no_se_puede_borrar(self):
        from django.db.models import ProtectedError

        self.novedad()
        with self.assertRaises(ProtectedError):
            self.ana.delete()


class ApiTest(NovedadTestCase):
    def setUp(self):
        self.api = APIClient()

    def test_requiere_sesion(self):
        self.assertEqual(self.api.get("/api/novedades/").status_code, 403)

    def test_instructor_crea_novedad(self):
        self.api.force_authenticate(self.instructor)
        datos = {"tipo": "DISC", "aprendiz": self.ana.pk, "descripcion": "Falta", "archivo": pdf()}
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.api.post("/api/novedades/", datos, format="multipart")
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertNotIn("archivo", respuesta.data)
        self.assertTrue(respuesta.data["archivo_url"].endswith(f"/{respuesta.data['id']}/evidencia/"))
        self.assertEqual(respuesta.data["creado_por"], self.instructor.pk)
        self.assertEqual(respuesta.data["aprendiz_nombre"], "Ana")

    def test_valida_el_archivo(self):
        self.api.force_authenticate(self.instructor)
        datos = {"tipo": "DISC", "aprendiz": self.ana.pk, "descripcion": "Falta", "archivo": pdf("a.pdf", b"nada")}
        respuesta = self.api.post("/api/novedades/", datos, format="multipart")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("archivo", respuesta.data)

    def test_aprendiz_no_escribe_pero_lee(self):
        self.api.force_authenticate(self.ana)
        datos = {"tipo": "DISC", "aprendiz": self.ana.pk, "descripcion": "x", "archivo": pdf()}
        self.assertEqual(self.api.post("/api/novedades/", datos, format="multipart").status_code, 403)
        self.assertEqual(self.api.get("/api/novedades/").status_code, 200)

    def test_solo_lista_las_visibles(self):
        self.novedad(self.ana)
        self.novedad(self.beto)
        self.api.force_authenticate(self.ana)
        self.assertEqual(self.api.get("/api/novedades/").data["count"], 1)

    def test_no_asigna_aprendiz_fuera_de_la_sede(self):
        self.api.force_authenticate(self.coordinador)
        datos = {"tipo": "ACAD", "aprendiz": self.lejano.pk, "descripcion": "x", "archivo": pdf()}
        self.assertEqual(self.api.post("/api/novedades/", datos, format="multipart").status_code, 400)
