from datetime import timedelta
from pathlib import Path

from django.contrib.admin.models import LogEntry
from django.contrib.auth.models import Permission
from django.test import Client
from django.urls import reverse
from django.utils import timezone
from PIL import Image
from rest_framework.test import APIClient

from core.testing import CLAVE, BaseTest, imagen

from .models import AccesoBloqueado, Usuario


class LoginTest(BaseTest):
    def test_anonimo_va_al_login(self):
        respuesta = self.client.get(reverse("novedades:lista"))
        self.assertRedirects(respuesta, f"{reverse('cuentas:ingresar')}?next=/")

    def test_ingreso_correcto(self):
        respuesta = self.client.post(reverse("cuentas:ingresar"), {"username": "ana", "password": CLAVE})
        self.assertRedirects(respuesta, reverse("novedades:lista"))

    def test_clave_incorrecta_no_ingresa(self):
        respuesta = self.client.post(reverse("cuentas:ingresar"), {"username": "ana", "password": "mala"})
        self.assertEqual(respuesta.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_pagina_carga_el_script_del_ojo_para_la_clave(self):
        respuesta = self.client.get(reverse("cuentas:ingresar"))
        self.assertContains(respuesta, 'type="password"')
        self.assertContains(respuesta, "core/js/app.js")
        self.assertContains(respuesta, reverse("cuentas:registro"))

    def test_bloqueo_tras_cinco_fallos(self):
        for _ in range(5):
            self.client.post(reverse("cuentas:ingresar"), {"username": "ana", "password": "mala"})
        respuesta = self.client.post(reverse("cuentas:ingresar"), {"username": "ana", "password": CLAVE})
        self.assertContains(respuesta, "Demasiados intentos", status_code=429)

    def test_salir_solo_por_post(self):
        self.client.force_login(self.ana)
        self.assertEqual(self.client.get(reverse("cuentas:salir")).status_code, 405)
        self.client.post(reverse("cuentas:salir"))
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_hash_argon2(self):
        self.assertTrue(self.ana.password.startswith("argon2"))

    def test_ya_autenticado_no_ve_el_login(self):
        self.client.force_login(self.ana)
        self.assertRedirects(self.client.get(reverse("cuentas:ingresar")), reverse("novedades:lista"))


class RegistroTest(BaseTest):
    def datos(self, **cambios):
        datos = {
            "first_name": "Laura", "last_name": "Pardo", "tipo_doc": "CC", "numero_documento": "5550001",
            "ficha": self.ficha_otra.pk, "email": "laura@x.co", "telefono": "3001112233",
            "username": "laura", "password1": "una-clave-larga-77", "password2": "una-clave-larga-77",
        }
        return {**datos, **cambios}

    def test_pantalla_de_registro(self):
        respuesta = self.client.get(reverse("cuentas:registro"))
        self.assertContains(respuesta, "Crea tu cuenta")
        self.assertContains(respuesta, "2900002")

    def test_crea_aprendiz_con_sede_de_su_ficha_y_abre_sesion(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos())
        self.assertRedirects(respuesta, reverse("novedades:lista"))
        nuevo = Usuario.objects.get(username="laura")
        self.assertEqual(nuevo.rol, Usuario.Rol.APRENDIZ)
        self.assertEqual(nuevo.sede, self.otra_sede)
        self.assertFalse(nuevo.is_staff or nuevo.is_superuser)
        self.assertTrue(nuevo.password.startswith("argon2"))
        self.assertEqual(int(self.client.session["_auth_user_id"]), nuevo.pk)

    def test_no_se_puede_elegir_rol_ni_permisos(self):
        datos = self.datos(rol="coordinador", is_superuser="on", is_staff="on")
        self.client.post(reverse("cuentas:registro"), datos)
        nuevo = Usuario.objects.get(username="laura")
        self.assertEqual(nuevo.rol, Usuario.Rol.APRENDIZ)
        self.assertFalse(nuevo.is_staff or nuevo.is_superuser)

    def test_documento_repetido_se_rechaza(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos(numero_documento="1001"))
        self.assertContains(respuesta, "Ya existe una cuenta con ese tipo y número de documento")
        self.assertFalse(Usuario.objects.filter(username="laura").exists())

    def test_clave_debil_se_rechaza(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos(password1="12345678", password2="12345678"))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="laura").exists())

    def test_ficha_es_obligatoria(self):
        respuesta = self.client.post(reverse("cuentas:registro"), self.datos(ficha=""))
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(username="laura").exists())

    def test_con_sesion_no_se_registra(self):
        self.client.force_login(self.ana)
        self.assertRedirects(self.client.get(reverse("cuentas:registro")), reverse("novedades:lista"))


