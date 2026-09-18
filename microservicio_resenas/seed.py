"""Carga reseñas de ejemplo en Supabase. Idempotente: no duplica filas."""
import os

from supabase import create_client

RESENAS = [
    {"libro_id": 1, "lector": "Ana Gómez", "puntaje": 5, "comentario": "Imperdible, lo leí dos veces."},
    {"libro_id": 1, "lector": "Luis Pérez", "puntaje": 4, "comentario": "Muy bueno, algo denso al principio."},
    {"libro_id": 2, "lector": "Marta Díaz", "puntaje": 3, "comentario": "Entretenido pero desparejo."},
    {"libro_id": 2, "lector": "Jorge Ruiz", "puntaje": 5, "comentario": "Un clásico que envejeció bien."},
    {"libro_id": 3, "lector": "Sofía Lima", "puntaje": 4, "comentario": "Buen ritmo, final flojo."},
]


def main():
    supabase = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_KEY"])

    for resena in RESENAS:
        existentes = (
            supabase.table("resenas")
            .select("id")
            .eq("libro_id", resena["libro_id"])
            .eq("lector", resena["lector"])
            .execute()
        )
        if existentes.data:
            print(f"ya existe: {resena['lector']} sobre libro {resena['libro_id']}")
            continue

        supabase.table("resenas").insert(resena).execute()
        print(f"insertada: {resena['lector']} sobre libro {resena['libro_id']}")


if __name__ == "__main__":
    main()
