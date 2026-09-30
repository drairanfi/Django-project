from datetime import date

from django.shortcuts import get_object_or_404, render

from libros import servicios

from .models import Lector, Prestamo


def _titulo_de_libros():
    """Devuelve {id_libro: titulo} pidiendo los libros al microservicio.

    Si el microservicio no responde, devuelve un dict vacío y las vistas
    muestran un placeholder en vez de reventar.
    """
    try:
        datos, _, _ = servicios.obtener_libros()
        return {libro["id"]: libro.get("titulo", "?") for libro in datos.get("libros", [])}
    except servicios.MicroservicioNoDisponible:
        return {}


def _prestamos_con_titulo(prestamos):
    """Adjunta el título del libro a cada préstamo, pidiéndolos al microservicio."""
    titulos = _titulo_de_libros()
    for prestamo in prestamos:
        prestamo.titulo_libro = titulos.get(prestamo.libro_id, f"libro {prestamo.libro_id}")
    return prestamos


def lista_lectores(request):
    """Consulta todos los Lectores y los envía al template dentro del context."""
    lectores = Lector.objects.all()

    context = {
        "lectores": lectores,
    }
    return render(request, "prestamos/lectores.html", context)


def detalle_lector(request, lector_id):
    """Busca un Lector por id y trae sus Préstamos; los títulos de libros se piden al microservicio."""
    lector = get_object_or_404(Lector, pk=lector_id)
    prestamos = _prestamos_con_titulo(lector.prestamos.all())

    context = {
        "lector": lector,
        "prestamos": prestamos,
    }
    return render(request, "prestamos/detalle_lector.html", context)


def prestamos_por_estado(request, estado):
    """Filtra los Préstamos por estado; los títulos de libros se piden al microservicio."""
    estados_validos = [opcion[0] for opcion in Prestamo.ESTADO_CHOICES]
    if estado not in estados_validos:
        estado = "activo"

    prestamos = _prestamos_con_titulo(Prestamo.objects.filter(estado=estado))

    context = {
        "estado": estado,
        "prestamos": prestamos,
    }
    return render(request, "prestamos/prestamos.html", context)


def registrar_devolucion(request, prestamo_id):
    """Busca el Préstamo, actualiza el modelo y libera el libro en el microservicio."""
    prestamo = get_object_or_404(Prestamo, pk=prestamo_id)

    titulos = _titulo_de_libros()
    titulo_libro = titulos.get(prestamo.libro_id, f"libro {prestamo.libro_id}")

    if prestamo.estado == "activo":
        prestamo.estado = "devuelto"
        prestamo.fecha_devolucion = date.today()
        prestamo.save()

        # El libro vive en Supabase: hay que devolverlo ahí, no en SQLite.
        # Si el microservicio no responde, el préstamo igual se marca devuelto
        # y el libro quedará liberado en el próximo intento.
        try:
            datos, _ = servicios.obtener_libro(prestamo.libro_id)
            servicios.editar_libro(
                "python", prestamo.libro_id, {"disponible": True}
            )
            titulo_libro = datos.get("titulo", titulo_libro)
        except servicios.MicroservicioNoDisponible:
            pass

    context = {
        "prestamo": prestamo,
        "titulo_libro": titulo_libro,
    }
    return render(request, "prestamos/devolucion.html", context)


def crear_prestamo(request, libro_id):
    """Muestra el formulario (GET) y crea el Préstamo (POST) contra un libro del microservicio."""
    lectores = Lector.objects.all()
    mensaje = ""

    try:
        libro, _ = servicios.obtener_libro(libro_id)
        libro_existe = True
    except servicios.MicroservicioNoDisponible:
        libro = None
        libro_existe = False
        mensaje = "El microservicio de libros no está disponible"

    if request.method == "POST" and libro_existe:
        lector_id = request.POST.get("lector_id")
        lector = get_object_or_404(Lector, pk=lector_id)

        if libro.get("disponible"):
            Prestamo.objects.create(
                lector=lector,
                libro_id=libro_id,
                estado="activo",
            )
            # El libro vive en Supabase: se marca prestado ahí.
            try:
                servicios.editar_libro("python", libro_id, {"disponible": False})
                mensaje = f"Préstamo registrado para {lector.nombre}"
            except servicios.MicroservicioNoDisponible:
                mensaje = "Préstamo registrado, pero no se pudo avisar al microservicio"
        else:
            mensaje = "Ese libro ya no está disponible"

    context = {
        "libro": libro,
        "libro_existe": libro_existe,
        "lectores": lectores,
        "mensaje": mensaje,
    }
    return render(request, "prestamos/crear_prestamo.html", context)