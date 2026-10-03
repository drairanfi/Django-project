from django.db import models


class Docente(models.Model):
    """Un docente involucrado en el proyecto.

    A diferencia de los libros, los docentes sí viven en SQLite y se consultan
    con el ORM, igual que Lector y Prestamo.
    """

    nombre = models.CharField(max_length=150)
    cargo = models.CharField(max_length=200)
    foto = models.ImageField(upload_to="docentes/", blank=True)

    def __str__(self):
        return self.nombre