class PerfilTest(BaseTest):
    def datos(self, **extra):
        return {"first_name": "Ana", "last_name": "Gómez", "email": "ana@x.co", "telefono": "300", **extra}

    def guardar(self, usuario, **extra):
        self.client.force_login(usuario)
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(reverse("cuentas:perfil"), self.datos(**extra))

    def test_edita_datos(self):
        respuesta = self.guardar(self.ana, last_name="Rojas")
        self.assertRedirects(respuesta, reverse("cuentas:perfil"))
        self.ana.refresh_from_db()
        self.assertEqual(self.ana.last_name, "Rojas")
        self.assertEqual(self.ana.rol, Usuario.Rol.APRENDIZ)

    def test_foto_se_recorta_y_se_guarda_como_jpeg(self):
        self.guardar(self.ana, foto=imagen("grande.png", tamano=(900, 500)))
        self.ana.refresh_from_db()
        self.assertRegex(self.ana.foto.name, r"^fotos/\d{4}/\d{2}/[0-9a-f]{32}\.jpg$")
        with Image.open(self.ana.foto.path) as guardada:
            self.assertEqual((guardada.format, guardada.size), ("JPEG", (320, 320)))

    def test_rechaza_archivo_que_no_es_imagen(self):
        from django.core.files.uploadedfile import SimpleUploadedFile

        falso = SimpleUploadedFile("foto.png", b"esto no es una imagen")
        respuesta = self.guardar(self.ana, foto=falso)
        self.assertEqual(respuesta.status_code, 200)
        self.ana.refresh_from_db()
        self.assertFalse(self.ana.foto)

    def test_reemplazar_borra_la_foto_anterior(self):
        self.guardar(self.ana, foto=imagen())
        self.ana.refresh_from_db()
        anterior = Path(self.ana.foto.path)
        self.guardar(self.ana, foto=imagen("otra.png"))
        self.ana.refresh_from_db()
        self.assertFalse(anterior.exists())
        self.assertTrue(Path(self.ana.foto.path).is_file())

    def test_quitar_foto(self):
        self.guardar(self.ana, foto=imagen())
        self.ana.refresh_from_db()
        ruta = Path(self.ana.foto.path)
        self.guardar(self.ana, quitar_foto="on")
        self.ana.refresh_from_db()
        self.assertFalse(self.ana.foto)
        self.assertFalse(ruta.exists())

    def test_sin_foto_se_muestran_iniciales(self):
        self.client.force_login(self.ana)
        self.assertContains(self.client.get(reverse("novedades:lista")), ">A<")

    def test_login_no_borra_la_foto(self):
        self.guardar(self.ana, foto=imagen())
        self.ana.refresh_from_db()
        ruta = Path(self.ana.foto.path)
        self.client.post(reverse("cuentas:salir"))
        with self.captureOnCommitCallbacks(execute=True):
            self.client.post(reverse("cuentas:ingresar"), {"username": "ana", "password": CLAVE})
        self.assertTrue(ruta.exists())


