from django.contrib import admin

# Los libros ya no viven en SQLite: viven en Supabase y los expone un
# microservicio. No hay modelo Libro para registrar en el admin de Django.
# Sí quedan los modelos de la app prestamos (Lector, Prestamo).