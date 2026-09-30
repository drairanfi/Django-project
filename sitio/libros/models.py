from django.db import models

# Este modelo ya no existe porque los libros viven en Supabase y los expone un
# microservicio. Django los lee y escribe por HTTP (ver libros/servicios.py).
# La tabla libros en Supabase tiene: id, titulo, isbn, anio_publicacion,
# paginas, disponible, categoria (texto) y autores (texto).