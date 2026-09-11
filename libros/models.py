from django.db import models


class Autor(models.Model):
    nombre = models.CharField(max_length=100)
    apellido = models.CharField(max_length=100)
    nacionalidad = models.CharField(max_length=100, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.nombre} {self.apellido}"


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Libro(models.Model):
    titulo = models.CharField(max_length=200)
    isbn = models.CharField(max_length=20, unique=True)
    anio_publicacion = models.IntegerField()
    paginas = models.IntegerField(default=0)
    disponible = models.BooleanField(default=True)
    autores = models.ManyToManyField(Autor, related_name="libros")
    categoria = models.ForeignKey(
        Categoria, on_delete=models.CASCADE, related_name="libros"
    )

    def __str__(self):
        return self.titulo