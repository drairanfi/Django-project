import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "biblioteca.settings")

import django

django.setup()

from datetime import date

from django.contrib.auth.models import User

from libros.models import Autor, Categoria, Libro
from prestamos.models import Lector, Prestamo


def crear_datos():
    print("Creando datos de ejemplo...")

    ficcion = Categoria.objects.get_or_create(nombre="Ficción")[0]
    ciencia = Categoria.objects.get_or_create(nombre="Ciencia")[0]
    historia = Categoria.objects.get_or_create(nombre="Historia")[0]

    borges = Autor.objects.get_or_create(
        nombre="Jorge Luis", apellido="Borges", nacionalidad="Argentina"
    )[0]
    verne = Autor.objects.get_or_create(
        nombre="Julio", apellido="Verne", nacionalidad="Francia"
    )[0]
    hawking = Autor.objects.get_or_create(
        nombre="Stephen", apellido="Hawking", nacionalidad="Inglaterra"
    )[0]

    libros = [
        ("Ficciones", "9788420633997", 1944, 176, ficcion, [borges]),
        ("El Aleph", "9788420633988", 1949, 194, ficcion, [borges]),
        ("Veinte mil leguas de viaje submarino", "9788420680554", 1870, 418, ficcion, [verne]),
        ("La vuelta al mundo en 80 días", "9788420600989", 1872, 290, ficcion, [verne]),
        ("Breve historia del tiempo", "9788474238745", 1988, 256, ciencia, [hawking]),
        ("El universo en una cáscara de nuez", "9788466625973", 2001, 224, ciencia, [hawking]),
    ]

    for titulo, isbn, anio, paginas, categoria, autores in libros:
        libro = Libro.objects.get_or_create(
            titulo=titulo,
            defaults={
                "isbn": isbn,
                "anio_publicacion": anio,
                "paginas": paginas,
                "categoria": categoria,
                "disponible": True,
            },
        )[0]
        libro.autores.set(autores)

    ana = Lector.objects.get_or_create(
        nombre="Ana García", email="ana@mail.com", telefono="11-2222-3333"
    )[0]
    carlos = Lector.objects.get_or_create(
        nombre="Carlos Pérez", email="carlos@mail.com", telefono="11-4444-5555"
    )[0]

    if Prestamo.objects.count() == 0:
        f = Libro.objects.get(titulo="Ficciones")
        Prestamo.objects.create(lector=ana, libro=f, estado="activo")
        f.disponible = False
        f.save()

        a = Libro.objects.get(titulo="El Aleph")
        Prestamo.objects.create(
            lector=carlos, libro=a, estado="devuelto", fecha_devolucion=date(2026, 9, 1)
        )

    if not User.objects.filter(username="admin").exists():
        User.objects.create_superuser("admin", "admin@mail.com", "admin123")

    print("¡Datos creados! Usuario admin -> usuario: admin, contraseña: admin123")


if __name__ == "__main__":
    crear_datos()