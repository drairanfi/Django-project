from unittest.mock import patch

from django.test import TestCase

from prestamos.models import Lector, Prestamo


class BibliotecaTests(TestCase):
    """Las vistas leen libros desde el microservicio, no del ORM: hay que mockearlo."""

    def setUp(self):
        self.lector = Lector.objects.create(
            nombre="Ana García", email="ana@mail.com"
        )
        self.libro = {
            "id": 1,
            "titulo": "Ficciones",
            "isbn": "9788420633997",
            "anio_publicacion": 1944,
            "paginas": 176,
            "disponible": True,
            "categoria": "Ficción",
            "autores": "Jorge Luis Borges",
        }

    def test_detalle_libro_muestra_datos(self):
        with patch(
            "libros.servicios.obtener_libro",
            return_value=(self.libro, "python"),
        ):
            respuesta = self.client.get("/libro/1/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ficciones")

    def test_filtrar_por_categoria(self):
        with patch(
            "libros.servicios.obtener_libros",
            return_value=({"cantidad": 1, "libros": [self.libro]}, "python", []),
        ):
            respuesta = self.client.get("/categoria/Ficción/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ficciones")

    def test_prestar_y_devolver(self):
        with patch(
            "libros.servicios.obtener_libro",
            return_value=(self.libro, "python"),
        ), patch(
            "libros.servicios.editar_libro",
            return_value=self.libro,
        ):
            self.client.post("/prestamos/prestar/1/", {"lector_id": self.lector.id})

        prestamo = Prestamo.objects.get()
        self.assertEqual(prestamo.estado, "activo")
        self.assertEqual(prestamo.libro_id, 1)

        with patch(
            "libros.servicios.obtener_libro",
            return_value=(self.libro, "python"),
        ), patch(
            "libros.servicios.editar_libro",
            return_value=self.libro,
        ):
            self.client.get(f"/prestamos/devolver/{prestamo.id}/")

        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, "devuelto")