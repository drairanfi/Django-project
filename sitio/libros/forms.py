from django import forms


class LibroForm(forms.Form):
    """Formulario para crear y editar un libro.

    No es un ModelForm: el libro no vive en el ORM. Los datos viajan a un
    microservicio (Python, NodeJS, Java o PHP), que valida y guarda en Supabase.
    El formulario solo arma el JSON y deja que el servicio haga su parte.
    """

    titulo = forms.CharField(max_length=200)
    isbn = forms.CharField(max_length=20)
    anio_publicacion = forms.IntegerField(required=False)
    paginas = forms.IntegerField(required=False)
    disponible = forms.BooleanField(required=False)
    categoria = forms.CharField(max_length=100, required=False)
    autores = forms.CharField(max_length=500, required=False)

    def datos_para_el_servicio(self):
        """Convierte los datos limpios en el dict JSON que espera el microservicio."""
        return {
            "titulo": self.cleaned_data["titulo"],
            "isbn": self.cleaned_data["isbn"],
            "anio_publicacion": self.cleaned_data.get("anio_publicacion"),
            "paginas": self.cleaned_data.get("paginas"),
            "disponible": self.cleaned_data.get("disponible", False),
            "categoria": self.cleaned_data.get("categoria", ""),
            "autores": self.cleaned_data.get("autores", ""),
        }