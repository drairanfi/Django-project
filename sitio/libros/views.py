from django.conf import settings
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from . import servicios
from .forms import LibroForm

# Lenguajes en los que está implementado el CRUD de libros. El usuario elige con
# cuál se ejecuta cada operación desde la interfaz; la vista solo lo traduce.
LENGUAJES_CRUD = ["python", "nodejs", "java", "php"]


def _servicio_elegido(request, contexto):
    """Devuelve el lenguaje elegido para la operación.

    El usuario lo elige con los botones del formulario; si no eligió ninguno,
    cae a python (el primario).
    """
    servicio = request.POST.get("servicio", "")
    if servicio not in settings.MICROSERVICIOS_LIBROS:
        servicio = "python"
    contexto["servicios_crud"] = LENGUAJES_CRUD
    contexto["servicio_elegido"] = servicio
    return servicio


def inicio(request):
    """Consulta los libros y las categorías al microservicio, arma el context y lo envía."""
    libros = []
    error = ""
    servicio = "python"
    caidos = []
    try:
        datos, servicio, caidos = servicios.obtener_libros()
        libros = datos.get("libros", [])
    except servicios.MicroservicioNoDisponible as fallo:
        error = f"El microservicio de libros no está disponible ({fallo})"

    disponibles = sum(1 for libro in libros if libro.get("disponible"))
    categorias = sorted({libro.get("categoria", "") for libro in libros if libro.get("categoria")})

    context = {
        "libros": libros,
        "disponibles": disponibles,
        "categorias": categorias,
        "servicio_origen": servicio,
        "servicios_caidos": caidos,
        "error": error,
    }
    return render(request, "libros/inicio.html", context)


def detalle_libro(request, libro_id):
    """Busca un Libro en el microservicio. Si no existe, la vista muestra un aviso."""
    try:
        libro, servicio = servicios.obtener_libro(libro_id)
    except servicios.LibroNoEncontrado:
        return render(request, "libros/no_encontrado.html", {"libro_id": libro_id})
    except servicios.MicroservicioNoDisponible as fallo:
        return render(request, "libros/no_encontrado.html", {
            "libro_id": libro_id,
            "error": f"El microservicio de libros no está disponible ({fallo})",
        })

    from prestamos.models import Prestamo

    prestamos_activos = Prestamo.objects.filter(libro_id=libro_id, estado="activo").count()

    autores = [a.strip() for a in libro.get("autores", "").split(",") if a.strip()]

    context = {
        "libro": libro,
        "autores": autores,
        "prestamos_activos": prestamos_activos,
        "servicio_origen": servicio,
    }
    return render(request, "libros/detalle_libro.html", context)


def libros_por_categoria(request, categoria):
    """Filtra los libros del microservicio por el nombre de su categoría."""
    libros = []
    error = ""
    servicio = "python"
    caidos = []
    try:
        datos, servicio, caidos = servicios.obtener_libros()
        libros = datos.get("libros", [])
    except servicios.MicroservicioNoDisponible as fallo:
        error = f"El microservicio de libros no está disponible ({fallo})"

    libros = [libro for libro in libros if libro.get("categoria", "") == categoria]

    context = {
        "categoria": categoria,
        "libros": libros,
        "servicio_origen": servicio,
        "servicios_caidos": caidos,
        "error": error,
    }
    return render(request, "libros/por_categoria.html", context)


def libros_por_autor(request, autor):
    """Filtra los libros del microservicio por el nombre del autor."""
    libros = []
    error = ""
    servicio = "python"
    caidos = []
    try:
        datos, servicio, caidos = servicios.obtener_libros()
        libros = datos.get("libros", [])
    except servicios.MicroservicioNoDisponible as fallo:
        error = f"El microservicio de libros no está disponible ({fallo})"

    libros = [libro for libro in libros if autor.lower() in libro.get("autores", "").lower()]

    context = {
        "autor": autor,
        "libros": libros,
        "servicio_origen": servicio,
        "servicios_caidos": caidos,
        "error": error,
    }
    return render(request, "libros/por_autor.html", context)


