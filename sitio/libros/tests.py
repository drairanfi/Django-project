from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse

from libros import servicios
from prestamos.models import Lector


class ResenasTests(TestCase):
    """La vista de reseñas consume el microservicio: hay que probar los dos casos."""

    def setUp(self):
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

    def test_muestra_las_resenas_que_devuelve_el_microservicio(self):
        respuesta_del_servicio = {
            "libro_id": 1,
            "cantidad": 1,
            "promedio": 5.0,
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

        with patch(
            "libros.servicios.obtener_libro", return_value=(self.libro, "python")
        ), patch(
            "libros.servicios.obtener_resenas_con_origen",
            return_value=(respuesta_del_servicio, "http://127.0.0.1:8001/api"),
        ):
            respuesta = self.client.get("/libro/1/resenas/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ana Gómez")
        self.assertContains(respuesta, "Imperdible")

    def test_si_el_microservicio_no_responde_la_pagina_igual_carga(self):
        fallo = servicios.MicroservicioNoDisponible("timeout")

        with patch(
            "libros.servicios.obtener_libro", return_value=(self.libro, "python")
        ), patch("libros.servicios.obtener_resenas_con_origen", side_effect=fallo):
            respuesta = self.client.get("/libro/1/resenas/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "no está disponible")


class ResilienciaLibrosTests(TestCase):
    """La lectura de libros tiene resiliencia: si el primario falla, usa el respaldo."""

    @override_settings(
        MICROSERVICIOS_LIBROS={
            "python": "http://127.0.0.1:8001/api",
            "nodejs": "http://127.0.0.1:8002/api",
            "java": "http://127.0.0.1:8003/api",
            "php": "http://127.0.0.1:8004/api",
        },
        MICROSERVICIOS_LIBROS_ORDEN_LECTURA=["python", "nodejs", "java", "php"],
    )
    def test_cae_al_respaldo_cuando_el_primario_falla(self):
        fallo = servicios.MicroservicioNoDisponible("timeout")
        datos_respaldo = {"cantidad": 1, "libros": []}

        with patch(
            "libros.servicios._pedir",
            side_effect=[fallo, datos_respaldo],
        ):
            datos, servicio, caidos = servicios.obtener_libros()

        self.assertEqual(datos, datos_respaldo)
        self.assertEqual(servicio, "nodejs")
        self.assertEqual(caidos, ["python"])

    @override_settings(
        MICROSERVICIOS_LIBROS={
            "python": "http://127.0.0.1:8001/api",
            "nodejs": "http://127.0.0.1:8002/api",
            "java": "http://127.0.0.1:8003/api",
            "php": "http://127.0.0.1:8004/api",
        },
        MICROSERVICIOS_LIBROS_ORDEN_LECTURA=["python", "nodejs", "java", "php"],
    )
    def test_levanta_si_todos_los_servicios_fallan(self):
        fallo = servicios.MicroservicioNoDisponible("timeout")

        with patch("libros.servicios._pedir", side_effect=[fallo, fallo, fallo, fallo]):
            with self.assertRaises(servicios.MicroservicioNoDisponible):
                servicios.obtener_libros()

    @override_settings(
        MICROSERVICIOS_LIBROS={
            "python": "http://127.0.0.1:8001/api",
            "nodejs": "http://127.0.0.1:8002/api",
            "java": "http://127.0.0.1:8003/api",
            "php": "http://127.0.0.1:8004/api",
        },
        MICROSERVICIOS_LIBROS_ORDEN_LECTURA=["python", "nodejs", "java", "php"],
    )
    def test_cae_al_respaldo_cuando_el_primario_no_encuentra_el_libro(self):
        no_encontrado = servicios.LibroNoEncontrado("el libro no existe")
        datos_respaldo = {"id": 2, "titulo": "El Aleph"}

        with patch(
            "libros.servicios._pedir",
            side_effect=[no_encontrado, datos_respaldo],
        ):
            datos, servicio = servicios.obtener_libro(1)

        self.assertEqual(datos, datos_respaldo)
        self.assertEqual(servicio, "nodejs")

    def test_la_vista_inicio_avisa_que_servicio_se_cayo_y_cual_se_uso(self):
        """Si Java y PHP caen pero NodeJS responde, la home lo muestra."""
        con_libros = {
            "cantidad": 1,
            "libros": [{
                "id": 1,
                "titulo": "Ficciones",
                "isbn": "9788420633997",
                "anio_publicacion": 1944,
                "paginas": 176,
                "disponible": True,
                "categoria": "Ficción",
                "autores": "Jorge Luis Borges",
            }],
        }

        with patch(
            "libros.servicios.obtener_libros",
            return_value=(con_libros, "nodejs", ["python", "java"]),
        ):
            respuesta = self.client.get("/")

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "python, java")
        self.assertContains(respuesta, "nodejs")
        self.assertContains(respuesta, "Ficciones")


class CrudLibroTests(TestCase):
    """El CRUD de libros crea, edita y elimina a través del microservicio elegido."""

    def setUp(self):
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

    def test_crear_libro_guarda_en_el_microservicio_y_redirige(self):
        with patch(
            "libros.servicios.crear_libro",
            return_value=self.libro,
        ) as crear_mock:
            respuesta = self.client.post(
                reverse("libros:crear_libro"),
                {
                    "titulo": "Ficciones",
                    "isbn": "9788420633997",
                    "anio_publicacion": 1944,
                    "paginas": 176,
                    "disponible": "on",
                    "categoria": "Ficción",
                    "autores": "Jorge Luis Borges",
                    "servicio": "nodejs",
                },
            )

        self.assertRedirects(respuesta, reverse("libros:detalle_libro", args=[1]))
        crear_mock.assert_called_once()
        llamada = crear_mock.call_args
        self.assertEqual(llamada.args[0], "nodejs")

    def test_crear_libro_invalido_muestra_errores_sin_redirigir(self):
        respuesta = self.client.post(
            reverse("libros:crear_libro"),
            {"titulo": "", "isbn": ""},
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "libro")

    def test_editar_libro_envia_al_microservicio_elegido(self):
        with patch(
            "libros.servicios.obtener_libro",
            return_value=(self.libro, "python"),
        ), patch(
            "libros.servicios.editar_libro",
            return_value={**self.libro, "titulo": "Ficciones (edición 2000)"},
        ) as editar_mock:
            respuesta = self.client.post(
                reverse("libros:editar_libro", args=[1]),
                {
                    "titulo": "Ficciones (edición 2000)",
                    "isbn": "9788420633997",
                    "anio_publicacion": 2000,
                    "paginas": 180,
                    "categoria": "Ficción",
                    "autores": "Jorge Luis Borges",
                    "servicio": "java",
                },
            )

        self.assertRedirects(respuesta, reverse("libros:detalle_libro", args=[1]))
        editar_mock.assert_called_once()
        self.assertEqual(editar_mock.call_args.args[0], "java")

    def test_eliminar_libro_get_muestra_confirmacion(self):
        with patch(
            "libros.servicios.obtener_libro",
            return_value=(self.libro, "python"),
        ):
            respuesta = self.client.get(reverse("libros:eliminar_libro", args=[1]))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Ficciones")

    def test_eliminar_libro_post_borra_en_el_microservicio(self):
        with patch(
            "libros.servicios.obtener_libro",
            return_value=(self.libro, "python"),
        ), patch(
            "libros.servicios.eliminar_libro",
            return_value=self.libro,
        ) as eliminar_mock:
            respuesta = self.client.post(
                reverse("libros:eliminar_libro", args=[1]),
                {"servicio": "php"},
            )

        self.assertRedirects(respuesta, reverse("libros:inicio"))
        eliminar_mock.assert_called_once()

    def test_crear_libro_cae_a_otro_servicio_si_el_elegido_esta_caido(self):
        """Resiliencia en escritura: si el servicio elegido no responde, se usa otro."""
        fallo = servicios.MicroservicioNoDisponible("timeout")

        with patch(
            "libros.servicios.crear_libro",
            side_effect=[fallo, self.libro],
        ) as crear_mock:
            respuesta = self.client.post(
                reverse("libros:crear_libro"),
                {
                    "titulo": "Ficciones",
                    "isbn": "9788420633997",
                    "anio_publicacion": 1944,
                    "paginas": 176,
                    "disponible": "on",
                    "categoria": "Ficción",
                    "autores": "Jorge Luis Borges",
                    "servicio": "java",
                },
            )

        self.assertRedirects(respuesta, reverse("libros:detalle_libro", args=[1]))
        # Primero se intentó java (el elegido) y después cayó a python.
        self.assertEqual(crear_mock.call_count, 2)
        self.assertEqual(crear_mock.call_args_list[0].args[0], "java")
        self.assertEqual(crear_mock.call_args_list[1].args[0], "python")


class AsistenteTests(TestCase):
    """La vista del asistente consulta una API externa: hay que probar los dos casos."""

    def setUp(self):
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

    def test_armar_contexto_biblioteca_incluye_los_datos_del_microservicio(self):
        con_libros = {"cantidad": 1, "libros": [self.libro]}

        with patch("libros.servicios.obtener_libros", return_value=(con_libros, "python", [])), patch(
            "libros.servicios.obtener_todas_resenas", return_value={"resenas": []}
        ), patch("libros.servicios.obtener_resenas", return_value={}):
            contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("LIBROS:", contexto)
        self.assertIn("Ficciones", contexto)
        self.assertIn("categoria Ficción", contexto)

    def test_armar_contexto_biblioteca_incluye_el_funcionamiento_de_la_app(self):
        with patch("libros.servicios.obtener_libros", return_value=({"libros": []}, "python", [])), patch(
            "libros.servicios.obtener_todas_resenas", return_value={"resenas": []}
        ), patch("libros.servicios.obtener_resenas", return_value={}):
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

        with patch("libros.servicios.obtener_libros", return_value=({"libros": []}, "python", [])), patch(
            "libros.servicios.obtener_todas_resenas", return_value=con_resenas
        ), patch("libros.servicios.obtener_resenas", return_value={}):
            contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("RESENAS:", contexto)
        self.assertIn("Ana Gómez", contexto)
        self.assertIn("le puso 5", contexto)

    def test_armar_contexto_biblioteca_degrada_si_el_microservicio_falla(self):
        fallo = servicios.MicroservicioNoDisponible("timeout")

        with patch("libros.servicios.obtener_libros", side_effect=fallo), patch(
            "libros.servicios.obtener_todas_resenas", side_effect=fallo
        ), patch("libros.servicios.obtener_resenas", side_effect=fallo):
            contexto = servicios.armar_contexto_biblioteca()

        self.assertIn("RESENAS:", contexto)
        self.assertIn("No hay reseñas cargadas", contexto)