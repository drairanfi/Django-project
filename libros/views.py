from django.shortcuts import get_object_or_404, render

from .models import Autor, Categoria, Libro


def inicio(request):
    """Consulta el modelo Libro y Categoría, arma el context y lo envía al template."""
    libros = Libro.objects.all()
    disponibles = Libro.objects.filter(disponible=True).count()
    categorias = Categoria.objects.all()

    context = {
        "libros": libros,
        "disponibles": disponibles,
        "categorias": categorias,
    }
    return render(request, "libros/inicio.html", context)


def detalle_libro(request, libro_id):
    """Busca un Libro por su id. Si no existe, get_object_or_404 devuelve un 404."""
    libro = get_object_or_404(Libro, pk=libro_id)
    prestamos_activos = libro.prestamos.filter(estado="activo").count()

    context = {
        "libro": libro,
        "prestamos_activos": prestamos_activos,
    }
    return render(request, "libros/detalle_libro.html", context)


def libros_por_categoria(request, categoria_id):
    """Busca la Categoría y filtra los Libros que le pertenecen."""
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    libros = Libro.objects.filter(categoria=categoria)

    context = {
        "categoria": categoria,
        "libros": libros,
    }
    return render(request, "libros/por_categoria.html", context)


def libros_por_autor(request, autor_id):
    """Busca el Autor y recorre sus Libros usando el related_name del modelo."""
    autor = get_object_or_404(Autor, pk=autor_id)
    libros = autor.libros.all()

    context = {
        "autor": autor,
        "libros": libros,
    }
    return render(request, "libros/por_autor.html", context)
