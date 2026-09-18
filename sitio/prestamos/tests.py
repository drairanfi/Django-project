from django.test import TestCase

from libros.models import Categoria, Libro
from prestamos.models import Lector, Prestamo


class BibliotecaTests(TestCase):
    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Ficción")
        self.libro = Libro.objects.create(
            titulo="Ficciones",
            isbn="9788420633997",
            anio_publicacion=1944,
            paginas=176,
            categoria=self.categoria,
        )
        self.lector = Lector.objects.create(
            nombre="Ana García", email="ana@mail.com"
        )

    def test_detalle_libro_muestra_datos(self):
        respuesta = self.client.get(f"/libro/{self.libro.id}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ficciones")

    def test_filtrar_por_categoria(self):
        respuesta = self.client.get(f"/categoria/{self.categoria.id}/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ficciones")

    def test_prestar_y_devolver(self):
        self.client.post(f"/prestamos/prestar/{self.libro.id}/", {"lector_id": self.lector.id})

        prestamo = Prestamo.objects.get()
        self.assertEqual(prestamo.estado, "activo")
        self.libro.refresh_from_db()
        self.assertFalse(self.libro.disponible)

        self.client.get(f"/prestamos/devolver/{prestamo.id}/")
        prestamo.refresh_from_db()
        self.assertEqual(prestamo.estado, "devuelto")
        self.libro.refresh_from_db()
        self.assertTrue(self.libro.disponible)