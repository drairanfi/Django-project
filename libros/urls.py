from django.urls import path

from . import views

app_name = "libros"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("libro/<int:libro_id>/", views.detalle_libro, name="detalle_libro"),
    path("categoria/<int:categoria_id>/", views.libros_por_categoria, name="por_categoria"),
    path("autor/<int:autor_id>/", views.libros_por_autor, name="por_autor"),
]