class FotoTest(BaseTest):
    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.ana.foto = imagen()
        cls.ana.save()

    def test_la_ve_su_dueno_y_los_gestores(self):
        for usuario in (self.ana, self.instructor, self.coordinador, self.admin):
            self.client.force_login(usuario)
            respuesta = self.client.get(reverse("cuentas:foto", args=[self.ana.pk]))
            self.assertEqual(respuesta.status_code, 200, usuario)
            self.assertEqual(respuesta["Content-Type"], "image/jpeg")
            self.assertTrue(respuesta["Content-Disposition"].startswith("inline"))

    def test_otro_aprendiz_no_la_ve(self):
        self.client.force_login(self.beto)
        self.assertEqual(self.client.get(reverse("cuentas:foto", args=[self.ana.pk])).status_code, 404)

    def test_anonimo_redirige(self):
        self.assertEqual(self.client.get(reverse("cuentas:foto", args=[self.ana.pk])).status_code, 302)

    def test_sin_foto_es_404(self):
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(reverse("cuentas:foto", args=[self.beto.pk])).status_code, 404)

    def test_la_url_cambia_con_la_foto(self):
        self.assertIn("?v=", self.ana.foto_url)
        self.assertEqual(self.beto.foto_url, "")


class ClaveTest(BaseTest):
    def test_cambiar_clave(self):
        self.client.force_login(self.ana)
        datos = {"old_password": CLAVE, "new_password1": "una-clave-nueva-99", "new_password2": "una-clave-nueva-99"}
        self.assertRedirects(self.client.post(reverse("cuentas:clave"), datos), reverse("cuentas:clave_lista"))
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password("una-clave-nueva-99"))

    def test_rechaza_clave_corta(self):
        self.client.force_login(self.ana)
        datos = {"old_password": CLAVE, "new_password1": "corta1", "new_password2": "corta1"}
        self.assertEqual(self.client.post(reverse("cuentas:clave"), datos).status_code, 200)


class DesbloqueoTest(BaseTest):
    url = "/admin/cuentas/accesobloqueado/"

    def fallar(self, veces, username="ana"):
        for _ in range(veces):
            self.client.post(reverse("cuentas:ingresar"), {"username": username, "password": "mala"})

    def cliente_admin(self):
        cliente = Client()
        cliente.force_login(self.admin)
        return cliente

    def test_lista_solo_a_los_bloqueados(self):
        self.fallar(5, "ana")
        self.fallar(4, "beto")
        respuesta = self.cliente_admin().get(self.url)
        self.assertEqual([a.username for a in respuesta.context["cl"].result_list], ["ana"])

    def test_no_lista_bloqueos_vencidos(self):
        self.fallar(5)
        AccesoBloqueado.objects.update(attempt_time=timezone.now() - timedelta(minutes=16))
        self.assertEqual(len(self.cliente_admin().get(self.url).context["cl"].result_list), 0)

    def test_desbloquear_permite_volver_a_ingresar(self):
        self.fallar(5)
        bloqueado = AccesoBloqueado.objects.get()
        entrada = {"username": "ana", "password": CLAVE}
        self.assertEqual(self.client.post(reverse("cuentas:ingresar"), entrada).status_code, 429)
        respuesta = self.cliente_admin().post(
            self.url, {"action": "desbloquear", "_selected_action": [bloqueado.pk]}, follow=True
        )
        self.assertContains(respuesta, "Se desbloquearon 1 accesos")
        self.assertFalse(AccesoBloqueado.objects.exists())
        self.assertEqual(LogEntry.objects.filter(user=self.admin, change_message__contains="Desbloqueado").count(), 1)
        self.assertEqual(self.client.post(reverse("cuentas:ingresar"), entrada).status_code, 302)

    def test_no_ofrece_borrado_generico_ni_alta(self):
        self.fallar(5)
        cliente = self.cliente_admin()
        self.assertNotContains(cliente.get(self.url), 'value="delete_selected"')
        self.assertEqual(cliente.get(self.url + "add/").status_code, 403)

    def test_staff_sin_permiso_no_puede_desbloquear(self):
        self.fallar(5)
        gestor = self.usuario("gestor", Usuario.Rol.COORDINADOR, "4001", sede=self.sede, is_staff=True)
        gestor.user_permissions.add(Permission.objects.get(codename="view_accesobloqueado"))
        cliente = Client()
        cliente.force_login(gestor)
        bloqueado = AccesoBloqueado.objects.get()
        self.assertEqual(cliente.get(self.url).status_code, 200)
        cliente.post(self.url, {"action": "desbloquear", "_selected_action": [bloqueado.pk]})
        self.assertTrue(AccesoBloqueado.objects.exists())

    def test_usuario_normal_no_entra(self):
        cliente = Client()
        cliente.force_login(self.ana)
        self.assertEqual(cliente.get(self.url).status_code, 302)


