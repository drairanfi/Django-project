from django.urls import path

from . import views

app_name = "prestamos"

urlpatterns = [
    path("lectores/", views.lista_lectores, name="lista_lectores"),
    path("lector/<int:lector_id>/", views.detalle_lector, name="detalle_lector"),
    path("estado/<str:estado>/", views.prestamos_por_estado, name="prestamos_por_estado"),
    path("devolver/<int:prestamo_id>/", views.registrar_devolucion, name="devolver"),
    path("prestar/<int:libro_id>/", views.crear_prestamo, name="crear_prestamo"),
]