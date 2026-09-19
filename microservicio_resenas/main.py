"""Microservicio de reseñas.

Expone una API HTTP sobre una tabla de Supabase (PostgreSQL en la nube).
Django NO habla con esta base de datos: habla con esta API por HTTP.
"""
import os

from fastapi import APIRouter, FastAPI, HTTPException
from pydantic import BaseModel, Field
from supabase import Client, create_client

TABLA = "resenas"

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

app = FastAPI(
    title="Microservicio de Reseñas",
    description="API de reseñas de libros almacenadas en Supabase.",
    version="1.0.0",
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


app.include_router(api)
