from unittest.mock import patch

from django.test import TestCase
from django.urls import reverse

from libros import servicios
from libros.models import Autor, Categoria, Libro


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

        with patch("libros.servicios.obtener_todas_resenas", return_value={"resenas": []}):
            contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("LIBROS:", contexto)
        self.assertIn("Ficciones", contexto)
        self.assertIn("categoria Ficción", contexto)

    def test_armar_contexto_biblioteca_incluye_el_funcionamiento_de_la_app(self):
        with patch("libros.servicios.obtener_todas_resenas", return_value={"resenas": []}):
            contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("COMO FUNCIONA UN PRESTAMO:", contexto)
        self.assertIn("disponible", contexto)
        self.assertIn("devolver", contexto)

    def test_armar_contexto_biblioteca_incluye_las_resenas_del_microservicio(self):
        con_resenas = {
            "cantidad": 1,
            "resenas": [
                {
                    "id": 1,
                    "libro_id": 1,
                    "lector": "Ana Gómez",
                    "puntaje": 5,
                    "comentario": "Imperdible",
                    "creada_en": "2026-09-18T10:00:00+00:00",
                }
            ],
        }

        with patch("libros.servicios.obtener_todas_resenas", return_value=con_resenas):
            contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("RESENAS:", contexto)
        self.assertIn("Ana Gómez", contexto)
        self.assertIn("le puso 5", contexto)

    def test_armar_contexto_biblioteca_degrada_si_el_microservicio_falla(self):
        fallo = servicios.MicroservicioNoDisponible("timeout")

        with patch("libros.servicios.obtener_todas_resenas", side_effect=fallo):
            contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("RESENAS:", contexto)
        self.assertIn("No hay reseñas cargadas", contexto)


class CrudLibroTests(TestCase):
    """El CRUD de libros: crear, editar y eliminar usando LibroForm."""

    def setUp(self):
        self.categoria = Categoria.objects.create(nombre="Ficción")
        self.autor = Autor.objects.create(nombre="Jorge Luis", apellido="Borges")
        self.libro = Libro.objects.create(
            titulo="Ficciones",
            isbn="9788420633997",
            anio_publicacion=1944,
            paginas=176,
            categoria=self.categoria,
        )
        self.libro.autores.add(self.autor)

    def test_crear_libro_guarda_y_redirige(self):
        respuesta = self.client.post(
            reverse("libros:crear_libro"),
            {
                "titulo": "El Aleph",
                "isbn": "9788420633988",
                "anio_publicacion": 1949,
                "paginas": 194,
                "disponible": "on",
                "categoria": self.categoria.id,
                "autores": [self.autor.id],
            },
        )

        self.assertRedirects(respuesta, reverse("libros:detalle_libro", args=[2]))
        libro = Libro.objects.get(isbn="9788420633988")
        self.assertEqual(libro.titulo, "El Aleph")
        self.assertEqual(libro.categoria, self.categoria)

    def test_crear_libro_con_categoria_y_autor_nuevos(self):
        respuesta = self.client.post(
            reverse("libros:crear_libro"),
            {
                "titulo": "Cuentos",
                "isbn": "9788420633977",
                "anio_publicacion": 1950,
                "paginas": 100,
                "categoria": self.categoria.id,
                "categoria_nueva": "Policial",
                "autores": [self.autor.id],
                "autores_nuevos": "Julio Verne",
            },
        )

        self.assertRedirects(respuesta, reverse("libros:detalle_libro", args=[2]))
        libro = Libro.objects.get(isbn="9788420633977")
        self.assertEqual(libro.categoria.nombre, "Policial")
        self.assertTrue(libro.autores.filter(apellido="Verne").exists())

    def test_crear_libro_invalido_muestra_errores_sin_redirigir(self):
        respuesta = self.client.post(
            reverse("libros:crear_libro"),
            {"titulo": "", "isbn": ""},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(Libro.objects.count(), 1)

    def test_editar_libro_actualiza_los_datos(self):
        respuesta = self.client.post(
            reverse("libros:editar_libro", args=[self.libro.id]),
            {
                "titulo": "Ficciones (edición 2000)",
                "isbn": self.libro.isbn,
                "anio_publicacion": 2000,
                "paginas": 180,
                "categoria": self.categoria.id,
                "autores": [self.autor.id],
            },
        )

        self.assertRedirects(respuesta, reverse("libros:detalle_libro", args=[self.libro.id]))
        self.libro.refresh_from_db()
        self.assertEqual(self.libro.titulo, "Ficciones (edición 2000)")
        self.assertEqual(self.libro.anio_publicacion, 2000)

    def test_eliminar_libro_get_muestra_confirmacion(self):
        respuesta = self.client.get(reverse("libros:eliminar_libro", args=[self.libro.id]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ficciones")

    def test_eliminar_libro_post_borra(self):
        respuesta = self.client.post(reverse("libros:eliminar_libro", args=[self.libro.id]))

        self.assertRedirects(respuesta, reverse("libros:inicio"))
        self.assertFalse(Libro.objects.filter(pk=self.libro.id).exists())
