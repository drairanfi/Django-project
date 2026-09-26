"""Genera el PDF explicativo de la vista del asistente con IA."""
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    HRFlowable, KeepTogether, PageBreak, Paragraph, SimpleDocTemplate,
    Spacer, Table, TableStyle,
)

RAIZ = Path("/Users/ESTUDIO/Django-project")
SALIDA = RAIZ / "docs" / "asistente-virtual.pdf"

AZUL = colors.HexColor("#1B3A5C")
AZUL_CLARO = colors.HexColor("#2E6DA4")
GRIS = colors.HexColor("#4A4A4A")
GRIS_FONDO = colors.HexColor("#F2F4F7")
BORDE = colors.HexColor("#C9D2DD")
VERDE = colors.HexColor("#1E7A46")

hojas = getSampleStyleSheet()


def estilo(nombre, **kw):
    return ParagraphStyle(nombre, parent=hojas["Normal"], **kw)


H1 = estilo("H1", fontName="Helvetica-Bold", fontSize=19, leading=23,
            textColor=AZUL, spaceBefore=6, spaceAfter=10)
H2 = estilo("H2", fontName="Helvetica-Bold", fontSize=13.5, leading=17,
            textColor=AZUL_CLARO, spaceBefore=16, spaceAfter=7)
H3 = estilo("H3", fontName="Helvetica-Bold", fontSize=11, leading=14,
            textColor=GRIS, spaceBefore=11, spaceAfter=5)
CUERPO = estilo("Cuerpo", fontSize=9.7, leading=14.5, alignment=TA_JUSTIFY,
                spaceAfter=7, textColor=colors.HexColor("#22252A"))
NOTA = estilo("Nota", fontSize=9, leading=13, textColor=GRIS,
              leftIndent=10, spaceAfter=7)
CODIGO = estilo("Codigo", fontName="Courier", fontSize=7.9, leading=10.4,
                textColor=colors.HexColor("#1A1A1A"))
DIAGRAMA = estilo("Diagrama", fontName="Courier", fontSize=8.2, leading=11.5,
                  textColor=AZUL)
CELDA = estilo("Celda", fontSize=8.7, leading=11.8)
CELDA_B = estilo("CeldaB", fontName="Helvetica-Bold", fontSize=8.7, leading=11.8,
                 textColor=colors.white)
CELDA_COD = estilo("CeldaCod", fontName="Courier", fontSize=7.9, leading=11)


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def esc_cod(t):
    return esc(t).replace(" ", "&nbsp;")


def parrafo(t):
    return Paragraph(t, CUERPO)


