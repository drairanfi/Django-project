from django.contrib import admin

from .models import Autor, Categoria, Libro


@admin.register(Autor)
class AutorAdmin(admin.ModelAdmin):
    search_fields = ["nombre", "apellido"]


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ["nombre"]


@admin.register(Libro)
class LibroAdmin(admin.ModelAdmin):
    list_display = ["titulo", "isbn", "anio_publicacion", "categoria", "disponible"]
    list_filter = ["disponible", "categoria"]
    search_fields = ["titulo", "isbn"]