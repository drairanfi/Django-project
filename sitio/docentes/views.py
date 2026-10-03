from django.shortcuts import render

from .models import Docente


def lista_docentes(request):
    """Consulta todos los Docentes y los envía al template dentro del context."""
    docentes = Docente.objects.all()

    context = {
        "docentes": docentes,
    }
    return render(request, "docentes/lista_docentes.html", context)