def codigo(texto, titulo=None):
    lineas = [Paragraph(esc_cod(l) if l.strip() else "&nbsp;", CODIGO)
              for l in texto.strip("\n").split("\n")]
    t = Table([[lineas]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), GRIS_FONDO),
        ("BOX", (0, 0), (-1, -1), 0.6, BORDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    piezas = []
    if titulo:
        piezas.append(Paragraph(f"<font face='Courier' size=8 color='#2E6DA4'>{esc(titulo)}</font>",
                                estilo("ct", spaceAfter=3)))
    piezas.append(t)
    piezas.append(Spacer(1, 8))
    return piezas


def diagrama(texto):
    lineas = [Paragraph(esc_cod(l) if l.strip() else "&nbsp;", DIAGRAMA)
              for l in texto.strip("\n").split("\n")]
    t = Table([[lineas]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEF4FA")),
        ("BOX", (0, 0), (-1, -1), 0.6, AZUL_CLARO),
        ("LEFTPADDING", (0, 0), (-1, -1), 12),
        ("TOPPADDING", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
    ]))
    return [t, Spacer(1, 10)]


def tabla(cabecera, filas, anchos, mono_col=None):
    datos = [[Paragraph(c, CELDA_B) for c in cabecera]]
    for f in filas:
        fila = []
        for i, c in enumerate(f):
            est = CELDA_COD if (mono_col is not None and i in mono_col) else CELDA
            fila.append(Paragraph(c, est))
        datos.append(fila)
    t = Table(datos, colWidths=anchos, repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), AZUL_CLARO),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, GRIS_FONDO]),
        ("GRID", (0, 0), (-1, -1), 0.4, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return [t, Spacer(1, 10)]


def destacado(titulo, texto):
    contenido = [
        Paragraph(f"<b>{titulo}</b>", estilo("dt", fontSize=9.5, leading=13,
                                             textColor=VERDE, spaceAfter=4)),
        Paragraph(texto, estilo("dc", fontSize=9.3, leading=13.5, alignment=TA_JUSTIFY)),
    ]
    t = Table([[contenido]], colWidths=[16.4 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EDF7F1")),
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, VERDE),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    return [t, Spacer(1, 10)]


def glosario(titulo, entradas):
    piezas = [Paragraph(titulo, H3)]
    datos = []
    for termino, definicion in entradas:
        datos.append([
            Paragraph(f"<b>{termino}</b>", estilo("gt", fontSize=8.8, leading=12)),
            Paragraph(definicion, estilo("gd", fontSize=8.8, leading=12.4,
                                         alignment=TA_JUSTIFY)),
        ])
    t = Table(datos, colWidths=[4.0 * cm, 12.4 * cm])
    t.setStyle(TableStyle([
        ("ROWBACKGROUNDS", (0, 0), (-1, -1), [colors.white, GRIS_FONDO]),
        ("LINEBELOW", (0, 0), (-1, -2), 0.3, BORDE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    piezas.append(t)
    piezas.append(Spacer(1, 10))
    if len(entradas) <= 7:
        return [KeepTogether(piezas)]
    return piezas


def pie(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(BORDE)
    canvas.setLineWidth(0.4)
    canvas.line(2.2 * cm, 1.6 * cm, A4[0] - 2.2 * cm, 1.6 * cm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(GRIS)
    canvas.drawString(2.2 * cm, 1.15 * cm,
                      "Biblioteca Comunitaria — Vista del Asistente con IA")
    canvas.drawRightString(A4[0] - 2.2 * cm, 1.15 * cm, f"Página {doc.page}")
    canvas.restoreState()


c = []

# ---------------------------------------------------------------- PORTADA
c.append(Spacer(1, 3.4 * cm))
c.append(Paragraph("El Asistente con IA",
                   estilo("Tit", fontName="Helvetica-Bold", fontSize=27, leading=32,
                          textColor=AZUL, alignment=TA_CENTER)))
c.append(Spacer(1, 0.5 * cm))
c.append(Paragraph("La vista asistente() explicada línea por línea",
                   estilo("Sub", fontSize=13, leading=18, textColor=AZUL_CLARO,
                          alignment=TA_CENTER)))
c.append(Spacer(1, 1.1 * cm))
c.append(HRFlowable(width="55%", thickness=1, color=BORDE, hAlign="CENTER"))
c.append(Spacer(1, 1.1 * cm))
c.append(Paragraph(
    "Proyecto Biblioteca Comunitaria<br/>Trabajo práctico de Desarrollo Web",
    estilo("Meta", fontSize=11, leading=17, textColor=GRIS, alignment=TA_CENTER)))
c.append(Spacer(1, 2.2 * cm))

c += tabla(
    ["Componente", "Archivo", "Rol"],
    [["Ruta", "sitio/libros/urls.py", "Asocia /asistente/ con la vista"],
     ["Vista", "sitio/libros/views.py", "Recibe la pregunta, llama al servicio, arma el context"],
     ["Servicio", "sitio/libros/servicios.py", "Arma el contexto, llama a la API de IA, maneja errores"],
     ["Configuración", "sitio/biblioteca/settings.py", "Lee la clave, la URL, el modelo y el timeout"],
     ["Template", "sitio/libros/templates/libros/asistente.html", "Muestra el formulario y la respuesta"]],
    [2.6 * cm, 6.4 * cm, 7.4 * cm], mono_col=[1])

c.append(PageBreak())

# ------------------------------------------------------- 1. QUÉ ES
c.append(Paragraph("1. Qué es esta vista y cómo encaja", H1))
c.append(parrafo(
    "La vista <font face='Courier' size=8.5>asistente()</font> es la sexta vista de la "
    "app <font face='Courier' size=8.5>libros</font>. Su trabajo es simple de enunciar y "
    "complejo de lograr: <b>dejar que un usuario le pregunte en lenguaje natural a una "
    "inteligencia artificial cosas sobre el catálogo</b> (qué libros hay, quién tiene uno "
    "prestado, cómo se devuelve un préstamo) y mostrar la respuesta."))
c.append(parrafo(
    "La particularidad es que la IA es un sistema <b>externo</b>, como el microservicio de "
    "reseñas. La vista no sabe cómo se genera la respuesta: solo sabe pedirla y mostrarla. "
    "Todo el conocimiento de la IA —el formato del pedido, la URL, la clave— vive en "
    "<font face='Courier' size=8.5>servicios.py</font>, y la configuración en "
    "<font face='Courier' size=8.5>settings.py</font>."))

c.append(Paragraph("El requisito que cumple", H2))
c.append(parrafo(
    "La consigna pedía que el proyecto consumiera una <b>API de inteligencia artificial</b> "
    "para responder preguntas sobre el catálogo. El asistente usa Gemini, de Google, pero "
    "el código no conoce a Gemini: conoce una URL, un modelo y una clave."))
c += destacado(
    "La idea central",
    "La IA se trata como un recurso remoto y falible. Si la clave falta o la API se cae, "
    "la página se muestra igual con un aviso; nunca un error 500. Es el mismo criterio de "
    "degradación controlada que ya usan las reseñas.")

c.append(PageBreak())

# ------------------------------------------------------- 2. LA RUTA
c.append(Paragraph("2. La ruta: cómo se llega a la vista", H1))
c += codigo("""
from django.urls import path
from . import views

app_name = "libros"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("libro/<int:libro_id>/", views.detalle_libro, name="detalle_libro"),
    path("categoria/<int:categoria_id>/", views.libros_por_categoria, name="por_categoria"),
    path("autor/<int:autor_id>/", views.libros_por_autor, name="por_autor"),
    path("libro/<int:libro_id>/resenas/", views.resenas_libro, name="resenas_libro"),
    path("asistente/", views.asistente, name="asistente"),
]
""", "sitio/libros/urls.py (líneas 7-13)")
c.append(parrafo(
    "La línea que importa es la última: <font face='Courier' size=8.5>path(\"asistente/\", "
    "views.asistente, name=\"asistente\")</font>. Tres decisiones que vale la pena leer:"))
c.append(Paragraph(
    "<b>1.</b> La URL <font face='Courier' size=8.5>/asistente/</font> no lleva parámetro: "
    "la vista no necesita un id en la ruta porque la pregunta viaja por el <b>cuerpo del "
    "POST</b>, no por la URL. A diferencia de "
    "<font face='Courier' size=8.5>libro/&lt;int:libro_id&gt;/</font>, acá no hay nada "
    "dinámico que capturar.", NOTA))
c.append(Paragraph(
    "<b>2.</b> La misma URL atiende <b>dos métodos</b>: GET muestra el formulario vacío y "
    "POST procesa la pregunta. La vista decide según "
    "<font face='Courier' size=8.5>request.method</font>. Esto no requiere nada especial "
    "en urls.py: el enrutador de Django no distingue métodos.", NOTA))
c.append(Paragraph(
    "<b>3.</b> El <font face='Courier' size=8.5>name=\"asistente\"</font> es lo que permite "
    "escribir <font face='Courier' size=8.5>{% url 'libros:asistente' %}</font> en los "
    "templates sin hardcodear la URL. El prefijo <font face='Courier' size=8.5>libros:</font> "
    "viene de <font face='Courier' size=8.5>app_name = \"libros\"</font>. Ese link está en "
    "la barra de <font face='Courier' size=8.5>base.html</font>.", NOTA))

# ------------------------------------------------------- 3. LA VISTA
c.append(PageBreak())
c.append(Paragraph("3. La vista: views.py", H1))
c.append(parrafo(
    "La vista entera, tal como está en el archivo, son 20 líneas. La leemos de arriba a "
    "abajo."))
c += codigo("""
def asistente(request):
    \"\"\"Muestra el formulario (GET) y consulta la IA con el contexto del proyecto (POST).\"\"\"
    respuesta = ""
    error = ""

    if request.method == "POST":
        pregunta = request.POST.get("pregunta", "").strip()
        if not pregunta:
            error = "Escribí una pregunta primero"
        else:
            try:
                respuesta = servicios.preguntar_al_asistente(pregunta)
            except servicios.IANoDisponible as fallo:
                error = f"No se pudo consultar a la IA ({fallo})"

    context = {
        "respuesta": respuesta,
        "error": error,
    }
    return render(request, "libros/asistente.html", context)
""", "sitio/libros/views.py (líneas 104-123)")

c.append(Paragraph("3.1 Los dos acumuladores", H2))
c.append(parrafo(
    "La vista arranca inicializando dos variables en vacío:"))
c += codigo("""
respuesta = ""
error = ""
""")
c.append(parrafo(
    "Son <b>acumuladores</b>: se llenan a lo largo del flujo y se mandan siempre al "
    "template. Gracias a estos valores por defecto, el template puede asumir que "
    "<font face='Courier' size=8.5>respuesta</font> y <font face='Courier' size=8.5>error</font> "
    "siempre existen en el context. En un GET —donde todavía no hay nada que mostrar— "
    "quedan como cadenas vacías, y el template las ignora con sus "
    "<font face='Courier' size=8.5>{% if %}</font>."))

c.append(Paragraph("3.2 GET vs. POST", H2))
c.append(parrafo(
    "El <font face='Courier' size=8.5>if request.method == \"POST\"</font> separa los dos "
    "usos de la misma URL. En <b>GET</b> (abrir la página) el bloque se salta entero y la "
    "vista va directo a renderizar el formulario. En <b>POST</b> (enviar el formulario) se "
    "ejecuta la lógica de consulta."))
c += destacado(
    "Por qué no usar el GET para preguntar",
    "Si la pregunta fuera por GET, quedaría visible en la URL, en el historial y en los "
    "logs del servidor. Además, un GET debe ser una operación que no modifica nada. Acá "
    "cada consulta dispara una llamada a una API de pago, así que debe ser un POST.")

c.append(Paragraph("3.3 Leer y limpiar la pregunta", H2))
c += codigo("""
pregunta = request.POST.get("pregunta", "").strip()
""")
c.append(parrafo(
    "<font face='Courier' size=8.5>request.POST</font> es un diccionario con los campos del "
    "formulario enviado. <font face='Courier' size=8.5>.get(\"pregunta\", \"\")</font> lee "
    "el campo llamado <font face='Courier' size=8.5>pregunta</font> (el <font "
    "face='Courier' size=8.5>name</font> del textarea) y devuelve una cadena vacía si "
    "faltara. El <font face='Courier' size=8.5>.strip()</font> quita espacios al inicio y "
    "al final, de modo que <font face='Courier' size=8.5>\"   \"</font> se convierte en "
    "<font face='Courier' size=8.5>\"\"</font>."))

c.append(Paragraph("3.4 Validar y consultar", H2))
c += codigo("""
if not pregunta:
    error = "Escribí una pregunta primero"
else:
    try:
        respuesta = servicios.preguntar_al_asistente(pregunta)
    except servicios.IANoDisponible as fallo:
        error = f"No se pudo consultar a la IA ({fallo})"
""")
c.append(parrafo(
    "Hay dos caminos de fallo y uno de éxito:"))
c.append(Paragraph(
    "<b>1.</b> Si la pregunta quedó vacía tras el strip, no vale la pena gastar una llamada "
    "a la API: se setea el error y se termina.", NOTA))
c.append(Paragraph(
    "<b>2.</b> Si hay pregunta, se llama a "
    "<font face='Courier' size=8.5>servicios.preguntar_al_asistente(pregunta)</font>. Esa "
    "función puede lanzar <font face='Courier' size=8.5>IANoDisponible</font>, la excepción "
    "propia del proyecto para cuando la IA falla. Si ocurre, la vista la atrapa y convierte "
    "el fallo en un mensaje legible.", NOTA))
c.append(Paragraph(
    "<b>3.</b> Si todo sale bien, <font face='Courier' size=8.5>respuesta</font> queda con "
    "el texto de la IA. Nótese el <font face='Courier' size=8.5>f-string</font> del error: "
    "incluye el detalle de la excepción entre paréntesis, lo que ayuda a diagnosticar sin "
    "mostrar un traceback.", NOTA))

c.append(Paragraph("3.5 El context y el render", H2))
c += codigo("""
context = {
    "respuesta": respuesta,
    "error": error,
}
return render(request, "libros/asistente.html", context)
""")
c.append(parrafo(
    "Cumple el patrón de tres pasos que exige el proyecto: el context es una variable con "
    "nombre y se usa el shortcut <font face='Courier' size=8.5>render()</font>. El template "
    "recibe exactamente dos variables: lo que respondió la IA (o vacío) y el error (o "
    "vacío). No hay más estado que ese."))

c.append(PageBreak())

# ------------------------------------------------------- 4. EL SERVICIO
c.append(Paragraph("4. El servicio: servicios.py", H1))
c.append(parrafo(
    "La vista es delgada porque toda la complejidad externa está en "
    "<font face='Courier' size=8.5>servicios.py</font>. Este módulo concentra <b>todo</b> "
    "lo que el proyecto sabe sobre la API de IA, igual que ya hacía con el microservicio de "
    "reseñas. Hay tres piezas: la excepción propia, el cliente HTTP genérico "
    "<font face='Courier' size=8.5>_pedir()</font>, y las dos funciones específicas del "
    "asistente: <font face='Courier' size=8.5>armar_contexto_biblioteca()</font> y "
    "<font face='Courier' size=8.5>preguntar_al_asistente()</font>."))

c.append(Paragraph("4.1 La excepción propia", H2))
c += codigo("""
class IANoDisponible(Exception):
    \"\"\"La API de IA no respondió, tardó demasiado o falta la clave en biblioteca/.env.\"\"\"
""", "sitio/libros/servicios.py (líneas 21-22)")
c.append(parrafo(
    "Es una excepción propia, del mismo estilo que "
    "<font face='Courier' size=8.5>MicroservicioNoDisponible</font>. Define un vocabulario "
    "del problema: <i>\"la IA no está\"</i>. Todas las fallas técnicas del lado de la IA —red "
    "caída, timeout, respuesta malformada, falta de clave— se traducen a esta única "
    "excepción. Así la vista atrapa <b>una</b> cosa, sin saber nada de urllib ni de HTTP."))

c.append(Paragraph("4.2 El cliente HTTP genérico", H2))
c += codigo("""
def _pedir(url, datos=None, timeout=5, error_cls=MicroservicioNoDisponible):
    \"\"\"Hace la petición HTTP y devuelve el JSON ya parseado.\"\"\"
    cuerpo = None
    cabeceras = {"Accept": "application/json"}

    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"

    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras)

    try:
        with urllib.request.urlopen(peticion, timeout=timeout) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise error_cls(str(error)) from error
""", "sitio/libros/servicios.py (líneas 25-40)")
c.append(parrafo(
    "Esta función es la misma que usa el microservicio de reseñas, con dos diferencias de "
    "diseño para servir a la IA:"))
c.append(Paragraph(
    "<b>1.</b> El parámetro <font face='Courier' size=8.5>timeout</font> ahora es "
    "configurable: el asistente le pasa 15 segundos, porque una consulta de IA tarda más "
    "que una lectura de reseñas.", NOTA))
c.append(Paragraph(
    "<b>2.</b> El parámetro <font face='Courier' size=8.5>error_cls</font> dice qué "
    "excepción lanzar. El asistente pasa <font face='Courier' size=8.5>IANoDisponible</font> "
    "para que el error llegue con el nombre correcto.", NOTA))
c.append(parrafo(
    "El cuerpo: si <font face='Courier' size=8.5>datos</font> no es None, se serializa a "
    "JSON con <font face='Courier' size=8.5>json.dumps</font> y se manda en el cuerpo del "
    "request con <font face='Courier' size=8.5>Content-Type: application/json</font>. Eso "
    "es lo que convierte a la petición en un POST. El `with` garantiza cerrar la conexión, "
    "y los tres errores atrapados (red, timeout, JSON inválido) se convierten en "
    "<font face='Courier' size=8.5>error_cls</font>."))

c.append(PageBreak())

c.append(Paragraph("4.3 Armar el contexto del catálogo", H2))
c.append(parrafo(
    "Una IA externa no sabe nada del proyecto. Para que responda con datos reales y no "
    "invente, la función <font face='Courier' size=8.5>armar_contexto_biblioteca()</font> "
    "arma un <b>texto plano</b> con la descripción de la app, cómo funciona un préstamo y "
    "los datos actuales de la base. Ese texto viaja con la pregunta."))
c += codigo("""
def armar_contexto_biblioteca():
    \"\"\"Devuelve un texto con el funcionamiento de la app y los datos actuales para la IA.\"\"\"
    lineas = []

    lineas.append("DESCRIPCION DE LA APP:")
    lineas.append(
        "La biblioteca comunitaria es un sistema web en Django. Un lector "
        "registrado se lleva un libro prestado: eso se llama un préstamo. "
        "Cada libro tiene un campo 'disponible': True significa que está en la "
        "biblioteca y se puede prestar; False significa que alguien ya lo tiene. ..."
    )

    lineas.append("COMO FUNCIONA UN PRESTAMO:")
    lineas.append(
        "- Prestar: se elige un lector y un libro disponible, se crea el "
        "préstamo con estado 'activo' y el libro pasa a disponible=False. ..."
    )
    lineas.append(
        "- Devolver: el préstamo activo pasa a estado 'devuelto', se guarda la "
        "fecha de devolución y el libro vuelve a disponible=True. ..."
    )

    lineas.append("QUE SE PUEDE HACER EN LA APP:")
    lineas.append("- Ver el catálogo completo y si cada libro está disponible o prestado.")
    lineas.append("- Filtrar libros por categoría y por autor.")
    lineas.append("- Ver el detalle de cada libro, sus autores y sus reseñas.")
    lineas.append("- Registrar y devolver préstamos, y verlos por estado.")
    lineas.append("- Ver el historial de préstamos de cada lector.")
    return "\n".join(lineas)
""", "sitio/libros/servicios.py (líneas 61-124, resumido)")
c.append(parrafo(
    "Después de la descripción estática, la función <b>consulta el ORM</b> y vuelca los "
    "datos reales:"))
c += codigo("""
    lineas.append("DATOS ACTUALES DEL PROYECTO:")
    lineas.append("LIBROS:")
    for libro in Libro.objects.all():
        autores = ", ".join(str(autor) for autor in libro.autores.all())
        estado = "disponible" if libro.disponible else "prestado"
        lineas.append(
            f"- {libro.titulo} ({libro.anio_publicacion}), "
            f"categoria {libro.categoria.nombre}, autores: {autores}, {estado}"
        )

    lineas.append("CATEGORIAS:")
    for categoria in Categoria.objects.all():
        lineas.append(f"- {categoria.nombre}")

    lineas.append("LECTORES:")
    for lector in Lector.objects.all():
        lineas.append(f"- {lector.nombre} ({lector.email})")

    lineas.append("PRESTAMOS:")
    for prestamo in Prestamo.objects.all():
        lineas.append(
            f"- {prestamo.libro.titulo} -> {prestamo.lector.nombre} "
            f"({prestamo.estado}, desde {prestamo.fecha_prestamo})"
        )

    return "\n".join(lineas)
""", "sitio/libros/servicios.py (líneas 99-124)")
c.append(parrafo(
    "La función importa los cuatro modelos del proyecto: "
    "<font face='Courier' size=8.5>Libro</font> y <font face='Courier' size=8.5>Categoria</font> "
    "de <font face='Courier' size=8.5>libros</font>, y "
    "<font face='Courier' size=8.5>Lector</font> y <font face='Courier' size=8.5>Prestamo</font> "
    "de <font face='Courier' size=8.5>prestamos</font>. Es el único momento en que el "
    "asistente toca la base local: lee, no escribe."))
c += destacado(
    "Por qué el contexto se arma con datos reales",
    "Si solo se le diera a la IA la descripción de la app, inventaría datos. El contexto "
    "con los libros y préstamos actuales le da <b>anclaje</b>: la consigna del mensaje de "
    "sistema le prohíbe responder con información que no esté en el contexto. Así el "
    "asistente habla de los 5 libros que hay de verdad, no de los que imagina.")

c.append(PageBreak())

c.append(Paragraph("4.4 La función que llama a la IA", H2))
c += codigo("""
def preguntar_al_asistente(pregunta):
    \"\"\"Envía la pregunta con el contexto del catálogo a la API de IA y devuelve la respuesta.\"\"\"
    if not settings.IA_API_KEY:
        raise IANoDisponible("falta IA_API_KEY en biblioteca/.env")

    contexto = armar_contexto_biblioteca()
    mensaje_sistema = (
        "Sos el asistente de la Biblioteca Comunitaria, un sistema web de "
        "préstamo de libros. Respondé SOLO usando la información que te doy en "
        "el contexto (el funcionamiento de la app y sus datos actuales), nunca "
        "inventes datos ni funciones que no estén en el contexto. ... "
        "Respondé en español, breve y en el mismo idioma que la pregunta."
    )

    url = f"{settings.IA_API_URL}/models/{settings.IA_MODEL}:generateContent?key={settings.IA_API_KEY}"
    datos = {
        "contents": [
            {
                "parts": [
                    {"text": mensaje_sistema},
                    {"text": f"CONTEXTO DEL PROYECTO:\\n{contexto}\\n\\nPREGUNTA: {pregunta}"},
                ]
            }
        ],
        "generationConfig": {"temperature": 0.2},
    }

    respuesta = _pedir(url, datos, timeout=settings.IA_TIMEOUT, error_cls=IANoDisponible)
    return respuesta["candidates"][0]["content"]["parts"][0]["text"].strip()
""", "sitio/libros/servicios.py (líneas 127-161)")

c.append(Paragraph("4.4.1 La clave como guarda", H2))
c.append(parrafo(
    "La primera línea es una <b>validación de configuración</b>:"))
c += codigo("""
if not settings.IA_API_KEY:
    raise IANoDisponible("falta IA_API_KEY en biblioteca/.env")
""")
c.append(parrafo(
    "Si no hay clave configurada, no tiene sentido armar la URL (la petición fallaría de "
    "todas formas). Mejor fallar temprano, con un mensaje que dice exactamente qué falta. "
    "La vista atrapa esto como un <font face='Courier' size=8.5>IANoDisponible</font> más "
    "y muestra el aviso."))

c.append(Paragraph("4.4.2 El mensaje de sistema", H2))
c.append(parrafo(
    "El <font face='Courier' size=8.5>mensaje_sistema</font> es la <b>instrucción de rol</b> "
    "para la IA: le dice quién es, qué debe responder y qué debe evitar. Es la frontera "
    "técnica del problema de las alucinaciones: prohibir explícitamente inventar datos y "
    "obligarla a basarse solo en el contexto. También le pide responder en español."))

c.append(Paragraph("4.4.3 El formato del pedido a Gemini", H2))
c += codigo("""
url = f"{settings.IA_API_URL}/models/{settings.IA_MODEL}:generateContent?key={settings.IA_API_KEY}"
datos = {
    "contents": [
        {
            "parts": [
                {"text": mensaje_sistema},
                {"text": f"CONTEXTO DEL PROYECTO:\\n{contexto}\\n\\nPREGUNTA: {pregunta}"},
            ]
        }
    ],
    "generationConfig": {"temperature": 0.2},
}
""")
c.append(parrafo(
    "Cada proveedor de IA define su propio protocolo. Gemini usa "
    "<font face='Courier' size=8.5>:generateContent</font> como acción, pasa la clave por "
    "la URL con <font face='Courier' size=8.5>?key=...</font> (no por una cabecera de "
    "autorización, como haría OpenAI) y espera los textos dentro de "
    "<font face='Courier' size=8.5>contents → parts → text</font>."))
c.append(parrafo(
    "La pregunta y el contexto viajan <b>en el mismo part</b>, separados por etiquetas "
    "legibles: <font face='Courier' size=8.5>CONTEXTO DEL PROYECTO:</font> y "
    "<font face='Courier' size=8.5>PREGUNTA:</font>. El mensaje de sistema va en un part "
    "anterior. <font face='Courier' size=8.5>temperature: 0.2</font> pide respuestas "
    "predecibles y apegadas a los datos: no queremos que el asistente sea creativo, queremos "
    "que sea exacto."))

c.append(Paragraph("4.4.4 Leer la respuesta", H2))
c += codigo("""
respuesta = _pedir(url, datos, timeout=settings.IA_TIMEOUT, error_cls=IANoDisponible)
return respuesta["candidates"][0]["content"]["parts"][0]["text"].strip()
""")
c.append(parrafo(
    "Gemini devuelve un JSON anidado: una lista de <font face='Courier' size=8.5>candidates</font> "
    "(respuestas posibles, tomamos la primera), cada una con su "
    "<font face='Courier' size=8.5>content</font>, que tiene "
    "<font face='Courier' size=8.5>parts</font> (fragmentos de texto) y en el primero su "
    "<font face='Courier' size=8.5>text</font>. El <font face='Courier' size=8.5>.strip()</font> "
    "final limpia espacios. Nótese cómo se navega el JSON: tres índices anidados con sus "
    "claves literales, que es la parte más frágil del código: si Gemini cambia el formato, "
    "esto rompe con un <font face='Courier' size=8.5>KeyError</font> que "
    "<font face='Courier' size=8.5>_pedir</font> traduciría a "
    "<font face='Courier' size=8.5>IANoDisponible</font>."))

c.append(PageBreak())

# ------------------------------------------------------- 5. SETTINGS
c.append(Paragraph("5. La configuración: settings.py", H1))
c.append(parrafo(
    "El asistente lee cuatro valores de configuración. La regla del proyecto es que las "
    "credenciales <b>nunca</b> se escriben en el código: se leen de variables de entorno, y "
    "en local desde un archivo <font face='Courier' size=8.5>.env</font> que "
    "<font face='Courier' size=8.5>settings.py</font> parsea solo."))
c += codigo("""
IA_API_KEY = os.environ.get('IA_API_KEY') or _ENV_LOCAL.get('IA_API_KEY', '')
IA_API_URL = os.environ.get('IA_API_URL') or _ENV_LOCAL.get(
    'IA_API_URL', 'https://generativelanguage.googleapis.com/v1beta',
)
IA_MODEL = os.environ.get('IA_MODEL') or _ENV_LOCAL.get('IA_MODEL', 'gemini-2.5-flash')
IA_TIMEOUT = 15  # segundos: una consulta de IA tarda más que el microservicio
""", "sitio/biblioteca/settings.py (líneas 224-229)")
c.append(parrafo(
    "El patrón <font face='Courier' size=8.5>os.environ.get(...) or _ENV_LOCAL.get(...)</font> "
    "es la jerarquía de precedencia: si la variable ya está en el entorno (por ejemplo en "
    "Vercel), gana esa; si no, se busca en el <font face='Courier' size=8.5>.env</font> local; "
    "y solo si no hay nada, se usa el valor por defecto. Así la misma configuración funciona "
    "en la nube y en la máquina del desarrollador sin cambiar una línea."))

c.append(Paragraph("5.1 De dónde sale _ENV_LOCAL", H2))
c += codigo("""
def _leer_env_local():
    \"\"\"Lee las variables del .env de esta carpeta y las devuelve en un dict.\"\"\"
    ruta = Path(__file__).resolve().parent / '.env'
    variables = {}
    if not ruta.exists():
        return variables
    for linea in ruta.read_text(encoding='utf-8').splitlines():
        linea = linea.strip()
        if not linea or linea.startswith('#') or '=' not in linea:
            continue
        nombre, _, valor = linea.partition('=')
        variables[nombre.strip()] = valor.strip().strip("'\\\"")
    return variables


_ENV_LOCAL = _leer_env_local()
""", "sitio/biblioteca/settings.py (líneas 207-222)")
c.append(parrafo(
    "Lee el archivo <font face='Courier' size=8.5>biblioteca/.env</font> —que no se "
    "versiona— línea por línea, ignora comentarios y líneas sin <font face='Courier' "
    "size=8.5>=</font>, y guarda pares clave/valor. El "
    "<font face='Courier' size=8.5>.strip(\"'\\\"\")</font> quita las comillas con las que se "
    "envuelven los valores en el archivo, porque la shell las necesitaría pero el valor "
    "real no las incluye."))

c.append(PageBreak())

# ------------------------------------------------------- 6. TEMPLATE
c.append(Paragraph("6. El template: asistente.html", H1))
c += codigo("""
{% extends "base.html" %}

{% block title %}Asistente con IA{% endblock %}

{% block content %}
    <h2>Asistente con IA</h2>
    <p>Preguntá por los libros, autores, categorías, lectores o préstamos de la biblioteca.</p>

    <form method="post">
        {% csrf_token %}
        <p><label for="pregunta">Tu pregunta:</label></p>
        <p><textarea id="pregunta" name="pregunta" rows="4" cols="60" required></textarea></p>
        <p><button type="submit">Preguntar</button></p>
    </form>

    {% if error %}
        <p><strong>{{ error }}</strong></p>
    {% endif %}

    {% if respuesta %}
        <hr>
        <h3>Respuesta</h3>
        <p>{{ respuesta|linebreaks }}</p>
    {% endif %}
{% endblock %}
""", "sitio/libros/templates/libros/asistente.html")
c.append(parrafo(
    "El template no consulta la base ni llama a la IA: solo muestra las dos variables del "
    "context. Cada bloque tiene su lógica:"))
c.append(Paragraph(
    "<b>1.</b> <font face='Courier' size=8.5>{% extends \"base.html\" %}</font> hereda la "
    "estructura común (barra de navegación, título, pie). El bloque "
    "<font face='Courier' size=8.5>{% block content %}</font> es donde este template mete "
    "su contenido.", NOTA))
c.append(Paragraph(
    "<b>2.</b> El formulario usa <font face='Courier' size=8.5>method=\"post\"</font>, "
    "necesario para que la vista entre en la rama POST. El "
    "<font face='Courier' size=8.5>{% csrf_token %}</font> es la protección CSRF de Django: "
    "sin él, el POST sería rechazado con un 403. El textarea tiene "
    "<font face='Courier' size=8.5>name=\"pregunta\"</font>, que es la clave que la vista "
    "lee con <font face='Courier' size=8.5>request.POST.get(\"pregunta\")</font>, y "
    "<font face='Courier' size=8.5>required</font> para que el navegador no deje enviar "
    "vacío.", NOTA))
c.append(Paragraph(
    "<b>3.</b> El error se muestra solo si <font face='Courier' size=8.5>{% if error %}</font> "
    "tiene contenido. La respuesta, solo si <font face='Courier' size=8.5>{% if respuesta %}</font>. "
    "El filtro <font face='Courier' size=8.5>|linebreaks</font> convierte los saltos de línea "
    "del texto en <font face='Courier' size=8.5>&lt;p&gt;</font> o "
    "<font face='Courier' size=8.5>&lt;br&gt;</font>, porque la IA suele responder en "
    "párrafos y el HTML plano los ignoraría.", NOTA))
c.append(parrafo(
    "Ambos <font face='Courier' size=8.5>{% if %}</font> son posibles gracias a los "
    "acumuladores de la vista: <font face='Courier' size=8.5>error</font> y "
    "<font face='Courier' size=8.5>respuesta</font> siempre existen en el context, aunque "
    "estén vacíos."))

c.append(PageBreak())

# ------------------------------------------------------- 7. TESTS
c.append(Paragraph("7. Cómo se prueba", H1))
c.append(parrafo(
    "El asistente consulta una API externa, así que el test <b>no puede</b> llamar a Gemini "
    "de verdad (sería lento, costoso y no determinista). La técnica es el "
    "<font face='Courier' size=8.5>mock</font>: se reemplaza la función del servicio por un "
    "falso y se prueba cómo reacciona la vista. Hay tres tests en "
    "<font face='Courier' size=8.5>sitio/libros/tests.py</font>."))

c.append(Paragraph("7.1 Cuando la IA responde", H2))
c += codigo("""
def test_muestra_la_respuesta_que_devuelve_la_ia(self):
    with patch(
        "libros.servicios.preguntar_al_asistente",
        return_value="Hay 3 libros de Ficción.",
    ):
        respuesta = self.client.post(
            "/asistente/",
            {"pregunta": "¿Cuántos libros de ficción hay?"},
        )

    self.assertEqual(respuesta.status_code, 200)
    self.assertContains(respuesta, "Hay 3 libros de Ficción.")
""")
c.append(parrafo(
    "<font face='Courier' size=8.5>patch</font> reemplaza "
    "<font face='Courier' size=8.5>preguntar_al_asistente</font> con un falso que devuelve "
    "un texto fijo. La vista se comporta igual, pero no hay red. El test hace un POST real "
    "al cliente de pruebas de Django y verifica que el HTML contiene la respuesta."))

c.append(Paragraph("7.2 Cuando la IA falla", H2))
c += codigo("""
def test_si_la_ia_no_responde_la_pagina_igual_carga(self):
    fallo = servicios.IANoDisponible("timeout")

    with patch("libros.servicios.preguntar_al_asistente", side_effect=fallo):
        respuesta = self.client.post(
            "/asistente/",
            {"pregunta": "¿Qué libros hay?"},
        )

    self.assertEqual(respuesta.status_code, 200)
    self.assertContains(respuesta, "No se pudo consultar a la IA")
""")
c.append(parrafo(
    "Este test protege la degradación controlada: si la IA falla, la página sigue "
    "devolviendo 200 y muestra el aviso. Es la misma filosofía que el microservicio de "
    "reseñas: lo remoto falla y la página no debe romperse."))

c.append(Paragraph("7.3 El contexto del catálogo", H2))
c += codigo("""
def test_armar_contexto_biblioteca_incluye_los_datos_del_orm(self):
    categoria = Categoria.objects.create(nombre="Ficción")
    libro = Libro.objects.create(
        titulo="Ficciones", isbn="9788420633997", anio_publicacion=1944,
        paginas=176, categoria=categoria,
    )

    contexto = servicios.armar_contexto_biblioteca()

    self.assertIn("LIBROS:", contexto)
    self.assertIn("Ficciones", contexto)
    self.assertIn("categoria Ficción", contexto)
""")
c.append(parrafo(
    "Este test sí crea datos reales en la base de prueba y verifica que "
    "<font face='Courier' size=8.5>armar_contexto_biblioteca()</font> los vuelca al texto. "
    "Garantiza que la IA siempre reciba el catálogo real."))

c.append(PageBreak())

# ------------------------------------------------------- 8. FLUJO COMPLETO
c.append(Paragraph("8. El recorrido completo de una pregunta", H1))
c.append(parrafo(
    "Todo junto, esto es lo que pasa cuando alguien escribe una pregunta y la envía:"))

pasos = [
    ("1", "El usuario abre <font face='Courier' size=8.5>/asistente/</font>: GET, formulario vacío."),
    ("2", "Escribe una pregunta y pulsa «Preguntar»: el navegador manda un POST con el campo "
          "<font face='Courier' size=8.5>pregunta</font> y el token CSRF."),
    ("3", "Django valida el CSRF y enruta al view "
          "<font face='Courier' size=8.5>asistente(request)</font>."),
    ("4", "La vista lee y limpia la pregunta: <font face='Courier' size=8.5>request.POST.get(\"pregunta\").strip()</font>."),
    ("5", "Si quedó vacía, setea el error y salta al render."),
    ("6", "Si hay pregunta, llama a "
          "<font face='Courier' size=8.5>servicios.preguntar_al_asistente(pregunta)</font>."),
    ("7", "La función verifica la clave, arma el contexto del catálogo con "
          "<font face='Courier' size=8.5>armar_contexto_biblioteca()</font> (que consulta "
          "los 4 modelos), y compone el mensaje de sistema."),
    ("8", "Arma la URL de Gemini y el payload JSON, y llama a "
          "<font face='Courier' size=8.5>_pedir()</font> con 15 segundos de timeout."),
    ("9", "<font face='Courier' size=8.5>_pedir()</font> hace el POST por "
          "<font face='Courier' size=8.5>urllib</font> y parsea el JSON de la respuesta."),
    ("10", "Se extrae el texto del primer candidate y se devuelve como string."),
    ("11", "La vista guarda la respuesta en el acumulador y arma el "
           "<font face='Courier' size=8.5>context</font>."),
    ("12", "El template renderiza la respuesta con <font face='Courier' size=8.5>|linebreaks</font> "
           "y el usuario la lee en pantalla."),
]
c += tabla(["#", "Qué ocurre"], [[n, t] for n, t in pasos], [1.1 * cm, 15.3 * cm])

c.append(Paragraph("Qué pasa si algo falla", H2))
c += tabla(
    ["Falla", "Dónde se detecta", "Qué ve el usuario"],
    [["Falta la clave", "preguntar_al_asistente (línea 129)",
      "«No se pudo consultar a la IA (falta IA_API_KEY...)»"],
     ["La API no responde o tarda +15s", "_pedir (timeout)",
      "«No se pudo consultar a la IA (...timeout...)»"],
     ["La pregunta está vacía", "la vista (if not pregunta)",
      "«Escribí una pregunta primero»"],
     ["Respuesta con formato inesperado", "_pedir (ValueError)",
      "«No se pudo consultar a la IA (...bad JSON...)»"]],
    [5.0 * cm, 5.8 * cm, 5.6 * cm], mono_col=[1])

c.append(PageBreak())

# ------------------------------------------------------- 9. CIERRE
c.append(Paragraph("9. Lo que conviene llevarse", H1))
c += destacado(
    "1. La vista es un mediador delgado",
    "No conoce a Gemini, ni la clave, ni el formato del JSON. Recibe una pregunta, llama "
    "a una función del servicio y muestra el resultado. Toda la complejidad externa vive "
    "en servicios.py.")
c += destacado(
    "2. La IA se trata como un recurso falible",
    "Timeout, excepción propia y degradación controlada. Sin clave o sin API, la página "
    "carga igual con un aviso. Nunca un 500.")
c += destacado(
    "3. El contexto ancla a la realidad",
    "El texto que se le manda a la IA se arma con datos reales del ORM. El mensaje de "
    "sistema le prohíbe inventar. Eso convierte a un modelo generalista en un asistente "
    "del catálogo.")
c += destacado(
    "4. La configuración no viaja en el código",
    "Clave, URL, modelo y timeout se leen por variable de entorno con fallback a un "
    ".env no versionado y a valores de desarrollo. En Vercel se cargan desde el panel.")

c.append(Spacer(1, 0.7 * cm))
c.append(HRFlowable(width="100%", thickness=0.5, color=BORDE))
c.append(Spacer(1, 0.3 * cm))
c.append(Paragraph(
    "Archivos de referencia: <font face='Courier' size=8>sitio/libros/views.py</font>, "
    "<font face='Courier' size=8>sitio/libros/servicios.py</font>, "
    "<font face='Courier' size=8>sitio/biblioteca/settings.py</font>, "
    "<font face='Courier' size=8>sitio/libros/urls.py</font>, "
    "<font face='Courier' size=8>sitio/libros/templates/libros/asistente.html</font>, "
    "<font face='Courier' size=8>sitio/libros/tests.py</font>",
    estilo("Ref", fontSize=8.3, leading=12.5, textColor=GRIS)))

# ------------------------------------------------------- 10. GLOSARIO
c.append(PageBreak())
c.append(Paragraph("10. Glosario de términos", H1))
c.append(parrafo(
    "Los términos que aparecen en este documento, explicados en el contexto del asistente."))

c += glosario("La vista y el flujo", [
    ("Vista",
     "Función de Python que recibe una petición HTTP y devuelve una respuesta. "
     "<font face='Courier' size=8>asistente()</font> sigue el patrón de tres pasos del "
     "proyecto: consumir datos, armar el context, renderizar."),
    ("GET / POST",
     "Los dos métodos HTTP. GET pide una página sin efectos; POST envía datos para "
     "procesarlos. La misma URL /asistente/ responde a ambos, y la vista distingue por "
     "request.method."),
    ("Context",
     "Diccionario que la vista le pasa al template. Acá lleva exactamente dos claves: "
     "respuesta y error."),
    ("Template",
     "HTML con plantillas de Django. Solo muestra las variables del context; no consulta "
     "la base ni llama a servicios."),
    ("CSRF token",
     "Token de seguridad que Django exige en los POST de formularios propios para impedir "
     "que un sitio externo envíe peticiones en nombre del usuario. Sin él, el POST "
     "devuelve 403."),
    ("Acumulador",
     "Variable que arranca con un valor vacío y se va llenando según el flujo. respuesta y "
     "error se pasan al template aunque no se hayan tocado."),
])

c += glosario("El servicio y la IA", [
    ("API",
     "Interfaz que un programa externo expone para ser usado. El asistente consume la API "
     "de Gemini por HTTP."),
    ("Gemini",
     "Modelo de IA de Google que responde texto. El código no lo menciona: solo conoce la "
     "URL y el modelo de settings."),
    ("generateContent",
     "La acción concreta de la API de Gemini que genera texto. La URL termina en "
     "<font face='Courier' size=8>:generateContent</font>."),
    ("Prompt",
     "El texto que se le envía a la IA. Acá son dos parts: el mensaje de sistema y el "
     "contexto con la pregunta."),
    ("Mensaje de sistema",
     "Instrucción de rol que define cómo debe comportarse la IA: quién es, qué responder, "
     "qué evitar. Es la guía contra las alucinaciones."),
    ("Alucinación",
     "Cuando una IA inventa datos que no existen. Se combate dándole un contexto real y "
     "prohibiéndole responder fuera de él."),
    ("Temperature",
     "Parámetro de generación: cuánta aleatoriedad se permite. 0.2 es bajo: respuestas "
     "predecibles y apegadas al contexto."),
    ("Timeout",
     "Tiempo máximo de espera de una respuesta. La IA usa 15 segundos, más que el "
     "microservicio, porque generar texto es lento."),
    ("JSON",
     "Formato de datos con llaves y listas. Es lo que el asistente envía a Gemini y lo que "
     "recibe de vuelta."),
])

c += glosario("Python y Django", [
    ("urllib",
     "Librería estándar de Python para pedidos HTTP. Se usa en vez de requests para no "
     "sumar dependencias al proyecto."),
    ("Excepción propia",
     "Clase de error definida por el proyecto, como IANoDisponible. Traduce fallas "
     "técnicas a un vocabulario de negocio."),
    ("Mock",
     "Falso que reemplaza a una función real en un test. Permite probar la vista sin "
     "llamar a Gemini."),
    ("patch",
     "Contexto de unittest.mock que reemplaza un objeto durante la ejecución y lo "
     "restaura al salir."),
    ("ORM",
     "Traductor entre clases de Python y tablas SQL. armar_contexto_biblioteca() usa "
     "Libro.objects.all() para leer el catálogo real."),
    ("render()",
     "Shortcut de Django que combina un template con un context y devuelve una respuesta "
     "HTML."),
    ("Variable de entorno",
     "Valor externo al código (como IA_API_KEY). Permite cambiar la configuración sin "
     "tocar ni desplegar código."),
    (".env",
     "Archivo local con variables de entorno, excluido del repo. settings.py lo lee solo "
     "con _leer_env_local()."),
])

SALIDA.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(
    str(SALIDA), pagesize=A4,
    leftMargin=2.2 * cm, rightMargin=2.2 * cm,
    topMargin=2.0 * cm, bottomMargin=2.2 * cm,
    title="El Asistente con IA — Biblioteca Comunitaria",
    author="Proyecto Biblioteca Comunitaria",
    subject="La vista asistente() explicada línea por línea",
)
doc.build(c, onFirstPage=pie, onLaterPages=pie)
print(f"PDF generado: {SALIDA}")