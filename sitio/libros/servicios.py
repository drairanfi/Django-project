"""Clientes HTTP del microservicio de reseñas y del asistente con IA.

Este módulo es el único lugar del proyecto que sabe que las reseñas y la IA
viven fuera de Django. Usa urllib de la biblioteca estándar: el proyecto sigue
sin dependencias externas.
"""
import json
import urllib.error
import urllib.request

from django.conf import settings

from prestamos.models import Lector, Prestamo


class MicroservicioNoDisponible(Exception):
    """El microservicio no respondió, tardó demasiado o devolvió algo inesperado."""


class IANoDisponible(Exception):
    """La API de IA no respondió, tardó demasiado o falta la clave en biblioteca/.env."""


class LibroNoEncontrado(Exception):
    """El microservicio respondió 404: el libro no existe."""


def _pedir(url, datos=None, timeout=5, error_cls=MicroservicioNoDisponible, cabeceras_extra=None, metodo="GET"):
    """Hace la petición HTTP y devuelve el JSON ya parseado."""
    cuerpo = None
    cabeceras = {
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    }

    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"
        if metodo == "GET":
            metodo = "POST"

    if cabeceras_extra:
        cabeceras.update(cabeceras_extra)

    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras, method=metodo)

    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        if error.code == 404:
            raise LibroNoEncontrado("el libro no existe")
        raise error_cls(f"HTTP {error.code}") from error
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise error_cls(str(error)) from error


def _pedir_con_respaldo(ruta, datos=None):
    """Pide al microservicio primario y, si falla, al de respaldo.

    Devuelve (json, url_que_respondio). Si los dos fallan, levanta
    MicroservicioNoDisponible. El respaldo existe para que la lectura de
    reseñas no dependa de un solo servicio: si el primario (Python) se cae,
    el sitio sigue mostrando datos desde otro servicio escrito en otro
    lenguaje (NodeJS).
    """
    urls = [
        settings.MICROSERVICIO_RESENAS_URL,
        settings.MICROSERVICIO_RESENAS_FALLBACK_URL,
    ]
    ultimo_error = None

    for url in urls:
        try:
            datos_json = _pedir(f"{url}{ruta}", datos)
            return datos_json, url
        except MicroservicioNoDisponible as error:
            ultimo_error = error

    raise MicroservicioNoDisponible(str(ultimo_error))


def obtener_resenas(libro_id):
    """Trae las reseñas de un libro: {libro_id, cantidad, promedio, resenas}.

    Con resiliencia: intenta el microservicio primario y, si no responde, el de
    respaldo.
    """
    datos, _ = _pedir_con_respaldo(f"/libros/{libro_id}/resenas")
    return datos


def obtener_resenas_con_origen(libro_id):
    """Igual que obtener_resenas pero además devuelve qué URL respondió.

    La vista lo usa para mostrarle al usuario de dónde salieron los datos.
    """
    return _pedir_con_respaldo(f"/libros/{libro_id}/resenas")


def obtener_todas_resenas():
    """Trae todas las reseñas: {cantidad, resenas}.

    Con resiliencia: intenta el microservicio primario y, si no responde, el de
    respaldo.
    """
    datos, _ = _pedir_con_respaldo("/resenas")
    return datos


def _pedir_a_servicio_libros(servicio, ruta, datos=None, metodo="GET"):
    """Pide a un microservicio de libros concreto, por su nombre de lenguaje."""
    url = settings.MICROSERVICIOS_LIBROS[servicio] + ruta
    return _pedir(url, datos=datos, metodo=metodo)


def obtener_libros():
    """Trae todos los libros: {cantidad, libros}.

    Resiliencia: recorre MICROSERVICIOS_LIBROS_ORDEN_LECTURA y devuelve el
    primer servicio que responda. Devuelve (datos, servicio_que_respondio,
    servicios_caidos): los caídos son los que no respondieron antes de dar con
    el que sí lo hizo, para que la vista pueda avisar al usuario.
    """
    caidos = []
    ultimo_error = None
    for servicio in settings.MICROSERVICIOS_LIBROS_ORDEN_LECTURA:
        try:
            datos = _pedir_a_servicio_libros(servicio, "/libros")
            return datos, servicio, caidos
        except MicroservicioNoDisponible as error:
            caidos.append(servicio)
            ultimo_error = error
    raise MicroservicioNoDisponible(str(ultimo_error))


