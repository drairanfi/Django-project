from datetime import date

from django.shortcuts import get_object_or_404, render

from libros.models import Libro

from .models import Lector, Prestamo


def lista_lectores(request):
    lectores = Lector.objects.all()
    return render(request, "prestamos/lectores.html", {
        "lectores": lectores,
    })


def detalle_lector(request, lector_id):
    lector = get_object_or_404(Lector, pk=lector_id)
    prestamos = lector.prestamos.all()
    return render(request, "prestamos/detalle_lector.html", {
        "lector": lector,
        "prestamos": prestamos,
    })


def prestamos_por_estado(request, estado):
    validos = [e[0] for e in Prestamo.ESTADO_CHOICES]
    if estado not in validos:
        estado = "activo"
    prestamos = Prestamo.objects.filter(estado=estado)
    return render(request, "prestamos/prestamos.html", {
        "estado": estado,
        "prestamos": prestamos,
    })


def registrar_devolucion(request, prestamo_id):
    prestamo = get_object_or_404(Prestamo, pk=prestamo_id)
    if prestamo.estado == "activo":
        prestamo.estado = "devuelto"
        prestamo.fecha_devolucion = date.today()
        prestamo.libro.disponible = True
        prestamo.libro.save()
        prestamo.save()
    return render(request, "prestamos/devolucion.html", {
        "prestamo": prestamo,
    })


def crear_prestamo(request, libro_id):
    libro = get_object_or_404(Libro, pk=libro_id)
    lectores = Lector.objects.all()
    mensaje = ""

    if request.method == "POST":
        lector_id = request.POST.get("lector_id")
        lector = get_object_or_404(Lector, pk=lector_id)
        if libro.disponible:
            prestamo = Prestamo.objects.create(
                lector=lector,
                libro=libro,
                estado="activo",
            )
            libro.disponible = False
            libro.save()
            mensaje = f"Préstamo registrado para {lector.nombre}"
        else:
            mensaje = "Ese libro ya no está disponible"

    return render(request, "prestamos/crear_prestamo.html", {
        "libro": libro,
        "lectores": lectores,
        "mensaje": mensaje,
    })