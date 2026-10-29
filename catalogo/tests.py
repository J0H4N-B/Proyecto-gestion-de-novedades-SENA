from rest_framework.test import APIClient

from core.testing import BaseTest


class CatalogoApiTest(BaseTest):
    def setUp(self):
        self.api = APIClient()

    def test_lectura_para_todos_escritura_para_staff(self):
        datos = {"codigo": "S3", "nombre": "N", "direccion": "D"}
        self.api.force_authenticate(self.ana)
        self.assertEqual(self.api.get("/api/sedes/").status_code, 200)
        self.assertEqual(self.api.post("/api/sedes/", datos).status_code, 403)
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.post("/api/sedes/", datos).status_code, 201)

    def test_borrar_catalogo_en_uso_no_rompe(self):
        self.api.force_authenticate(self.admin)
        self.assertEqual(self.api.delete(f"/api/sedes/{self.sede.pk}/").status_code, 400)

    def test_fichas_y_ambientes_se_listan(self):
        self.api.force_authenticate(self.instructor)
        self.assertEqual(self.api.get("/api/fichas/").data["count"], 2)
        self.assertEqual(self.api.get("/api/ambientes/").data["count"], 1)
        self.assertEqual(self.api.get("/api/programas/").data["count"], 1)
