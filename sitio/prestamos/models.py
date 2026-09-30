from django.db import models


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
    # Los libros ya no viven en SQLite: viven en Supabase, y los expone un
    # microservicio. Por eso acá se guarda solo el id y el título se pide por
    # HTTP cuando hace falta. Sin ForeignKey a Libro.
    libro_id = models.IntegerField()
    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="activo")

    def __str__(self):
        return f"libro {self.libro_id} -> {self.lector} ({self.estado})"