from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse

from . import servicios
from .forms import LibroForm
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


def resenas_libro(request, libro_id):
    """Combina un Libro del ORM con sus reseñas traídas del microservicio externo."""
    # 1. consumir el modelo y, por HTTP, el microservicio
    libro = get_object_or_404(Libro, pk=libro_id)
    mensaje = ""

    if request.method == "POST":
        lector = request.POST.get("lector", "").strip()
        puntaje = request.POST.get("puntaje", "")

        if not lector or not puntaje.isdigit():
            mensaje = "Falta el nombre del lector o el puntaje"
        else:
            try:
                servicios.crear_resena(
                    libro_id=libro.id,
                    lector=lector,
                    puntaje=int(puntaje),
                    comentario=request.POST.get("comentario", "").strip(),
                )
                mensaje = f"Reseña de {lector} guardada en el microservicio"
            except servicios.MicroservicioNoDisponible:
                mensaje = "No se pudo guardar: el microservicio no respondió"

    try:
        datos = servicios.obtener_resenas(libro.id)
        error = ""
    except servicios.MicroservicioNoDisponible as fallo:
        datos = {}
        error = f"El microservicio de reseñas no está disponible ({fallo})"

    # 2. armar el context como variable con nombre
    context = {
        "libro": libro,
        "resenas": datos.get("resenas", []),
        "cantidad": datos.get("cantidad", 0),
        "promedio": datos.get("promedio"),
        "url_microservicio": settings.MICROSERVICIO_RESENAS_URL,
        "mensaje": mensaje,
        "error": error,
    }

    # 3. enviarlo al template
    return render(request, "libros/resenas.html", context)


def asistente(request):
    """Muestra el formulario (GET) y consulta la IA con el contexto del proyecto (POST)."""
    respuesta = ""
    error = ""

    if request.method == "POST":
        pregunta = request.POST.get("pregunta", "").strip()
        if not pregunta:
            error = "Escribí una pregunta primero"
        else:
            try:
                respuesta = servicios.preguntar_al_asistente(pregunta)
            except servicios.IANoDisponible as fallo:
                error = f"No se pudo consultar a la IA ({fallo})"

    context = {
        "respuesta": respuesta,
        "error": error,
    }
    return render(request, "libros/asistente.html", context)


def _crear_categoria_o_autor_que_faltan(formulario, libro):
    """Crea la categoría y los autores nuevos que vienen del formulario y los asocia al libro."""
    categoria_nueva = formulario.cleaned_data.get("categoria_nueva")
    if categoria_nueva:
        categoria, _ = Categoria.objects.get_or_create(nombre=categoria_nueva.strip())
        libro.categoria = categoria
        libro.save()

    autores_nuevos = formulario.cleaned_data.get("autores_nuevos")
    if autores_nuevos:
        for nombre_completo in autores_nuevos.split(","):
            partes = nombre_completo.strip().split(" ")
            nombre = partes[0]
            apellido = " ".join(partes[1:]) if len(partes) > 1 else ""
            autor, _ = Autor.objects.get_or_create(nombre=nombre, apellido=apellido)
            libro.autores.add(autor)


def crear_libro(request):
    """Muestra el formulario (GET) y crea un Libro nuevo (POST), con categoría y autores."""
    if request.method == "POST":
        formulario = LibroForm(request.POST)
        if formulario.is_valid():
            libro = formulario.save()
            _crear_categoria_o_autor_que_faltan(formulario, libro)
            return HttpResponseRedirect(reverse("libros:detalle_libro", args=[libro.id]))
    else:
        formulario = LibroForm()

    context = {
        "formulario": formulario,
    }
    return render(request, "libros/crear_libro.html", context)


def editar_libro(request, libro_id):
    """Muestra el formulario prellenado (GET) y actualiza el Libro (POST)."""
    libro = get_object_or_404(Libro, pk=libro_id)

    if request.method == "POST":
        formulario = LibroForm(request.POST, instance=libro)
        if formulario.is_valid():
            formulario.save()
            _crear_categoria_o_autor_que_faltan(formulario, libro)
            return HttpResponseRedirect(reverse("libros:detalle_libro", args=[libro.id]))
    else:
        formulario = LibroForm(instance=libro)

    context = {
        "formulario": formulario,
        "libro": libro,
    }
    return render(request, "libros/editar_libro.html", context)


def eliminar_libro(request, libro_id):
    """Muestra la confirmación (GET) y borra el Libro con sus préstamos en cascada (POST)."""
    libro = get_object_or_404(Libro, pk=libro_id)

    if request.method == "POST":
        libro.delete()
        return HttpResponseRedirect(reverse("libros:inicio"))

    prestamos_activos = libro.prestamos.filter(estado="activo").count()

    context = {
        "libro": libro,
        "prestamos_activos": prestamos_activos,
    }
    return render(request, "libros/eliminar_libro.html", context)
