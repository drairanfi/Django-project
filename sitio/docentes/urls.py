from django.urls import path

from . import views

app_name = "docentes"

urlpatterns = [
    path("", views.lista_docentes, name="lista_docentes"),
]