def obtener_libro(libro_id):
    """Trae un libro por id con resiliencia: recorre los servicios hasta que uno responda."""
    ultimo_error = None
    for servicio in settings.MICROSERVICIOS_LIBROS_ORDEN_LECTURA:
        try:
            datos = _pedir_a_servicio_libros(servicio, f"/libros/{libro_id}")
            return datos, servicio
        except LibroNoEncontrado as error:
            # El servicio respondió pero el libro no existe ahí. Se sigue
            # probando el siguiente por si acaso hay datos desincronizados.
            ultimo_error = error
        except MicroservicioNoDisponible as error:
            ultimo_error = error
    if isinstance(ultimo_error, LibroNoEncontrado):
        raise LibroNoEncontrado(str(ultimo_error))
    raise MicroservicioNoDisponible(str(ultimo_error))


def crear_libro(servicio, datos):
    """Crea un libro en el microservicio elegido y devuelve el libro guardado."""
    return _pedir_a_servicio_libros(servicio, "/libros", datos=datos, metodo="POST")


def ejecutar_crud_con_respaldo(servicio_elegido, operacion, *args):
    """Ejecuta una operación de CRUD con resiliencia.

    Intenta primero el microservicio que eligió el usuario con los botones; si
    no responde, cae a los demás en orden de lectura. Devuelve
    (resultado, servicio_usado, servicios_caidos).
    """
    servicios_a_probar = [servicio_elegido] + [
        s for s in settings.MICROSERVICIOS_LIBROS_ORDEN_LECTURA if s != servicio_elegido
    ]
    caidos = []
    ultimo_error = None

    for servicio in servicios_a_probar:
        try:
            resultado = operacion(servicio, *args)
            return resultado, servicio, caidos
        except MicroservicioNoDisponible as error:
            caidos.append(servicio)
            ultimo_error = error

    raise MicroservicioNoDisponible(str(ultimo_error))


def editar_libro(servicio, libro_id, datos):
    """Actualiza un libro en el microservicio elegido y devuelve el libro guardado."""
    return _pedir_a_servicio_libros(servicio, f"/libros/{libro_id}", datos=datos, metodo="PUT")


