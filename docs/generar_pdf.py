"""Genera el PDF explicativo del microservicio de reseñas."""
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

RAIZ = Path("/Users/daniel.rairan/proyecto_django_biblioteca")
SALIDA = RAIZ / "docs" / "microservicio-resenas.pdf"

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
    """Escapa preservando TODOS los espacios.

    Paragraph colapsa cualquier secuencia de espacios, no solo los del margen.
    En codigo la indentacion es sintaxis y en los diagramas define los bordes,
    asi que cada espacio se convierte en uno duro.
    """
    return esc(t).replace(" ", "&nbsp;")


def parrafo(t):
    return Paragraph(t, CUERPO)


def codigo(texto, titulo=None):
    """Bloque de código con fondo gris."""
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
    """Bloque de glosario: termino a la izquierda, definicion a la derecha."""
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
    # Un grupo corto entra entero en una pagina: se mantiene junto para que el
    # titulo no quede huerfano al pie con una sola fila debajo.
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
                      "Biblioteca Comunitaria — Microservicio de Reseñas")
    canvas.drawRightString(A4[0] - 2.2 * cm, 1.15 * cm, f"Página {doc.page}")
    canvas.restoreState()


c = []

# ---------------------------------------------------------------- PORTADA
c.append(Spacer(1, 3.4 * cm))
c.append(Paragraph("Microservicio de Reseñas",
                   estilo("Tit", fontName="Helvetica-Bold", fontSize=27, leading=32,
                          textColor=AZUL, alignment=TA_CENTER)))
