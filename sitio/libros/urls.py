from django.urls import path

from . import views

app_name = "libros"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("libro/<int:libro_id>/", views.detalle_libro, name="detalle_libro"),
    path("categoria/<str:categoria>/", views.libros_por_categoria, name="por_categoria"),
    path("autor/<str:autor>/", views.libros_por_autor, name="por_autor"),
    path("libro/<int:libro_id>/resenas/", views.resenas_libro, name="resenas_libro"),
    path("libro/nuevo/", views.crear_libro, name="crear_libro"),
    path("libro/<int:libro_id>/editar/", views.editar_libro, name="editar_libro"),
    path("libro/<int:libro_id>/eliminar/", views.eliminar_libro, name="eliminar_libro"),
    path("asistente/", views.asistente, name="asistente"),
]