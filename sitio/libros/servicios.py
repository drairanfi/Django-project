"""Clientes HTTP del microservicio de reseñas y del asistente con IA.

Este módulo es el único lugar del proyecto que sabe que las reseñas y la IA
viven fuera de Django. Usa urllib de la biblioteca estándar: el proyecto sigue
sin dependencias externas.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings

from .models import Categoria, Libro
from prestamos.models import Lector, Prestamo


class MicroservicioNoDisponible(Exception):
    """El microservicio no respondió, tardó demasiado o devolvió algo inesperado."""


class IANoDisponible(Exception):
    """La API de IA no respondió, tardó demasiado o falta la clave en biblioteca/.env."""


def _pedir(url, datos=None, timeout=5, error_cls=MicroservicioNoDisponible):
    """Hace la petición HTTP y devuelve el JSON ya parseado."""
    cuerpo = None
    cabeceras = {"Accept": "application/json"}

    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"

    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras)

    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise error_cls(str(error)) from error


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


def armar_contexto_biblioteca():
    """Devuelve un texto con el funcionamiento de la app y los datos actuales para la IA."""
    lineas = []

    lineas.append("DESCRIPCION DE LA APP:")
    lineas.append(
        "La biblioteca comunitaria es un sistema web en Django. Un lector "
        "registrado se lleva un libro prestado: eso se llama un préstamo. "
        "Cada libro tiene un campo 'disponible': True significa que está en la "
        "biblioteca y se puede prestar; False significa que alguien ya lo tiene. "
        "Cuando un libro está prestado, no se puede prestar de nuevo hasta que "
        "se devuelva."
    )

    lineas.append("COMO FUNCIONA UN PRESTAMO:")
    lineas.append(
        "- Prestar: se elige un lector y un libro disponible, se crea el "
        "préstamo con estado 'activo' y el libro pasa a disponible=False. "
        "Si el libro ya no está disponible, no se puede prestar."
    )
    lineas.append(
        "- Devolver: el préstamo activo pasa a estado 'devuelto', se guarda la "
        "fecha de devolución y el libro vuelve a disponible=True."
    )
    lineas.append(
        "- Estados de un préstamo: 'activo' (el lector lo tiene), 'devuelto' "
        "(ya volvió), 'vencido' (no se devolvió a tiempo)."
    )

    lineas.append("QUE SE PUEDE HACER EN LA APP:")
    lineas.append(
        "- Ver el catálogo completo y si cada libro está disponible o prestado."
    )
    lineas.append("- Filtrar libros por categoría y por autor.")
    lineas.append("- Ver el detalle de cada libro, sus autores y sus reseñas.")
    lineas.append("- Registrar y devolver préstamos, y verlos por estado.")
    lineas.append("- Ver el historial de préstamos de cada lector.")

    lineas.append("DATOS ACTUALES DEL PROYECTO:")
    lineas.append("LIBROS:")
    for libro in Libro.objects.all():
        autores = ", ".join(str(autor) for autor in libro.autores.all())
        estado = "disponible" if libro.disponible else "prestado"
        lineas.append(
            f"- {libro.titulo} ({libro.anio_publicacion}), "
            f"categoria {libro.categoria.nombre}, autores: {autores}, {estado}"
        )

    lineas.append("CATEGORIAS:")
    for categoria in Categoria.objects.all():
        lineas.append(f"- {categoria.nombre}")

    lineas.append("LECTORES:")
    for lector in Lector.objects.all():
        lineas.append(f"- {lector.nombre} ({lector.email})")

    lineas.append("PRESTAMOS:")
    for prestamo in Prestamo.objects.all():
        lineas.append(
            f"- {prestamo.libro.titulo} -> {prestamo.lector.nombre} "
            f"({prestamo.estado}, desde {prestamo.fecha_prestamo})"
        )

    return "\n".join(lineas)


def preguntar_al_asistente(pregunta):
    """Envía la pregunta con el contexto del catálogo a la API de IA y devuelve la respuesta."""
    if not settings.IA_API_KEY:
        raise IANoDisponible("falta IA_API_KEY en biblioteca/.env")

    contexto = armar_contexto_biblioteca()
    mensaje_sistema = (
        "Sos el asistente de la Biblioteca Comunitaria, un sistema web de "
        "préstamo de libros. Respondé SOLO usando la información que te doy en "
        "el contexto (el funcionamiento de la app y sus datos actuales), nunca "
        "inventes datos ni funciones que no estén en el contexto. Podés "
        "responder preguntas sobre qué libros hay, quién los tiene prestados, "
        "cómo funciona un préstamo, cómo se presta o devuelve un libro, y qué "
        "se puede hacer en la app. Si la pregunta no tiene que ver con la "
        "biblioteca, decí que no podés responderla. Respondé en español, breve "
        "y en el mismo idioma que la pregunta."
    )

    # Gemini recibe la clave como parámetro de la URL y las instrucciones en
    # "contents", no en "messages" como OpenAI.
    url = f"{settings.IA_API_URL}/models/{settings.IA_MODEL}:generateContent?key={settings.IA_API_KEY}"
    datos = {
        "contents": [
            {
                "parts": [
                    {"text": mensaje_sistema},
                    {"text": f"CONTEXTO DEL PROYECTO:\n{contexto}\n\nPREGUNTA: {pregunta}"},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }

    respuesta = _pedir(url, datos, timeout=settings.IA_TIMEOUT, error_cls=IANoDisponible)
    return respuesta["candidates"][0]["content"]["parts"][0]["text"].strip()
