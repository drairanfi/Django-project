from django import forms

from .models import Libro


class LibroForm(forms.ModelForm):
    """Formulario para crear y editar un Libro, con campos para crear categoría y autor nuevos."""

    categoria_nueva = forms.CharField(
        label="Categoría nueva (opcional)",
        required=False,
        help_text="Si no elegís una categoría existente, escribí acá el nombre de una nueva.",
    )
    autores_nuevos = forms.CharField(
        label="Autores nuevos (opcional)",
        required=False,
        help_text="Separados por coma, formato: Nombre Apellido. Se crean si no existen.",
    )

    class Meta:
        model = Libro
        fields = [
            "titulo",
            "isbn",
            "anio_publicacion",
            "paginas",
            "disponible",
            "categoria",
            "autores",
        ]