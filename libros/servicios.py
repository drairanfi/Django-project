"""Cliente HTTP del microservicio de reseñas.

Este módulo es el único lugar del proyecto que sabe que las reseñas viven fuera
de Django. Usa urllib de la biblioteca estándar: el proyecto sigue sin
dependencias externas.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

from django.conf import settings


class MicroservicioNoDisponible(Exception):
    """El microservicio no respondió, tardó demasiado o devolvió algo inesperado."""


def _pedir(url, datos=None):
    """Hace la petición HTTP y devuelve el JSON ya parseado."""
    cuerpo = None
    cabeceras = {"Accept": "application/json"}

    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"

    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras)

    try:
        with urllib.request.urlopen(
            peticion, timeout=settings.MICROSERVICIO_RESENAS_TIMEOUT
        ) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise MicroservicioNoDisponible(str(error)) from error


def obtener_resenas(libro_id):
    """Trae las reseñas de un libro: {libro_id, cantidad, promedio, resenas}."""
    url = f"{settings.MICROSERVICIO_RESENAS_URL}/libros/{libro_id}/resenas"
    return _pedir(url)


def crear_resena(libro_id, lector, puntaje, comentario):
    """Envía una reseña nueva al microservicio y devuelve la reseña guardada."""
    url = f"{settings.MICROSERVICIO_RESENAS_URL}/resenas"
    datos = {
        "libro_id": libro_id,
        "lector": lector,
        "puntaje": puntaje,
        "comentario": comentario,
    }
    return _pedir(url, datos)
