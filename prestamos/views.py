from datetime import date

from django.shortcuts import get_object_or_404, render

from libros.models import Libro

from .models import Lector, Prestamo


def lista_lectores(request):
    """Consulta todos los Lectores y los envía al template dentro del context."""
    lectores = Lector.objects.all()

    context = {
        "lectores": lectores,
    }
    return render(request, "prestamos/lectores.html", context)


def detalle_lector(request, lector_id):
    """Busca un Lector por id y trae sus Préstamos con el related_name del modelo."""
    lector = get_object_or_404(Lector, pk=lector_id)
    prestamos = lector.prestamos.all()

    context = {
        "lector": lector,
        "prestamos": prestamos,
    }
    return render(request, "prestamos/detalle_lector.html", context)


def prestamos_por_estado(request, estado):
    """Filtra los Préstamos por estado. El estado llega como parámetro de la URL."""
    estados_validos = [opcion[0] for opcion in Prestamo.ESTADO_CHOICES]
    if estado not in estados_validos:
        estado = "activo"

    prestamos = Prestamo.objects.filter(estado=estado)

    context = {
        "estado": estado,
        "prestamos": prestamos,
    }
    return render(request, "prestamos/prestamos.html", context)


def registrar_devolucion(request, prestamo_id):
    """Busca el Préstamo, actualiza el modelo y muestra el resultado en el template."""
    prestamo = get_object_or_404(Prestamo, pk=prestamo_id)

    if prestamo.estado == "activo":
        prestamo.estado = "devuelto"
        prestamo.fecha_devolucion = date.today()
        prestamo.save()

        prestamo.libro.disponible = True
        prestamo.libro.save()

    context = {
        "prestamo": prestamo,
    }
    return render(request, "prestamos/devolucion.html", context)


def crear_prestamo(request, libro_id):
    """Muestra el formulario (GET) y crea el Préstamo en el modelo (POST)."""
    libro = get_object_or_404(Libro, pk=libro_id)
    lectores = Lector.objects.all()
    mensaje = ""

    if request.method == "POST":
        lector_id = request.POST.get("lector_id")
        lector = get_object_or_404(Lector, pk=lector_id)

        if libro.disponible:
            Prestamo.objects.create(
                lector=lector,
                libro=libro,
                estado="activo",
            )
            libro.disponible = False
            libro.save()
            mensaje = f"Préstamo registrado para {lector.nombre}"
        else:
            mensaje = "Ese libro ya no está disponible"

    context = {
        "libro": libro,
        "lectores": lectores,
        "mensaje": mensaje,
    }
    return render(request, "prestamos/crear_prestamo.html", context)
