from django.shortcuts import get_object_or_404, render

from .models import Autor, Categoria, Libro


def inicio(request):
    libros = Libro.objects.all()
    disponibles = Libro.objects.filter(disponible=True).count()
    categorias = Categoria.objects.all()
    return render(request, "libros/inicio.html", {
        "libros": libros,
        "disponibles": disponibles,
        "categorias": categorias,
    })


def detalle_libro(request, libro_id):
    libro = get_object_or_404(Libro, pk=libro_id)
    prestamos_activos = libro.prestamos.filter(estado="activo").count()
    return render(request, "libros/detalle_libro.html", {
        "libro": libro,
        "prestamos_activos": prestamos_activos,
    })


def libros_por_categoria(request, categoria_id):
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    libros = Libro.objects.filter(categoria=categoria)
    return render(request, "libros/por_categoria.html", {
        "categoria": categoria,
        "libros": libros,
    })


def libros_por_autor(request, autor_id):
    autor = get_object_or_404(Autor, pk=autor_id)
    libros = autor.libros.all()
    return render(request, "libros/por_autor.html", {
        "autor": autor,
        "libros": libros,
    })