c.append(Spacer(1, 0.5 * cm))
c.append(Paragraph("Cómo funciona y cómo lo consume el sitio Django",
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
    ["Componente", "Tecnología", "Dónde vive"],
    [["Sitio web", "Django 6.1.1", "<font face='Courier' size=8>sitio/</font>"],
     ["Microservicio", "FastAPI 0.141.1", "<font face='Courier' size=8>microservicio_resenas/</font>"],
     ["Base del sitio", "PostgreSQL (Supabase)", "La nube"],
     ["Base de reseñas", "PostgreSQL (Supabase)", "La nube"],
     ["Despliegue", "Vercel Services", "Un dominio, un deploy"]],
    [4.4 * cm, 5.4 * cm, 6.6 * cm])

c.append(PageBreak())

# ------------------------------------------------------- 1. QUÉ Y POR QUÉ
c.append(Paragraph("1. Qué es este microservicio y por qué existe", H1))
c.append(parrafo(
    "Un <b>microservicio</b> es una aplicación pequeña e independiente que resuelve "
    "una sola responsabilidad y que se comunica con el resto del sistema por la red, "
    "normalmente por HTTP. No comparte código ni base de datos con quien lo consume: "
    "solo expone un contrato público, que son sus URLs y el formato de sus respuestas."))
c.append(parrafo(
    "En este proyecto el microservicio tiene una única responsabilidad: <b>guardar y "
    "devolver las reseñas de los libros</b>. Nada más. No sabe qué es un préstamo, "
    "no sabe qué es un lector, ni siquiera sabe qué es un libro: para él un libro es "
    "apenas un número, el <font face='Courier' size=8.5>libro_id</font>."))

c.append(Paragraph("El requisito que cumple", H2))
c.append(parrafo(
    "La consigna pedía que una vista consumiera un microservicio propio, desplegado "
    "en la nube, y que ese microservicio accediera a una base de datos distinta de "
    "SQLite. Las reseñas son justamente el dato que <b>no</b> vive en la base local: "
    "viven en Supabase y solo se alcanzan a través de la API."))

c += destacado(
    "La idea central",
    "Las reseñas NO son un modelo de Django. No existe una clase "
    "<font face='Courier' size=8.5>Resena(models.Model)</font> en ninguna parte del "
    "proyecto, y eso es deliberado. Si existiera, Django estaría leyendo directamente "
    "la base del microservicio y ya no habría dos servicios: habría uno solo con dos "
    "conexiones.")

c.append(Paragraph("Por qué no hay un modelo de Django para las reseñas", H2))
c.append(parrafo(
    "Es la pregunta más común y vale la pena responderla con precisión. El modelo de "
    "las reseñas <b>sí existe</b>, pero está definido dentro del microservicio, en dos lugares:"))
c += tabla(
    ["Qué define", "Dónde está", "Qué establece"],
    [["La tabla", "microservicio_resenas/schema.sql",
      "Las columnas y sus tipos en PostgreSQL"],
     ["El contrato de entrada", "ResenaNueva, en main.py",
      "Qué acepta el POST y con qué validaciones"]],
    [3.6 * cm, 5.8 * cm, 7.0 * cm], mono_col=[1])
c.append(parrafo(
    "Si Django tuviera su propio modelo apuntando a esa misma tabla, habría "
    "<b>dos definiciones del mismo esquema en dos lugares distintos</b>. El día que "
    "el microservicio agregue una columna, las migraciones de Django no se enterarían "
    "y algo se rompería sin aviso. Por eso la regla es dura:"))
c += destacado(
    "Regla de aislamiento",
    "La base de datos de un servicio es privada. Solo se toca a través de su API. "
    "Django ni siquiera tiene las credenciales de esa base: lo único que conoce es una URL.")

c.append(PageBreak())

# ------------------------------------------------------- 2. ARQUITECTURA
c.append(Paragraph("2. La arquitectura completa", H1))
c.append(parrafo(
    "Este es el recorrido de una petición desde que alguien abre el navegador hasta "
    "que ve las reseñas en pantalla:"))
c += diagrama("""
  NAVEGADOR
      |
      |  GET /libro/1/resenas/
      v
  +--------------------------------------------------+
  |  SERVICIO 1 - Sitio Django   (carpeta sitio/)    |
  |                                                  |
  |  vista resenas_libro()                           |
  |    |                                             |
  |    +-- Libro ------> ORM ------> PostgreSQL      |
  |    |                                             |
  |    +-- resenas ---> servicios.py                 |
  |                         |                        |
  +-------------------------|------------------------+
                            |  HTTP GET
                            |  /api/libros/1/resenas
                            v
  +--------------------------------------------------+
  |  SERVICIO 2 - API FastAPI                        |
  |  (carpeta microservicio_resenas/)                |
  |                                                  |
  |  resenas_de_libro()                              |
  |    |                                             |
  |    +-- cliente supabase ---> tabla resenas       |
  |                              PostgreSQL / nube   |
  +--------------------------------------------------+
""")
c.append(parrafo(
    "Los dos servicios comparten dominio y se despliegan juntos, pero <b>se construyen "
    "por separado</b>, cada uno con sus propias dependencias. Compartir dominio no los "
    "convierte en una sola aplicación: el dominio es la puerta de entrada, no el programa."))

c += tabla(
    ["Dato", "Dónde vive", "Cómo lo obtiene Django"],
    [["Libros, autores, categorías", "PostgreSQL del sitio", "ORM de Django"],
     ["Lectores y préstamos", "PostgreSQL del sitio", "ORM de Django"],
     ["Reseñas y puntajes", "Tabla <font face='Courier' size=8>resenas</font> (Supabase)",
      "HTTP contra el microservicio"]],
    [5.2 * cm, 5.6 * cm, 5.6 * cm])

c.append(Paragraph("Cómo se reparte el tráfico", H2))
c.append(parrafo(
    "El archivo <font face='Courier' size=8.5>vercel.json</font> declara los dos "
    "servicios y decide qué URL atiende cada uno:"))
c += codigo("""
{
  "services": {
    "sitio": { "root": "sitio/",  "entrypoint": "biblioteca.wsgi:application" },
    "api":   { "root": "microservicio_resenas/", "entrypoint": "main:app" }
  },
  "rewrites": [
    { "source": "/api/(.*)", "destination": { "service": "api"   } },
    { "source": "/(.*)",     "destination": { "service": "sitio" } }
  ]
}
""", "vercel.json")
c += tabla(
    ["URL", "La atiende", "Devuelve"],
    [["/", "sitio", "El catálogo, en HTML"],
     ["/libro/1/resenas/", "sitio", "HTML con las reseñas pedidas a la API"],
     ["/api/libros/1/resenas", "api", "JSON crudo desde Supabase"],
     ["/api/salud", "api", "<font face='Courier' size=8>{\"estado\": \"ok\"}</font>"]],
    [5.6 * cm, 2.6 * cm, 8.2 * cm], mono_col=[0])

c.append(PageBreak())

# ------------------------------------------------------- 3. EL MICROSERVICIO
c.append(Paragraph("3. El microservicio, parte por parte", H1))
c.append(parrafo(
    "Todo el microservicio es un único archivo: "
    "<font face='Courier' size=8.5>microservicio_resenas/main.py</font>. "
    "Vamos por bloques."))

c.append(Paragraph("3.1 Las credenciales", H2))
c += codigo("""
def variable_obligatoria(nombre):
    \"\"\"Lee una variable de entorno obligatoria y falla con un mensaje legible.\"\"\"
    valor = os.environ.get(nombre)
    if not valor:
        raise RuntimeError(f"Falta la variable de entorno {nombre}. ...")
    return valor

SUPABASE_URL = variable_obligatoria("SUPABASE_URL")
SUPABASE_SERVICE_KEY = variable_obligatoria("SUPABASE_SERVICE_KEY")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
""")
c.append(parrafo(
    "Las claves <b>nunca se escriben en el código</b>: llegan por variables de entorno, "
    "que en el servidor se cargan desde el panel de la plataforma y en local desde el "
    "archivo <font face='Courier' size=8.5>.env</font>, que no se versiona."))
c.append(parrafo(
    "Esto ocurre al <b>importar</b> el módulo, no dentro de una función. Si falta una "
    "credencial, el servicio no arranca. Es intencional: es preferible que falle al "
    "iniciar, de forma ruidosa, antes que arranque a medias y falle en el primer "
    "pedido de un usuario."))
c += destacado(
    "Cómo se ve ese fallo en producción",
    "Si el módulo explota al importarse, <b>todas</b> las rutas devuelven error, "
    "incluso una tan simple como <font face='Courier' size=8.5>/api/salud</font>, que "
    "no toca ni la base ni la red. Ese síntoma —error en absolutamente todo— es la "
    "pista de que el problema no está en ninguna ruta, sino en el arranque del módulo.")

c.append(Paragraph("3.2 El prefijo /api", H2))
c += codigo("""
app = FastAPI(title="Microservicio de Reseñas", version="1.0.0")

api = APIRouter(prefix="/api")
...
app.include_router(api)
""")
c.append(parrafo(
    "Todas las rutas cuelgan de <font face='Courier' size=8.5>/api</font> porque el "
    "servicio comparte dominio con el sitio. Cuando Vercel enruta una petición a un "
    "servicio, <b>le entrega la ruta completa</b>: un pedido a "
    "<font face='Courier' size=8.5>/api/salud</font> le llega a FastAPI como "
    "<font face='Courier' size=8.5>/api/salud</font>, no como "
    "<font face='Courier' size=8.5>/salud</font>. Si el prefijo no estuviera declarado "
    "acá, todas las rutas darían 404."))

c.append(Paragraph("3.3 El contrato de entrada", H2))
c += codigo("""
class ResenaNueva(BaseModel):
    \"\"\"Datos que el cliente envía para crear una reseña.\"\"\"

    libro_id: int = Field(..., ge=1)
    lector: str = Field(..., min_length=1, max_length=100)
    puntaje: int = Field(..., ge=1, le=5)
    comentario: str = Field("", max_length=1000)
""")
c.append(parrafo(
    "Esto es un modelo de <b>Pydantic</b>, y cumple el papel que en Django cumpliría "
    "un formulario. FastAPI lo usa para validar automáticamente: si alguien manda un "
    "puntaje de 9, la petición se rechaza con un error 422 y el código del endpoint "
    "<b>nunca llega a ejecutarse</b>. No hay que escribir un solo <font face='Courier' "
    "size=8.5>if</font> de validación."))

c.append(PageBreak())

c.append(Paragraph("3.4 El endpoint que consume Django", H2))
c.append(parrafo("De los cuatro endpoints, este es el que usa la vista:"))
c += codigo("""
@api.get("/libros/{libro_id}/resenas")
def resenas_de_libro(libro_id: int):
    \"\"\"Devuelve las reseñas de un libro con su promedio de puntaje.\"\"\"
    try:
        respuesta = (
            supabase.table(TABLA)
            .select("*")
            .eq("libro_id", libro_id)
            .order("creada_en", desc=True)
            .execute()
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Error de Supabase: {error}")

    resenas = respuesta.data
    promedio = None
    if resenas:
        promedio = round(sum(r["puntaje"] for r in resenas) / len(resenas), 2)

    return {
        "libro_id": libro_id,
        "cantidad": len(resenas),
        "promedio": promedio,
        "resenas": resenas,
    }
""", "microservicio_resenas/main.py")
c.append(parrafo("Tres cosas para notar:"))
c.append(Paragraph(
    "<b>1.</b> El <font face='Courier' size=8.5>libro_id: int</font> de la firma no es "
    "decorativo: FastAPI convierte el texto de la URL a entero y, si no puede, responde "
    "422 solo.", NOTA))
c.append(Paragraph(
    "<b>2.</b> El <b>promedio se calcula acá</b>, no en Django ni en el template. El "
    "servicio devuelve el dato ya listo para mostrar.", NOTA))
c.append(Paragraph(
    "<b>3.</b> Un libro sin reseñas <b>no es un error</b>: devuelve "
    "<font face='Courier' size=8.5>cantidad: 0</font> y "
    "<font face='Courier' size=8.5>promedio: null</font>, con un 200. Una lista vacía "
    "es un resultado válido.", NOTA))

c.append(Paragraph("Los cuatro endpoints", H3))
c += tabla(
    ["Método y ruta", "Qué hace"],
    [["GET /api/", "Se describe a sí mismo y lista sus endpoints"],
     ["GET /api/salud", "Health check: responde si el servicio está vivo"],
     ["GET /api/resenas", "Todas las reseñas, de la más nueva a la más vieja"],
     ["GET /api/libros/{id}/resenas", "Reseñas de un libro y su promedio"],
     ["POST /api/resenas", "Crea una reseña nueva"]],
    [6.4 * cm, 10.0 * cm], mono_col=[0])
c.append(parrafo(
    "FastAPI genera además una documentación interactiva sola, en "
    "<font face='Courier' size=8.5>/api/docs</font>, donde se pueden probar los "
    "endpoints desde el navegador."))

c.append(Paragraph("3.5 La tabla en Supabase", H2))
c += codigo("""
create table if not exists public.resenas (
    id          bigint generated always as identity primary key,
    libro_id    integer     not null,
    lector      text        not null,
    puntaje     integer     not null check (puntaje between 1 and 5),
    comentario  text        not null default '',
    creada_en   timestamptz not null default now()
);

create index if not exists resenas_libro_id_idx on public.resenas (libro_id);

alter table public.resenas enable row level security;
""", "microservicio_resenas/schema.sql")
c.append(parrafo(
    "El <font face='Courier' size=8.5>check (puntaje between 1 and 5)</font> repite a "
    "propósito la validación que ya hace Pydantic. Son dos defensas en capas distintas: "
    "Pydantic protege de un cliente mal programado, el <font face='Courier' size=8.5>check"
    "</font> protege de cualquiera que escriba en la tabla sin pasar por la API."))
c += destacado(
    "Seguridad de la tabla",
    "Row Level Security queda activado y <b>sin políticas públicas</b>: con la clave "
    "anónima nadie puede leer ni escribir. Solo el microservicio atraviesa esa barrera, "
    "porque usa la clave <font face='Courier' size=8.5>service_role</font>, que vive "
    "como variable de entorno del servidor y nunca sale de ahí.")

c.append(PageBreak())

# ------------------------------------------------------- 4. LADO DJANGO
c.append(Paragraph("4. El lado de Django: cómo lo consume", H1))
c.append(parrafo(
    "Del lado del sitio hay tres capas bien separadas, y cada una sabe una cosa distinta:"))
c += tabla(
    ["Capa", "Archivo", "Qué sabe"],
    [["Cliente HTTP", "libros/servicios.py",
      "Que las reseñas son remotas y cómo pedirlas"],
     ["Vista", "libros/views.py",
      "Que hay que combinar datos locales y remotos"],
     ["Template", "libros/templates/libros/resenas.html",
      "Nada del origen: solo muestra el context"]],
    [3.4 * cm, 5.4 * cm, 7.6 * cm], mono_col=[1])

c.append(Paragraph("4.1 El cliente HTTP", H2))
c.append(parrafo(
    "<font face='Courier' size=8.5>servicios.py</font> es el <b>único módulo de todo "
    "el proyecto que sabe que las reseñas viven fuera</b>. Si mañana el microservicio "
    "cambiara de dirección o de formato, este es el único archivo a tocar."))
c += codigo("""
class MicroservicioNoDisponible(Exception):
    \"\"\"El microservicio no respondió, tardó demasiado o devolvió algo inesperado.\"\"\"


def _pedir(url, datos=None):
    \"\"\"Hace la petición HTTP y devuelve el JSON ya parseado.\"\"\"
    cuerpo = None
    cabeceras = {"Accept": "application/json"}

    if datos is not None:
        cuerpo = json.dumps(datos).encode("utf-8")
        cabeceras["Content-Type"] = "application/json"

    peticion = urllib.request.Request(url, data=cuerpo, headers=cabeceras)

    try:
        with urllib.request.urlopen(
            peticion, timeout=settings.MICROSERVICIO_RESENAS_TIMEOUT
        ) as respuesta:
            return json.loads(respuesta.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError) as error:
        raise MicroservicioNoDisponible(str(error)) from error


def obtener_resenas(libro_id):
    url = f"{settings.MICROSERVICIO_RESENAS_URL}/libros/{libro_id}/resenas"
    return _pedir(url)
""", "sitio/libros/servicios.py")
c.append(parrafo(
    "Usa <font face='Courier' size=8.5>urllib</font>, de la biblioteca estándar, en "
    "lugar de <font face='Courier' size=8.5>requests</font>: así el sitio no suma una "
    "dependencia solo para hacer un pedido HTTP."))
c.append(parrafo(
    "Lo importante es la <b>traducción de errores</b>. Una caída de red, un timeout y "
    "una respuesta que no es JSON son tres fallas técnicas muy distintas, pero para la "
    "vista significan exactamente lo mismo: <i>no tengo las reseñas</i>. Por eso las "
    "tres se convierten en una sola excepción propia. La vista no necesita saber nada "
    "de <font face='Courier' size=8.5>urllib</font>."))

c.append(PageBreak())

c.append(Paragraph("4.2 La vista", H2))
c.append(parrafo(
    "Sigue el mismo patrón de tres pasos que todas las vistas del proyecto. La "
    "diferencia es que consume <b>dos fuentes</b>: el ORM para el libro y el "
    "microservicio para las reseñas."))
c += codigo("""
def resenas_libro(request, libro_id):
    \"\"\"Combina un Libro del ORM con sus reseñas traídas del microservicio.\"\"\"
    # 1. consumir el modelo y, por HTTP, el microservicio
    libro = get_object_or_404(Libro, pk=libro_id)
    mensaje = ""

    if request.method == "POST":
        ...
        servicios.crear_resena(libro_id=libro.id, lector=lector, ...)

    try:
        datos = servicios.obtener_resenas(libro.id)
        error = ""
    except servicios.MicroservicioNoDisponible as fallo:
        datos = {}
        error = f"El microservicio de reseñas no está disponible ({fallo})"

    # 2. armar el context como variable con nombre
    context = {
        "libro": libro,
        "resenas": datos.get("resenas", []),
        "cantidad": datos.get("cantidad", 0),
        "promedio": datos.get("promedio"),
        "url_microservicio": settings.MICROSERVICIO_RESENAS_URL,
        "mensaje": mensaje,
        "error": error,
    }

    # 3. enviarlo al template
    return render(request, "libros/resenas.html", context)
""", "sitio/libros/views.py")

c.append(Paragraph("Por qué el try/except no es opcional", H3))
c.append(parrafo(
    "Una consulta al ORM local falla, casi siempre, solo si hay un error de programación. "
    "Una llamada HTTP a otra máquina falla por motivos que <b>no se controlan</b>: se "
    "cayó la red, la plataforma reinició el servicio, la base está lenta, alguien cambió "
    "la URL."))
c += destacado(
    "Degradación controlada",
    "Toda llamada remota se asume falible. Si el microservicio no responde, la página "
    "se sigue mostrando con un aviso y los datos del libro intactos; no devuelve un "
    "error 500. Esa es la diferencia práctica entre leer de una base local y leer de "
    "un servicio externo, y es el motivo de que el proyecto tenga un test dedicado a "
    "verificar justamente este caso.")
c.append(parrafo(
    "Por lo mismo existe un <b>timeout</b> de 5 segundos. Sin él, la vista quedaría "
    "colgada esperando a un servidor que quizá no conteste nunca, y con ella el "
    "proceso que atiende a ese usuario."))

c.append(Paragraph("4.3 El template", H2))
c.append(parrafo(
    "El template no sabe —ni tiene por qué saber— de dónde salieron los datos. Recibe "
    "una lista en el context y la recorre, igual que cualquier otra vista del proyecto. "
    "Esa ignorancia es justamente la señal de que la separación está bien hecha."))
c += codigo("""
{% if resenas %}
    <table border="1">
        <tr><th>Lector</th><th>Puntaje</th><th>Comentario</th><th>Fecha</th></tr>
        {% for resena in resenas %}
            <tr>
                <td>{{ resena.lector }}</td>
                <td>{{ resena.puntaje }}</td>
                <td>{{ resena.comentario }}</td>
                <td>{{ resena.creada_en }}</td>
            </tr>
        {% endfor %}
    </table>
{% else %}
    <p>Este libro todavía no tiene reseñas.</p>
{% endif %}
""", "sitio/libros/templates/libros/resenas.html")
c.append(parrafo(
    "Un detalle: <font face='Courier' size=8.5>resena.lector</font> no es un atributo "
    "de un objeto de Python, es una clave de un diccionario que vino de un JSON. La "
    "sintaxis del template es idéntica en los dos casos, y por eso el cambio de origen "
    "resulta invisible desde acá."))

c.append(PageBreak())

# ------------------------------------------------------- 5. EL FLUJO
c.append(Paragraph("5. El recorrido completo de una petición", H1))
c.append(parrafo(
    "Poniendo todo junto, esto es lo que pasa cuando alguien abre "
    "<font face='Courier' size=8.5>/libro/1/resenas/</font>:"))

pasos = [
    ("1", "El navegador pide <font face='Courier' size=8.5>/libro/1/resenas/</font>."),
    ("2", "Vercel mira sus reglas: la ruta no empieza con <font face='Courier' size=8.5>/api</font>, "
          "así que va al servicio <b>sitio</b>."),
    ("3", "Django resuelve la URL y llama a <font face='Courier' size=8.5>resenas_libro(request, 1)</font>."),
    ("4", "La vista busca el libro con el ORM: <font face='Courier' size=8.5>get_object_or_404(Libro, pk=1)</font>. "
          "Si no existe, 404 y se terminó."),
    ("5", "La vista llama a <font face='Courier' size=8.5>servicios.obtener_resenas(1)</font>."),
    ("6", "El cliente arma la URL y hace <font face='Courier' size=8.5>GET .../api/libros/1/resenas</font>, "
          "con 5 segundos de plazo."),
    ("7", "Vercel ve el prefijo <font face='Courier' size=8.5>/api</font> y manda la petición al servicio <b>api</b>."),
    ("8", "FastAPI convierte el <font face='Courier' size=8.5>1</font> de la URL a entero y ejecuta "
          "<font face='Courier' size=8.5>resenas_de_libro(1)</font>."),
    ("9", "El endpoint consulta Supabase, calcula el promedio y devuelve el JSON."),
    ("10", "El cliente parsea ese JSON y devuelve un diccionario. Si algo falló, lanza "
           "<font face='Courier' size=8.5>MicroservicioNoDisponible</font>."),
    ("11", "La vista arma el <font face='Courier' size=8.5>context</font> con el libro y las reseñas."),
    ("12", "El template lo renderiza y el navegador recibe el HTML."),
]
filas = [[n, t] for n, t in pasos]
c += tabla(["#", "Qué ocurre"], filas, [1.1 * cm, 15.3 * cm])

c.append(Paragraph("Qué pasa si el microservicio está caído", H2))
c.append(parrafo(
    "El paso 6 falla, el 10 lanza la excepción, y la vista la atrapa. El "
    "<font face='Courier' size=8.5>context</font> se arma igual, con una lista vacía "
    "de reseñas y un mensaje de error. <b>El usuario ve la página, con los datos del "
    "libro y un aviso donde irían las reseñas.</b> No ve una pantalla de error."))

c.append(Paragraph("Cómo sabe Django a qué dirección llamar", H2))
c += codigo("""
def _url_del_microservicio():
    explicita = os.environ.get('MICROSERVICIO_RESENAS_URL')
    if explicita:
        return explicita
    dominio = (
        os.environ.get('VERCEL_PROJECT_PRODUCTION_URL')
        or os.environ.get('VERCEL_URL')
    )
    if dominio:
        return f'https://{dominio}/api'
    return 'http://127.0.0.1:8001/api'


MICROSERVICIO_RESENAS_URL = _url_del_microservicio().rstrip('/')
MICROSERVICIO_RESENAS_TIMEOUT = 5  # segundos
""", "sitio/biblioteca/settings.py")
c.append(parrafo(
    "En desarrollo apunta al puerto 8001 de la propia máquina. En el servidor deduce "
    "el dominio público del proyecto y le agrega <font face='Courier' size=8.5>/api</font>, "
    "así que no hay nada que configurar a mano. Y siempre se puede forzar otra dirección "
    "con una variable de entorno, sin tocar una línea de código."))

c.append(PageBreak())

# ------------------------------------------------------- 6. CIERRE
c.append(Paragraph("6. Probarlo y entenderlo", H1))

c.append(Paragraph("Ver los dos lados de la misma información", H2))
c.append(parrafo(
    "La forma más clara de comprobar que son dos sistemas distintos es pedir el mismo "
    "dato por las dos vías:"))
c += tabla(
    ["Abrí esta URL", "Y vas a ver"],
    [["/libro/1/resenas/", "La página del sitio, con las reseñas en una tabla HTML"],
     ["/api/libros/1/resenas", "El JSON crudo que la vista consumió para armarla"],
     ["/api/docs", "La documentación interactiva que FastAPI genera sola"]],
    [6.0 * cm, 10.4 * cm], mono_col=[0])
c.append(parrafo(
    "Son los mismos datos, servidos por dos programas distintos, en dos formatos "
    "distintos, desde el mismo dominio."))

c.append(Paragraph("Levantarlo en local", H2))
c += codigo("""
# Terminal 1 — el microservicio
cd microservicio_resenas
set -a; . ../.env; set +a
venv/bin/uvicorn main:app --reload --port 8001

# Terminal 2 — el sitio
cd sitio
venv/bin/python manage.py runserver
""")
c.append(parrafo(
    "Hacen falta <b>dos terminales</b>, y eso también enseña algo: son dos procesos "
    "independientes. Se puede apagar el microservicio con el sitio andando y ver la "
    "degradación controlada en vivo."))

c.append(Paragraph("Lo que conviene llevarse", H2))
c += destacado(
    "1. El dato define el límite",
    "Las reseñas viven fuera de la base del sitio. Esa decisión es la que crea el "
    "microservicio: todo lo demás —la API, el cliente HTTP, el manejo de errores— "
    "es consecuencia de ella.")
c += destacado(
    "2. Lo remoto falla, y hay que preverlo",
    "Timeout y <font face='Courier' size=8.5>try/except</font> en toda llamada de red. "
    "Un servicio caído degrada la página; no la rompe.")
c += destacado(
    "3. Un solo lugar sabe del exterior",
    "<font face='Courier' size=8.5>servicios.py</font> concentra todo lo que sabe que "
    "las reseñas son remotas. La vista y el template quedan igual de simples que "
    "cualquier otro del proyecto.")
c += destacado(
    "4. Las credenciales no viajan",
    "Django no tiene las claves de la base de las reseñas. Solo conoce una URL. Ese "
    "aislamiento es el beneficio concreto que se compra al separar los servicios.")

c.append(Spacer(1, 0.7 * cm))
c.append(HRFlowable(width="100%", thickness=0.5, color=BORDE))
c.append(Spacer(1, 0.3 * cm))
c.append(Paragraph(
    "Archivos de referencia: <font face='Courier' size=8>microservicio_resenas/main.py</font>, "
    "<font face='Courier' size=8>microservicio_resenas/schema.sql</font>, "
    "<font face='Courier' size=8>sitio/libros/servicios.py</font>, "
    "<font face='Courier' size=8>sitio/libros/views.py</font>, "
    "<font face='Courier' size=8>vercel.json</font>",
    estilo("Ref", fontSize=8.3, leading=12.5, textColor=GRIS)))


# ------------------------------------------------------- 7. GLOSARIO
c.append(PageBreak())
c.append(Paragraph("7. Glosario de términos", H1))
c.append(parrafo(
    "Los términos que aparecen en este documento, agrupados por tema. Los ejemplos "
    "salen del propio proyecto."))

c += glosario("Arquitectura", [
    ("Microservicio",
     "Aplicación pequeña e independiente que resuelve una sola responsabilidad y se "
     "comunica con el resto por la red. No comparte código ni base de datos con quien "
     "la consume. Acá: la API de reseñas."),
    ("Monolito",
     "Lo opuesto: una única aplicación que hace todo y comparte una sola base de datos. "
     "El sitio Django, por sí solo, es un monolito, y para este tamaño está bien."),
    ("Acoplamiento",
     "Cuánto depende una parte del sistema de los detalles internos de otra. Que Django "
     "conozca solo una URL, y no el esquema de la base de reseñas, es bajo acoplamiento."),
    ("Contrato",
     "Lo que un servicio promete públicamente: sus URLs y el formato de sus respuestas. "
     "Mientras el contrato no cambie, el microservicio puede reescribirse por dentro sin "
     "que Django se entere."),
    ("Degradación controlada",
     "Que el sistema siga funcionando, con menos información, cuando una parte falla. "
     "Si la API se cae, la página del libro se muestra igual con un aviso en lugar de "
     "las reseñas."),
    ("Shared database antipattern",
     "El error de que dos servicios escriban la misma tabla con definiciones propias del "
     "esquema. Tarde o temprano se desincronizan. Es la razón de que no exista un modelo "
     "<font face='Courier' size=8>Resena</font> en Django."),
])

c += glosario("Web y HTTP", [
    ("HTTP",
     "El protocolo con el que se piden y devuelven cosas en la web. Es el canal por el "
     "que la vista de Django habla con el microservicio."),
    ("GET / POST",
     "Los dos métodos HTTP que usa el proyecto. <b>GET</b> pide datos sin modificar nada; "
     "<b>POST</b> envía datos para crear algo."),
    ("JSON",
     "Formato de texto para intercambiar datos, con llaves y listas. Es lo que devuelve "
     "el microservicio y lo que la vista convierte en un diccionario de Python."),
    ("API",
     "Interfaz de programación: el conjunto de URLs que un servicio expone para que otros "
     "programas lo usen. Devuelve datos, no páginas."),
    ("Endpoint",
     "Una URL concreta de una API, con su método. Por ejemplo "
     "<font face='Courier' size=8>GET /api/libros/1/resenas</font>."),
    ("Timeout",
     "El tiempo máximo que se espera una respuesta antes de darla por perdida. Acá son "
     "5 segundos. Sin timeout, una vista puede quedar colgada para siempre."),
    ("Health check",
     "Endpoint trivial que solo responde si el servicio está vivo. Acá es "
     "<font face='Courier' size=8>/api/salud</font>. Lo usan las plataformas para "
     "monitorear."),
])

c += glosario("Códigos de estado que usa el proyecto", [
    ("200 OK", "Todo bien. Un libro sin reseñas también devuelve 200: una lista vacía "
               "es un resultado válido, no un error."),
    ("201 Created", "Se creó algo. Lo devuelve <font face='Courier' size=8>POST /api/resenas</font>."),
    ("404 Not Found", "No existe lo pedido. Lo produce "
                      "<font face='Courier' size=8>get_object_or_404</font> cuando el libro no está."),
    ("422 Unprocessable", "Los datos enviados no pasaron la validación. FastAPI lo devuelve "
                          "solo, por ejemplo con un puntaje de 9."),
    ("500 Internal Error", "El servidor se rompió. Es lo que el <font face='Courier' size=8>"
                           "try/except</font> de la vista evita cuando la API no responde."),
    ("502 Bad Gateway", "Un servicio intermedio falló. El microservicio lo devuelve si "
                        "Supabase no contesta."),
])

c += glosario("Django", [
    ("Vista",
     "Función que recibe una petición, consigue los datos y devuelve una respuesta. "
     "En este proyecto siempre sigue tres pasos: consumir datos, armar el "
     "<font face='Courier' size=8>context</font>, renderizar el template."),
    ("Template",
     "Plantilla HTML con huecos que se rellenan con los datos del "
     "<font face='Courier' size=8>context</font>. No consulta la base de datos."),
    ("Context",
     "Diccionario que la vista le pasa al template. Es la frontera entre la lógica y la "
     "presentación."),
    ("ORM",
     "<i>Object-Relational Mapper</i>. Traduce clases de Python a tablas SQL, para no "
     "escribir consultas a mano. <font face='Courier' size=8>Libro.objects.filter(...)</font> "
     "es el ORM trabajando."),
    ("Modelo",
     "Clase de Python que representa una tabla. <font face='Courier' size=8>Libro</font>, "
     "<font face='Courier' size=8>Autor</font> y <font face='Courier' size=8>Prestamo</font> "
     "son modelos; las reseñas <b>no</b>."),
    ("Migración",
     "Archivo que describe un cambio en la estructura de la base, para poder aplicarlo de "
     "forma reproducible. Las genera <font face='Courier' size=8>makemigrations</font>."),
    ("Excepción propia",
     "Una clase de error definida por el proyecto, como "
     "<font face='Courier' size=8>MicroservicioNoDisponible</font>. Permite que la vista "
     "atrape el problema sin saber nada de <font face='Courier' size=8>urllib</font>."),
    ("urllib",
     "Librería de la biblioteca estándar de Python para hacer pedidos HTTP. Se usa en "
     "lugar de <font face='Courier' size=8>requests</font> para no sumar dependencias."),
    ("WSGI",
     "El estándar que conecta un servidor web con una aplicación Python sincrónica. "
     "<font face='Courier' size=8>biblioteca/wsgi.py</font> expone el objeto "
     "<font face='Courier' size=8>application</font> que la plataforma ejecuta."),
])

c += glosario("FastAPI y el microservicio", [
    ("FastAPI",
     "Framework de Python para construir APIs. Valida los datos y genera la documentación "
     "automáticamente a partir de los tipos que se declaran."),
    ("ASGI",
     "El equivalente asincrónico de WSGI. FastAPI es una aplicación ASGI; el objeto se "
     "llama <font face='Courier' size=8>app</font>."),
    ("Pydantic",
     "Librería de validación por tipos. <font face='Courier' size=8>ResenaNueva</font> es "
     "un modelo de Pydantic: cumple el papel de un formulario de Django."),
    ("APIRouter",
     "Agrupador de rutas de FastAPI. Con "
     "<font face='Courier' size=8>APIRouter(prefix=\"/api\")</font> todas las rutas del "
     "servicio cuelgan de <font face='Courier' size=8>/api</font> sin repetirlo una por una."),
    ("uvicorn",
     "El servidor que ejecuta la aplicación ASGI. En local: "
     "<font face='Courier' size=8>uvicorn main:app --port 8001</font>."),
    ("Swagger / /docs",
     "La documentación interactiva que FastAPI genera sola, donde se pueden probar los "
     "endpoints desde el navegador."),
])

c.append(PageBreak())

c += glosario("Bases de datos", [
    ("SQLite",
     "Base de datos que vive en un único archivo. Perfecta para desarrollo; inservible en "
     "un servidor sin disco persistente, que es el motivo de haber migrado a PostgreSQL."),
    ("PostgreSQL",
     "Motor de base de datos que corre como servicio aparte, en su propio servidor. La "
     "usan el sitio y el microservicio."),
    ("Supabase",
     "Servicio que ofrece PostgreSQL administrado en la nube, más una API HTTP para "
     "consultarlo. El microservicio usa esa API; Django se conecta al Postgres directo."),
    ("Connection pooler",
     "Intermediario que reutiliza conexiones a la base en lugar de abrir una nueva cada "
     "vez. En Supabase hay que usar el <b>Session pooler</b>: la conexión directa es IPv6 "
     "y la plataforma no la alcanza."),
    ("RLS",
     "<i>Row Level Security</i>. Mecanismo de PostgreSQL que decide, fila por fila, quién "
     "puede leer o escribir. Acá está activado <b>sin políticas públicas</b>: con la clave "
     "anónima nadie entra."),
    ("service_role / anon",
     "Las dos claves de Supabase. La <font face='Courier' size=8>anon</font> es pública y "
     "respeta RLS; la <font face='Courier' size=8>service_role</font> lo atraviesa y es "
     "secreta: vive solo en el servidor."),
    ("Idempotente",
     "Que se puede ejecutar varias veces con el mismo resultado. El "
     "<font face='Courier' size=8>seed.py</font> lo es: correrlo dos veces no duplica datos."),
])

c += glosario("Despliegue", [
    ("Serverless",
     "Modelo donde el código se ejecuta en respuesta a una petición, sin un servidor "
     "encendido de forma permanente. No hay disco que persista entre pedidos: de ahí que "
     "SQLite no sirva."),
    ("Función",
     "La unidad que se ejecuta en serverless. Toda la aplicación Django se empaqueta en "
     "una sola función."),
    ("Cold start",
     "La demora extra del primer pedido, cuando la función tiene que inicializarse desde "
     "cero porque no había ninguna instancia despierta."),
    ("Build",
     "El proceso que instala dependencias y arma el paquete que se va a ejecutar. Ocurre "
     "una vez por despliegue, no en cada pedido."),
    ("Deployment",
     "Una versión concreta y <b>inmutable</b> del proyecto ya construida. No se modifica: "
     "cada cambio genera uno nuevo."),
    ("Alias / dominio",
     "El nombre público que apunta a un deployment. Un deployment nuevo no se ve hasta que "
     "el alias lo apunta: si la URL no cambia pese a los cambios, este es el primer lugar "
     "donde mirar."),
    ("Promote",
     "La acción de hacer que los alias apunten a un deployment ya construido."),
    ("Entrypoint",
     "El archivo y la variable que la plataforma carga para arrancar la aplicación: "
     "<font face='Courier' size=8>biblioteca.wsgi:application</font> para el sitio y "
     "<font face='Courier' size=8>main:app</font> para la API."),
    ("Rewrite",
     "Regla que decide, según la ruta pedida, qué servicio la atiende. Las de este "
     "proyecto mandan <font face='Courier' size=8>/api/*</font> a la API y el resto al sitio."),
    ("Root Directory",
     "La carpeta que la plataforma toma como raíz del proyecto. Con Services va vacía, "
     "porque el reparto lo define <font face='Courier' size=8>vercel.json</font>."),
    ("Variable de entorno",
     "Valor que se le pasa al programa desde fuera del código, como una credencial o una "
     "URL. Permite cambiar la configuración sin tocar ni desplegar código nuevo."),
    ("collectstatic",
     "Comando de Django que junta los archivos estáticos en una carpeta para que el "
     "servidor los sirva. La plataforma lo corre sola durante el build."),
])


SALIDA.parent.mkdir(parents=True, exist_ok=True)
doc = SimpleDocTemplate(
    str(SALIDA), pagesize=A4,
    leftMargin=2.2 * cm, rightMargin=2.2 * cm,
    topMargin=2.0 * cm, bottomMargin=2.2 * cm,
    title="Microservicio de Reseñas — Biblioteca Comunitaria",
    author="Proyecto Biblioteca Comunitaria",
    subject="Explicación del microservicio y su integración con el sitio Django",
)
doc.build(c, onFirstPage=pie, onLaterPages=pie)
print(f"PDF generado: {SALIDA}")
