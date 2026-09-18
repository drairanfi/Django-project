from django.contrib import admin

from .models import Lector, Prestamo


@admin.register(Lector)
class LectorAdmin(admin.ModelAdmin):
    list_display = ["nombre", "email", "telefono", "fecha_registro"]
    search_fields = ["nombre", "email"]


@admin.register(Prestamo)
class PrestamoAdmin(admin.ModelAdmin):
    list_display = ["libro", "lector", "fecha_prestamo", "estado"]
    list_filter = ["estado"]
    search_fields = ["lector__nombre", "libro__titulo"]