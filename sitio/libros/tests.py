from unittest.mock import patch

from django.test import TestCase

from libros import servicios
from libros.models import Categoria, Libro


class ResenasTests(TestCase):
    """La vista de reseñas consume el microservicio: hay que probar los dos casos."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Ficción")
        self.libro = Libro.objects.create(
            titulo="Ficciones",
            isbn="9788420633997",
            anio_publicacion=1944,
            paginas=176,
            categoria=self.categoria,
        )

    def test_muestra_las_resenas_que_devuelve_el_microservicio(self):
        respuesta_del_servicio = {
            "libro_id": self.libro.id,
            "cantidad": 1,
            "promedio": 5.0,
            "resenas": [
                {
                    "id": 1,
                    "libro_id": self.libro.id,
                    "lector": "Ana Gómez",
                    "puntaje": 5,
                    "comentario": "Imperdible",
                    "creada_en": "2026-09-18T10:00:00+00:00",
                }
            ],
        }

        with patch("libros.servicios.obtener_resenas", return_value=respuesta_del_servicio):
            respuesta = self.client.get(f"/libro/{self.libro.id}/resenas/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ana Gómez")
        self.assertContains(respuesta, "Imperdible")

    def test_si_el_microservicio_no_responde_la_pagina_igual_carga(self):
        fallo = servicios.MicroservicioNoDisponible("timeout")

        with patch("libros.servicios.obtener_resenas", side_effect=fallo):
            respuesta = self.client.get(f"/libro/{self.libro.id}/resenas/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no está disponible")


class AsistenteTests(TestCase):
    """La vista del asistente consulta una API externa: hay que probar los dos casos."""

    def test_muestra_la_respuesta_que_devuelve_la_ia(self):
        with patch(
            "libros.servicios.preguntar_al_asistente",
            return_value="Hay 3 libros de Ficción.",
        ):
            respuesta = self.client.post(
                "/asistente/",
                {"pregunta": "¿Cuántos libros de ficción hay?"},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Hay 3 libros de Ficción.")

    def test_si_la_ia_no_responde_la_pagina_igual_carga(self):
        fallo = servicios.IANoDisponible("timeout")

        with patch("libros.servicios.preguntar_al_asistente", side_effect=fallo):
            respuesta = self.client.post(
                "/asistente/",
                {"pregunta": "¿Qué libros hay?"},
            )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "No se pudo consultar a la IA")

    def test_armar_contexto_biblioteca_incluye_los_datos_del_orm(self):
        categoria = Categoria.objects.create(nombre="Ficción")
        libro = Libro.objects.create(
            titulo="Ficciones",
            isbn="9788420633997",
            anio_publicacion=1944,
            paginas=176,
            categoria=categoria,
        )

        contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("LIBROS:", contexto)
        self.assertIn("Ficciones", contexto)
        self.assertIn("categoria Ficción", contexto)

    def test_armar_contexto_biblioteca_incluye_el_funcionamiento_de_la_app(self):
        contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("COMO FUNCIONA UN PRESTAMO:", contexto)
        self.assertIn("disponible", contexto)
        self.assertIn("devolver", contexto)
