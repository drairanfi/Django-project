"""Microservicio de reseñas.

Expone una API HTTP sobre una tabla de Supabase (PostgreSQL en la nube).
Django NO habla con esta base de datos: habla con esta API por HTTP.
"""
import os

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from supabase import Client, create_client

TABLA = "resenas"

# Las credenciales llegan por variables de entorno. Nunca se escriben en el código.
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

app = FastAPI(
    title="Microservicio de Reseñas",
    description="API de reseñas de libros almacenadas en Supabase.",
    version="1.0.0",
)


class ResenaNueva(BaseModel):
    """Datos que el cliente envía para crear una reseña."""

    libro_id: int = Field(..., ge=1)
    lector: str = Field(..., min_length=1, max_length=100)
    puntaje: int = Field(..., ge=1, le=5)
    comentario: str = Field("", max_length=1000)


@app.get("/")
def raiz():
    """Describe el servicio para quien entra a la URL base."""
    return {
        "servicio": "microservicio-resenas",
        "version": "1.0.0",
        "base_de_datos": "Supabase (PostgreSQL)",
        "endpoints": [
            "GET /salud",
            "GET /resenas",
            "GET /libros/{libro_id}/resenas",
            "POST /resenas",
        ],
    }


@app.get("/salud")
def salud():
    """Health check: Render lo usa para saber si el servicio está vivo."""
    return {"estado": "ok"}


@app.get("/resenas")
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


@app.get("/libros/{libro_id}/resenas")
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


@app.post("/resenas", status_code=201)
def crear_resena(resena: ResenaNueva):
    """Inserta una reseña nueva en Supabase y la devuelve ya guardada."""
    try:
        respuesta = supabase.table(TABLA).insert(resena.model_dump()).execute()
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    if not respuesta.data:
        raise HTTPException(status_code=502, detail="Supabase no devolvió la fila insertada")

    return respuesta.data[0]