class AdminTest(BaseTest):
    def test_alta_de_usuario_incluye_campos_del_centro(self):
        self.client.force_login(self.admin)
        respuesta = self.client.get("/admin/cuentas/usuario/add/")
        for campo in ("numero_documento", "rol", "foto"):
            self.assertContains(respuesta, campo)

    def test_listados_de_admin_cargan(self):
        self.client.force_login(self.admin)
        for ruta in ("cuentas/usuario", "catalogo/sede", "catalogo/programa", "catalogo/ficha",
                     "catalogo/ambiente", "novedades/novedad"):
            self.assertEqual(self.client.get(f"/admin/{ruta}/").status_code, 200, ruta)


class UsuariosApiTest(BaseTest):
    def setUp(self):
        self.api = APIClient()

    def test_solo_staff_y_sin_exponer_clave(self):
        self.api.force_authenticate(self.instructor)
        self.assertEqual(self.api.get("/api/usuarios/").status_code, 403)
        self.api.force_authenticate(self.admin)
        datos = {
            "username": "nuevo", "email": "n@x.co", "numero_documento": "5555", "rol": "aprendiz",
            "ficha": self.ficha.pk, "password": "otra-clave-larga-77",
        }
        respuesta = self.api.post("/api/usuarios/", datos)
        self.assertEqual(respuesta.status_code, 201, respuesta.data)
        self.assertNotIn("password", respuesta.data)
        nuevo = Usuario.objects.get(username="nuevo")
        self.assertTrue(nuevo.check_password("otra-clave-larga-77"))
        self.assertEqual(nuevo.sede, self.sede)

    def test_exige_clave_valida(self):
        self.api.force_authenticate(self.admin)
        base = {"username": "x", "numero_documento": "6666"}
        self.assertEqual(self.api.post("/api/usuarios/", base).status_code, 400)
        self.assertEqual(self.api.post("/api/usuarios/", {**base, "password": "12345678"}).status_code, 400)

    def test_cambiar_clave(self):
        self.api.force_authenticate(self.admin)
        respuesta = self.api.patch(f"/api/usuarios/{self.ana.pk}/", {"password": "clave-nueva-larga-88"})
        self.assertEqual(respuesta.status_code, 200)
        self.ana.refresh_from_db()
        self.assertTrue(self.ana.check_password("clave-nueva-larga-88"))

    def test_foto_por_api_se_normaliza(self):
        self.api.force_authenticate(self.admin)
        with self.captureOnCommitCallbacks(execute=True):
            respuesta = self.api.patch(
                f"/api/usuarios/{self.ana.pk}/", {"foto": imagen(tamano=(640, 480))}, format="multipart"
            )
        self.assertEqual(respuesta.status_code, 200, respuesta.data)
        self.assertNotIn("foto", respuesta.data)
        self.assertTrue(respuesta.data["foto_url"].endswith(f"/cuentas/foto/{self.ana.pk}/"))
        self.ana.refresh_from_db()
        with Image.open(self.ana.foto.path) as guardada:
            self.assertEqual(guardada.size, (320, 320))
