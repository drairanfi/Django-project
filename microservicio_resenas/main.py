"""Microservicio de reseñas.

Expone una API HTTP sobre una tabla de Supabase (PostgreSQL en la nube).
Django NO habla con esta base de datos: habla con esta API por HTTP.
"""
import os

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from supabase import Client, create_client

TABLA = "resenas"
TABLA_LIBROS = "libros"

def variable_obligatoria(nombre):
    """Lee una variable de entorno obligatoria y falla con un mensaje legible si falta."""
    valor = os.environ.get(nombre)
    if not valor:
        raise RuntimeError(
            f"Falta la variable de entorno {nombre}. "
            "Cargala en el panel de la plataforma de despliegue, "
            "o en el archivo .env si estás corriendo local."
        )
    return valor


# Las credenciales llegan por variables de entorno. Nunca se escriben en el código.
# Si falta alguna, el servicio no arranca: es preferible fallar al inicio y no
# en medio de un request.
SUPABASE_URL = variable_obligatoria("SUPABASE_URL")
SUPABASE_SERVICE_KEY = variable_obligatoria("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# La documentación interactiva (swagger) también vive bajo /api, igual que las
# rutas: el sitio ocupa / y este servicio /api, así que /docs en la raíz no le
# llegaría nunca en el despliegue compartido.
app = FastAPI(
    title="Microservicio de Reseñas",
    description="API de reseñas de libros almacenadas en Supabase.",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Todas las rutas cuelgan de /api porque el servicio comparte dominio con el
# sitio Django: el sitio vive en / y la API en /api. Vercel enruta por prefijo y
# le entrega al servicio la ruta completa, con /api incluido, asi que el prefijo
# tiene que estar declarado aca tambien.
api = APIRouter(prefix="/api")


class ResenaNueva(BaseModel):
    """Datos que el cliente envía para crear una reseña."""

    libro_id: int = Field(..., ge=1)
    lector: str = Field(..., min_length=1, max_length=100)
    puntaje: int = Field(..., ge=1, le=5)
    comentario: str = Field("", max_length=1000)


class LibroDatos(BaseModel):
    """Datos de un libro para crear (POST) o actualizar (PUT)."""

    titulo: str = Field(..., min_length=1, max_length=200)
    isbn: str = Field(..., min_length=1, max_length=20)
    anio_publicacion: int | None = None
    paginas: int | None = None
    disponible: bool = True
    categoria: str = Field("", max_length=100)
    autores: str = Field("", max_length=500)


class LibroParcial(BaseModel):
    """Campos opcionales para actualizar un libro (PUT)."""

    titulo: str | None = Field(None, min_length=1, max_length=200)
    isbn: str | None = Field(None, min_length=1, max_length=20)
    anio_publicacion: int | None = None
    paginas: int | None = None
    disponible: bool | None = None
    categoria: str | None = Field(None, max_length=100)
    autores: str | None = Field(None, max_length=500)


@api.get("/")
def raiz():
    """Describe el servicio para quien entra a la URL base."""
    return {
        "servicio": "microservicio-resenas",
        "version": "1.0.0",
        "base_de_datos": "Supabase (PostgreSQL)",
        "endpoints": [
            "GET /api/salud",
            "GET /api/resenas",
            "GET /api/libros/{libro_id}/resenas",
            "POST /api/resenas",
            "GET /api/libros",
            "POST /api/libros",
            "PUT /api/libros/{libro_id}",
            "DELETE /api/libros/{libro_id}",
            "GET /api/docs (swagger)",
        ],
    }


@api.get("/salud")
def salud():
    """Health check: la plataforma lo usa para saber si el servicio está vivo."""
    return {"estado": "ok"}


@api.get("/resenas")
def listar_resenas():
    """Devuelve todas las reseñas ordenadas de la más nueva a la más vieja."""
    try:
        respuesta = (
            supabase.table(TABLA)
            .select("*")
            .order("creada_en", desc=True)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    return {"cantidad": len(respuesta.data), "resenas": respuesta.data}


@api.get("/libros/{libro_id}/resenas")
def resenas_de_libro(libro_id: int):
    """Devuelve las reseñas de un libro con su promedio de puntaje.

    Este es el endpoint que consume la vista de Django.
    """
    try:
        respuesta = (
            supabase.table(TABLA)
            .select("*")
            .eq("libro_id", libro_id)
            .order("creada_en", desc=True)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    resenas = respuesta.data
    promedio = None
    if resenas:
        promedio = round(sum(r["puntaje"] for r in resenas) / len(resenas), 2)

    return {
        "libro_id": libro_id,
        "cantidad": len(resenas),
        "promedio": promedio,
        "resenas": resenas,
    }


@api.post("/resenas", status_code=201)
def crear_resena(resena: ResenaNueva):
    """Inserta una reseña nueva en Supabase y la devuelve ya guardada."""
    try:
        respuesta = supabase.table(TABLA).insert(resena.model_dump()).execute()
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    if not respuesta.data:
        raise HTTPException(status_code=502, detail="Supabase no devolvió la fila insertada")

    return respuesta.data[0]


@api.get("/libros")
def listar_libros():
    """Devuelve todos los libros ordenados del más nuevo al más viejo."""
    try:
        respuesta = (
            supabase.table(TABLA_LIBROS)
            .select("*")
            .order("creada_en", desc=True)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    return {"cantidad": len(respuesta.data), "libros": respuesta.data}


@api.get("/libros/{libro_id}")
def obtener_libro(libro_id: int):
    """Devuelve un libro por id, o 404 si no existe."""
    try:
        respuesta = (
            supabase.table(TABLA_LIBROS)
            .select("*")
            .eq("id", libro_id)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    if not respuesta.data:
        raise HTTPException(status_code=404, detail="no encontrado")

    return respuesta.data[0]


@api.post("/libros", status_code=201)
def crear_libro(libro: LibroDatos):
    """Inserta un libro nuevo en Supabase y lo devuelve ya guardado."""
    try:
        respuesta = (
            supabase.table(TABLA_LIBROS)
            .insert(libro.model_dump(exclude_none=True))
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    if not respuesta.data:
        raise HTTPException(status_code=502, detail="Supabase no devolvió la fila insertada")

    return respuesta.data[0]


@api.put("/libros/{libro_id}")
def actualizar_libro(libro_id: int, libro: LibroParcial):
    """Actualiza los campos que lleguen del libro y lo devuelve ya guardado."""
    cambios = {k: v for k, v in libro.model_dump().items() if v is not None}

    if not cambios:
        raise HTTPException(status_code=422, detail="No llega ningún campo para actualizar")

    try:
        respuesta = (
            supabase.table(TABLA_LIBROS)
            .update(cambios)
            .eq("id", libro_id)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    if not respuesta.data:
        raise HTTPException(status_code=404, detail="no encontrado")

    return respuesta.data[0]


@api.delete("/libros/{libro_id}")
def eliminar_libro(libro_id: int):
    """Borra el libro y devuelve la fila eliminada, o 404 si no existía."""
    try:
        respuesta = (
            supabase.table(TABLA_LIBROS)
            .delete()
            .eq("id", libro_id)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    if not respuesta.data:
        raise HTTPException(status_code=404, detail="no encontrado")

    return respuesta.data[0]


app.include_router(api)