def resenas_libro(request, libro_id):
    """Combina un Libro del microservicio con sus reseñas traídas del microservicio de reseñas."""
    try:
        libro, _ = servicios.obtener_libro(libro_id)
    except (servicios.LibroNoEncontrado, servicios.MicroservicioNoDisponible):
        return render(request, "libros/no_encontrado.html", {"libro_id": libro_id})

    mensaje = ""

    if request.method == "POST":
        lector = request.POST.get("lector", "").strip()
        puntaje = request.POST.get("puntaje", "")

        if not lector or not puntaje.isdigit():
            mensaje = "Falta el nombre del lector o el puntaje"
        else:
            try:
                servicios.crear_resena(
                    libro_id=libro["id"],
                    lector=lector,
                    puntaje=int(puntaje),
                    comentario=request.POST.get("comentario", "").strip(),
                )
                mensaje = f"Reseña de {lector} guardada en el microservicio"
            except servicios.MicroservicioNoDisponible:
                mensaje = "No se pudo guardar: el microservicio no respondió"

    try:
        datos, url_origen = servicios.obtener_resenas_con_origen(libro["id"])
        error = ""
    except servicios.MicroservicioNoDisponible as fallo:
        datos = {}
        url_origen = settings.MICROSERVICIO_RESENAS_URL
        error = f"El microservicio de reseñas no está disponible ({fallo})"

    # 2. armar el context como variable con nombre
    context = {
        "libro": libro,
        "resenas": datos.get("resenas", []),
        "cantidad": datos.get("cantidad", 0),
        "promedio": datos.get("promedio"),
        "url_microservicio": url_origen,
        "url_respaldo": settings.MICROSERVICIO_RESENAS_FALLBACK_URL,
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


def _mensaje_respaldo(caidos, servicio_usado):
    """Arma el aviso cuando el servicio elegido estaba caído y se usó otro."""
    if not caidos:
        return ""
    elegido = caidos[0]
    return f"El microservicio {elegido} está caído, así que se usó {servicio_usado}"


def crear_libro(request):
    """Muestra el formulario (GET) y crea un libro en el microservicio elegido (POST)."""
    context = {}
    servicio = _servicio_elegido(request, context)

    if request.method == "POST":
        formulario = LibroForm(request.POST)
        if formulario.is_valid():
            try:
                libro, servicio_usado, caidos = servicios.ejecutar_crud_con_respaldo(
                    servicio, servicios.crear_libro, formulario.datos_para_el_servicio()
                )
                aviso = _mensaje_respaldo(caidos, servicio_usado)
                if aviso:
                    messages.warning(request, aviso)
                return HttpResponseRedirect(reverse("libros:detalle_libro", args=[libro["id"]]))
            except servicios.MicroservicioNoDisponible as fallo:
                formulario.add_error(None, f"El microservicio {servicio} no respondió ({fallo})")
    else:
        formulario = LibroForm()

    context["formulario"] = formulario
    return render(request, "libros/crear_libro.html", context)


def editar_libro(request, libro_id):
    """Muestra el formulario prellenado (GET) y actualiza el libro en el microservicio (POST)."""
    try:
        libro, _ = servicios.obtener_libro(libro_id)
    except (servicios.LibroNoEncontrado, servicios.MicroservicioNoDisponible):
        return render(request, "libros/no_encontrado.html", {"libro_id": libro_id})

    context = {"libro": libro}
    servicio = _servicio_elegido(request, context)

    if request.method == "POST":
        formulario = LibroForm(request.POST)
        if formulario.is_valid():
            try:
                libro_actualizado, servicio_usado, caidos = servicios.ejecutar_crud_con_respaldo(
                    servicio, servicios.editar_libro, libro_id,
                    formulario.datos_para_el_servicio(),
                )
                aviso = _mensaje_respaldo(caidos, servicio_usado)
                if aviso:
                    messages.warning(request, aviso)
                return HttpResponseRedirect(
                    reverse("libros:detalle_libro", args=[libro_actualizado["id"]])
                )
            except servicios.MicroservicioNoDisponible as fallo:
                formulario.add_error(None, f"El microservicio {servicio} no respondió ({fallo})")
    else:
        formulario = LibroForm(initial={
            "titulo": libro.get("titulo"),
            "isbn": libro.get("isbn"),
            "anio_publicacion": libro.get("anio_publicacion"),
            "paginas": libro.get("paginas"),
            "disponible": libro.get("disponible"),
            "categoria": libro.get("categoria", ""),
            "autores": libro.get("autores", ""),
        })

    context["formulario"] = formulario
    return render(request, "libros/editar_libro.html", context)


def eliminar_libro(request, libro_id):
    """Muestra la confirmación (GET) y borra el libro en el microservicio elegido (POST)."""
    try:
        libro, _ = servicios.obtener_libro(libro_id)
    except (servicios.LibroNoEncontrado, servicios.MicroservicioNoDisponible):
        return render(request, "libros/no_encontrado.html", {"libro_id": libro_id})

    context = {"libro": libro}
    servicio = _servicio_elegido(request, context)

    if request.method == "POST":
        try:
            _, servicio_usado, caidos = servicios.ejecutar_crud_con_respaldo(
                servicio, servicios.eliminar_libro, libro_id
            )
            aviso = _mensaje_respaldo(caidos, servicio_usado)
            if aviso:
                messages.warning(request, aviso)
            return HttpResponseRedirect(reverse("libros:inicio"))
        except servicios.MicroservicioNoDisponible as fallo:
            context["error"] = f"El microservicio {servicio} no respondió ({fallo})"

    from prestamos.models import Prestamo

    prestamos_activos = Prestamo.objects.filter(libro_id=libro_id, estado="activo").count()
    context["prestamos_activos"] = prestamos_activos

    return render(request, "libros/eliminar_libro.html", context)