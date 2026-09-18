from django.db import models

from libros.models import Libro


class Lector(models.Model):
    nombre = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    fecha_registro = models.DateField(auto_now_add=True)

    def __str__(self):
        return self.nombre


class Prestamo(models.Model):
    ESTADO_CHOICES = [
        ("activo", "Activo"),
        ("devuelto", "Devuelto"),
        ("vencido", "Vencido"),
    ]

    lector = models.ForeignKey(Lector, on_delete=models.CASCADE, related_name="prestamos")
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, related_name="prestamos")
    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="activo")

    def __str__(self):
        return f"{self.libro} -> {self.lector} ({self.estado})"