def eliminar_libro(servicio, libro_id):
    """Borra un libro en el microservicio elegido y devuelve la fila eliminada."""
    return _pedir_a_servicio_libros(servicio, f"/libros/{libro_id}", metodo="DELETE")


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

    lineas.append("COMO AGREGAR UN LIBRO:")
    lineas.append(
        "Desde el enlace 'Agregar libro' del catálogo se abre un formulario "
        "con los campos del libro: título, ISBN, año de publicación, páginas, "
        "disponible, categoría y autores. Se puede elegir una categoría "
        "existente o escribir una nueva en el campo 'Categoría nueva'. Lo mismo "
        "con los autores: se marcan los existentes o se escriben nuevos "
        "separados por coma en el campo 'Autores nuevos'. Al guardar, el libro "
        "se crea con su categoría y autores (los que no existían se crean solos) "
        "y se redirige al detalle del libro nuevo. El ISBN no se puede repetir: "
        "si ya existe otro libro con el mismo ISBN, el formulario muestra un error."
    )

    lineas.append("COMO EDITAR UN LIBRO:")
    lineas.append(
        "Desde el detalle de un libro, el enlace 'Editar' abre el mismo "
        "formulario pero prellenado con los datos actuales del libro. Se pueden "
        "cambiar cualquiera de los campos: título, ISBN, año, páginas, estado "
        "de disponibilidad, categoría, autores, y agregar categoría o autores "
        "nuevos igual que en el alta. Al guardar, los cambios se aplican y se "
        "vuelve al detalle del libro con los datos actualizados. El ISBN "
        "tampoco puede repetirse acá: si se intenta poner el ISBN de otro "
        "libro existente, el formulario muestra un error."
    )

    lineas.append("COMO ELIMINAR UN LIBRO:")
    lineas.append(
        "Desde el detalle de un libro, el enlace 'Eliminar' abre una página de "
        "confirmación que muestra los datos del libro. Si el libro tiene "
        "préstamos activos, avisa que al eliminarlo se borran también todos sus "
        "préstamos. El libro solo se borra cuando se confirma el formulario de "
        "la página de confirmación; después se vuelve al catálogo. Un libro "
        "eliminado desaparece del catálogo y ya no se puede ver ni prestar."
    )

    lineas.append("DATOS ACTUALES DEL PROYECTO:")
    lineas.append("LIBROS:")
    try:
        libros, _, _ = obtener_libros()
        libros = libros.get("libros", [])
    except MicroservicioNoDisponible:
        libros = []
    for libro in libros:
        autores = libro.get("autores", "")
        estado = "disponible" if libro.get("disponible") else "prestado"
        lineas.append(
            f"- {libro['titulo']} ({libro.get('anio_publicacion')}), "
            f"categoria {libro.get('categoria', '')}, autores: {autores}, {estado}"
        )

    lineas.append("CATEGORIAS:")
    for categoria in {libro.get("categoria", "") for libro in libros if libro.get("categoria")}:
        lineas.append(f"- {categoria}")

    lineas.append("LECTORES:")
    for lector in Lector.objects.all():
        lineas.append(f"- {lector.nombre} ({lector.email})")

    titulos = {libro["id"]: libro.get("titulo", "?") for libro in libros}
    lineas.append("PRESTAMOS:")
    for prestamo in Prestamo.objects.all():
        lineas.append(
            f"- {titulos.get(prestamo.libro_id, 'libro ' + str(prestamo.libro_id))} -> {prestamo.lector.nombre} "
            f"({prestamo.estado}, desde {prestamo.fecha_prestamo})"
        )

    lineas.append("MICROSERVICIO DE RESEÑAS:")
    lineas.append(
        "Las reseñas de los libros NO viven en la base de datos del sitio: "
        "viven en un microservicio externo (FastAPI) que usa su propia base "
        "de datos, PostgreSQL administrada en Supabase. El sitio Django no se "
        "conecta a esa base directamente: solo conoce la URL pública del "
        "microservicio y le pide las reseñas por HTTP. Ese endpoint público "
        "es GET /api/resenas (todas las reseñas) y GET "
        "/api/libros/{libro_id}/resenas (las de un libro con su promedio). "
        "Django consume esas reseñas a través del módulo servicios.py."
    )

    lineas.append("RESENAS:")
    try:
        resenas = obtener_todas_resenas().get("resenas", [])
    except MicroservicioNoDisponible:
        resenas = []
    if not resenas:
        lineas.append("- No hay reseñas cargadas en el microservicio.")
    else:
        for resena in resenas:
            lineas.append(
                f"- Libro {resena['libro_id']}: {resena['lector']} le puso "
                f"{resena['puntaje']} ({resena['comentario'] or 'sin comentario'})"
            )

    lineas.append("JSON DEL ENDPOINT PUBLICO DE RESEÑAS:")
    lineas.append(
        "Cuando te pregunten por consultas a la base de datos o por el JSON que "
        "devuelve el microservicio, mostrá el contenido de este endpoint público: "
        f"{settings.MICROSERVICIO_RESENAS_URL}/libros/1/resenas"
    )
    try:
        json_resenas = obtener_resenas(1)
        lineas.append(json.dumps(json_resenas, ensure_ascii=False, indent=2))
    except MicroservicioNoDisponible:
        lineas.append("(el microservicio no está disponible para mostrar el JSON)")

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
        "cómo funciona un préstamo, cómo se presta o devuelve un libro, cómo "
        "agregar, editar o eliminar un libro, las reseñas del microservicio "
        "externo y su base de datos en Supabase, y qué se puede hacer en la app. "
        "Si te preguntan por una consulta a la base de datos o por el JSON que "
        "devuelve el microservicio, reproducí el contenido del bloque "
        "JSON DEL ENDPOINT PUBLICO DE RESEÑAS del contexto, tal cual está. Si la pregunta no tiene que ver con la "
        "biblioteca, decí que no podés responderla. Respondé en español, breve "
        "y en el mismo idioma que la pregunta."
    )

    # Gemini recibe la clave como parámetro de la URL y las instrucciones en
    # "contents", no en "messages" como OpenAI. El gateway de opencode-go usa
    # el formato OpenAI (chat/completions, Authorization, x-opencode-session).
    es_gemini = "generativelanguage.googleapis.com" in settings.IA_API_URL

    if es_gemini:
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

    url = f"{settings.IA_API_URL}/chat/completions"
    cabeceras = {"Authorization": f"Bearer {settings.IA_API_KEY}"}
    if settings.IA_API_SESION:
        cabeceras["x-opencode-session"] = settings.IA_API_SESION
    datos = {
        "model": settings.IA_MODEL,
        "messages": [
            {"role": "system", "content": mensaje_sistema},
            {"role": "user", "content": f"CONTEXTO DEL PROYECTO:\n{contexto}\n\nPREGUNTA: {pregunta}"},
        ],
        "temperature": 0.2,
    }
    respuesta = _pedir(
        url, datos, timeout=settings.IA_TIMEOUT, error_cls=IANoDisponible,
        cabeceras_extra=cabeceras,
    )
    return respuesta["choices"][0]["message"]["content"].strip()
