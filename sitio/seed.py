import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "biblioteca.settings")

import django

django.setup()

from datetime import date

import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "libros"))

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files import File

from libros import servicios
from prestamos.models import Lector, Prestamo
from docentes.models import Docente


def crear_libros_en_microservicio():
    """Crea los libros de ejemplo en Supabase a través del microservicio.

    Idempotente: si el ISBN ya existe, no lo vuelve a insertar (la tabla tiene
    unique sobre isbn). Devuelve {isbn: libro_guardado}.
    """
    libros = [
        {
            "titulo": "Ficciones",
            "isbn": "9788420633997",
            "anio_publicacion": 1944,
            "paginas": 176,
            "categoria": "Ficción",
            "autores": "Jorge Luis Borges",
        },
        {
            "titulo": "El Aleph",
            "isbn": "9788420633988",
            "anio_publicacion": 1949,
            "paginas": 194,
            "categoria": "Ficción",
            "autores": "Jorge Luis Borges",
        },
        {
            "titulo": "Veinte mil leguas de viaje submarino",
            "isbn": "9788420680554",
            "anio_publicacion": 1870,
            "paginas": 418,
            "categoria": "Ficción",
            "autores": "Julio Verne",
        },
        {
            "titulo": "La vuelta al mundo en 80 días",
            "isbn": "9788420600989",
            "anio_publicacion": 1872,
            "paginas": 290,
            "categoria": "Ficción",
            "autores": "Julio Verne",
        },
        {
            "titulo": "Breve historia del tiempo",
            "isbn": "9788474238745",
            "anio_publicacion": 1988,
            "paginas": 256,
            "categoria": "Ciencia",
            "autores": "Stephen Hawking",
        },
        {
            "titulo": "El universo en una cáscara de nuez",
            "isbn": "9788466625973",
            "anio_publicacion": 2001,
            "paginas": 224,
            "categoria": "Ciencia",
            "autores": "Stephen Hawking",
        },
    ]

    guardados = {}
    for libro in libros:
        try:
            datos = servicios.crear_libro("python", libro)
            guardados[libro["isbn"]] = datos
            print(f"insertado: {libro['titulo']}")
        except servicios.MicroservicioNoDisponible as error:
            print(f"AVISO: el microservicio no está disponible para {libro['titulo']} ({error})")

    return guardados


def crear_datos():
    print("Creando datos de ejemplo...")

    ana = Lector.objects.get_or_create(
        nombre="Ana García", email="ana@mail.com", telefono="11-2222-3333"
    )[0]
    carlos = Lector.objects.get_or_create(
        nombre="Carlos Pérez", email="carlos@mail.com", telefono="11-4444-5555"
    )[0]

    libros = crear_libros_en_microservicio()

    if libros and Prestamo.objects.count() == 0:
        f = libros.get("9788420633997")
        if f:
            Prestamo.objects.create(lector=ana, libro_id=f["id"], estado="activo")
            try:
                servicios.editar_libro("python", f["id"], {"disponible": False})
            except servicios.MicroservicioNoDisponible:
                pass

        a = libros.get("9788420633988")
        if a:
            Prestamo.objects.create(
                lector=carlos, libro_id=a["id"], estado="devuelto", fecha_devolucion=date(2026, 9, 1)
            )

    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@mail.com", "admin123")

    docentes = [
        {
            "nombre": "Omar Andrés Bonilla Acosta",
            "cargo": "Docente Líder de Proyectos Integradores de Aula",
            "foto": "omar.png",
        },
        {
            "nombre": "Elfar Didier Morantes Sánchez",
            "cargo": "Docente de Django",
            "foto": "elfar.png",
        },
    ]
    for datos in docentes:
        docente, _ = Docente.objects.get_or_create(
            nombre=datos["nombre"], defaults={"cargo": datos["cargo"]}
        )
        ruta = os.path.join(
            os.path.dirname(__file__), "docentes", "img", datos["foto"]
        )
        if not docente.foto and os.path.exists(ruta):
            with open(ruta, "rb") as archivo:
                docente.foto.save(datos["foto"], File(archivo), save=True)

    print("¡Datos creados! Usuario admin -> usuario: admin, contraseña: admin123")


if __name__ == "__main__":
    crear_datos()