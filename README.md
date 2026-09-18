# 📚 Biblioteca Comunitaria — Proyecto Django

Aplicación web en **Django 6.1** que gestiona una biblioteca comunitaria: catálogo
de libros, autores, categorías, lectores y el préstamo/devolución de ejemplares.

> Trabajo práctico de la materia **Desarrollo Web** — Python / Django.

---

## Índice

1. [Problemática identificada](#-problemática-identificada)
2. [Solución propuesta](#-solución-propuesta)
3. [Requisitos de la consigna y dónde se aplican](#-requisitos-de-la-consigna-y-dónde-se-aplican)
4. [El patrón vista → context → template](#-el-patrón-vista--context--template)
5. [Arquitectura del proyecto](#-arquitectura-del-proyecto)
6. [Modelos y relaciones](#-modelos-y-relaciones)
7. [Vistas y rutas](#-vistas-y-rutas)
8. [Funcionalidades](#-funcionalidades)
9. [Cómo montar el proyecto desde cero](#-cómo-montar-el-proyecto-desde-cero)
10. [Cómo ejecutar el proyecto](#-cómo-ejecutar-el-proyecto)
11. [Datos de ejemplo](#-datos-de-ejemplo)
12. [Panel de administración](#-panel-de-administración)
13. [Tests](#-tests)
14. [Microservicio externo de reseñas](#-microservicio-externo-de-reseñas)
15. [Tecnologías utilizadas](#-tecnologías-utilizadas)

---

## 🎯 Problemática identificada

Una biblioteca comunitaria maneja el préstamo de libros **sin ningún sistema**:
los registros se anotan en papel, no se sabe con certeza qué libro tiene quién,
y tampoco se puede consultar rápido si un título está disponible.

**Consecuencias del problema:**
- Se pierden libros porque no se registra a quién se prestaron.
- No hay forma de saber qué libros existen y cuáles están disponibles.
- Filtrar por categoría o por autor requiere revisar estanterías o listas a mano.
- La devolución no se controla: nadie avisa cuando un libro está vencido.

## ✅ Solución propuesta

Un sistema web que permite:

- **Consultar el catálogo** completo de la biblioteca y saber al instante si cada
  libro está disponible o prestado.
- **Filtrar los libros** por categoría (Ficción, Ciencia, Historia…) y por autor.
- **Registrar préstamos**: un lector se lleva un libro y el sistema lo marca como
  no disponible automáticamente.
- **Registrar devoluciones**: al devolver el libro, el sistema lo libera solo.
- **Ver el historial** de préstamos de cada lector y los préstamos filtrados por
  estado (activo / devuelto / vencido).
- **Administrar todos los datos** desde el panel de Django (`/admin/`).

---

## 🧩 Requisitos de la consigna y dónde se aplican

| Requisito | Dónde se cumple en el código | Explicación |
|---|---|---|
| **Múltiples vistas en una App** | `libros/views.py` → 5 vistas (`inicio`, `detalle_libro`, `libros_por_categoria`, `libros_por_autor`, `resenas_libro`) — `prestamos/views.py` → 5 vistas (`lista_lectores`, `detalle_lector`, `prestamos_por_estado`, `registrar_devolucion`, `crear_prestamo`) | Ambas apps tienen **más de una vista** que responde por distintas URLs. |
| **Múltiples Apps en un proyecto** | `biblioteca/settings.py` → `INSTALLED_APPS` incluye `'libros'` y `'prestamos'` | El proyecto se divide en **2 aplicaciones** con responsabilidades separadas. |
| **Modelos consultados desde las vistas** | `libros/views.py:6-53` y `prestamos/views.py:10-92` usan `Libro.objects.all()`, `Libro.objects.filter(categoria=categoria)`, `get_object_or_404(...)` | Cada vista **consulta la base de datos** a través del ORM y pasa los resultados al template. |
| **Uso de shortcuts de Django** | Las 10 vistas usan `render(...)`; 7 usan `get_object_or_404(...)`. Cero `HttpResponse` crudo, cero `loader.get_template`, cero `raise Http404` manual | `render()` une template + context en una sola respuesta. `get_object_or_404()` evita el `try/except Model.DoesNotExist` a mano y devuelve un 404 real. |
| **Patrón vista → context → template** | Las 10 vistas declaran una variable `context` explícita antes del `return render(...)` — ver [sección dedicada](#-el-patrón-vista--context--template) | La vista **consume el modelo**, arma un **diccionario `context`** y se lo **envía al template**. El template solo muestra: no consulta la base de datos. |
| **Rutas dinámicas con parámetros y vistas que hacen algo con esa info** | `libros/urls.py:9-11` (`<int:libro_id>`, `<int:categoria_id>`, `<int:autor_id>`) y `prestamos/urls.py:9-12` (`<int:lector_id>`, `<str:estado>`, `<int:libro_id>`, `<int:prestamo_id>`) | Las URLs **capturan parámetros** y las vistas los reciben en su firma para filtrar datos, crear o actualizar registros. |
| **Una vista consume un microservicio propio en la nube, sobre una base distinta de SQLite** | `libros/views.py:58` → `resenas_libro()` llama por HTTP a `microservicio_resenas/` (FastAPI en Render) a través del cliente `libros/servicios.py` — ver [sección dedicada](#-microservicio-externo-de-reseñas) | Las reseñas viven en **Supabase (PostgreSQL)**, no en `db.sqlite3`. Django no tiene credenciales de esa base: solo conoce una URL HTTP. |

### Detalle: rutas dinámicas → cómo fluye la información

1. **La URL captura el parámetro** (con `path`):

   ```python
   # prestamos/urls.py:9
   path("lector/<int:lector_id>/", views.detalle_lector, name="detalle_lector"),
   ```

2. **La vista recibe el parámetro** como argumento:

   ```python
   # prestamos/views.py:20
   def detalle_lector(request, lector_id):
   ```

3. **La vista usa ese parámetro** para consultar la base de datos:

   ```python
   # prestamos/views.py:22-23
   lector = get_object_or_404(Lector, pk=lector_id)
   prestamos = lector.prestamos.all()
   ```

Ejemplos de URLs que hacen algo con su parámetro:

| URL | Parámetro | Qué hace la vista |
|---|---|---|
| `/libro/3/` | `libro_id = 3` | Busca el libro con ese id y muestra su detalle + cantidad de préstamos activos |
| `/categoria/2/` | `categoria_id = 2` | Filtra los libros de esa categoría |
| `/autor/1/` | `autor_id = 1` | Filtra los libros de ese autor |
| `/lector/5/` | `lector_id = 5` | Muestra los datos y el historial de préstamos del lector |
| `/estado/activo/` | `estado = "activo"` | Filtra los préstamos según su estado |
| `/prestar/4/` | `libro_id = 4` | Registra un préstamo del libro (lo marca como no disponible) |
| `/devolver/12/` | `prestamo_id = 12` | Marca el préstamo como devuelto y libera el libro |

---

## 🔄 El patrón vista → context → template

Este es el patrón central de Django y el que estructura **las 9 vistas** del proyecto.
Siempre son los mismos tres pasos, en el mismo orden:

```python
# libros/views.py:34
def libros_por_categoria(request, categoria_id):
    """Busca la Categoría y filtra los Libros que le pertenecen."""

    # 1. LA VISTA CONSUME EL MODELO (consulta la base de datos con el ORM)
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    libros = Libro.objects.filter(categoria=categoria)

    # 2. ARMA EL CONTEXT (un diccionario: "nombre en el template" -> dato)
    context = {
        "categoria": categoria,
        "libros": libros,
    }

    # 3. SE LO ENVÍA AL TEMPLATE con el shortcut render()
    return render(request, "libros/por_categoria.html", context)
```

Y del otro lado, el template **solo muestra** lo que recibió — no consulta nada:

```html
<!-- libros/templates/libros/por_categoria.html -->
<h2>Libros de {{ categoria.nombre }}</h2>
{% for libro in libros %}
    <li>{{ libro.titulo }} - {{ libro.anio_publicacion }}</li>
{% endfor %}
```

Las claves del `context` (`"categoria"`, `"libros"`) son **exactamente** los nombres
que se usan entre llaves en el HTML. Ese diccionario es el contrato entre la vista y
el template.

### Los dos shortcuts que se usan

| Shortcut | Qué reemplaza | Por qué se usa |
|---|---|---|
| `render(request, template, context)` | `HttpResponse(loader.get_template(...).render(context, request))` | Carga el template, lo renderiza con el context y devuelve el `HttpResponse`, todo en una línea. |
| `get_object_or_404(Modelo, pk=id)` | `try: Modelo.objects.get(pk=id) / except Modelo.DoesNotExist: raise Http404` | Si el objeto no existe devuelve un **404 real** en vez de reventar con un error 500. |

Comprobación de que el 404 funciona de verdad:

```
GET /libro/1/       → 200 OK
GET /libro/99999/   → 404 Not Found   ← get_object_or_404 haciendo su trabajo
```

> **Nota sobre `prestamos_por_estado`:** es la única vista sin `get_object_or_404`, y es
> a propósito. Ese shortcut sirve para buscar **un** objeto por su clave primaria; esta
> vista filtra un *queryset* por un string de la URL. Que no haya préstamos en un estado
> no es un error, es un resultado válido (una lista vacía).

## 🏗️ Arquitectura del proyecto

```
proyecto_django_biblioteca/
├── venv/                      → Entorno virtual con Python 3.14 y Django 6.1.1
├── biblioteca/                → Configuración general del proyecto
│   ├── settings.py            → Configuración (apps, idioma, zona horaria, BD)
│   ├── urls.py                → Enrutador principal
│   ├── wsgi.py / asgi.py      → Puntos de entrada para servidores
│   └── __init__.py
├── libros/                    → App 1: catálogo de libros
│   ├── models.py              → Autor, Categoria, Libro
│   ├── views.py               → 4 vistas basadas en funciones (patron context)
│   ├── urls.py                → Rutas de la app libros
│   ├── admin.py               → Registro de modelos en el admin
│   ├── migrations/            → Migraciones de la app
│   └── templates/libros/      → Plantillas HTML de la app
├── prestamos/                 → App 2: gestión de préstamos
│   ├── models.py              → Lector, Prestamo
│   ├── views.py               → 5 vistas basadas en funciones (patron context)
│   ├── urls.py                → Rutas de la app prestamos
│   ├── admin.py               → Registro de modelos en el admin
│   ├── tests.py               → Tests automáticos
│   ├── migrations/            → Migraciones de la app
│   └── templates/prestamos/   → Plantillas HTML de la app
├── templates/
│   └── base.html              → Plantilla base con la navegación comun
├── manage.py                  → Utilidad de línea de comandos de Django
├── seed.py                    → Script de carga de datos de ejemplo
├── db.sqlite3                 → Base de datos SQLite
└── README.md                  → Este documento
```

### Modelo vista-controlador de Django (flujo de una petición)

```
Navegador escribe:  http://localhost:8000/libro/3/
        │
        ▼
biblioteca/urls.py  ── include('libros.urls') ──►  libros/urls.py
                                                       │  path("libro/<int:libro_id>/", ...)
                                                       ▼
                                            libros/views.py: detalle_libro(request, 3)
                                                       │  Libro.objects.filter(pk=3)
                                                       ▼
                                            libros/models.py  (base de datos)
                                                       │
                                                       ▼
                                  plantilla detalle_libro.html  ←  respuesta HTML
```

---

## 💾 Modelos y relaciones

### App `libros`

| Modelo | Campos | Relaciones |
|---|---|---|
| **Autor** | `nombre`, `apellido`, `nacionalidad`, `fecha_nacimiento` | — |
| **Categoria** | `nombre` | — |
| **Libro** | `titulo`, `isbn`, `anio_publicacion`, `paginas`, `disponible` | `categoria` → ForeignKey a `Categoria` · `autores` → ManyToMany a `Autor` |

### App `prestamos`

| Modelo | Campos | Relaciones |
|---|---|---|
| **Lector** | `nombre`, `email`, `telefono`, `fecha_registro` | — |
| **Prestamo** | `fecha_prestamo`, `fecha_devolucion`, `estado` | `lector` → ForeignKey a `Lector` · `libro` → ForeignKey a `Libro` |

```python
# prestamos/models.py:20-28
class Prestamo(models.Model):
    ESTADO_CHOICES = [("activo", "Activo"), ("devuelto", "Devuelto"), ("vencido", "Vencido")]
    lector = models.ForeignKey(Lector, on_delete=models.CASCADE, related_name="prestamos")
    libro = models.ForeignKey(Libro, on_delete=models.CASCADE, related_name="prestamos")
    fecha_prestamo = models.DateField(auto_now_add=True)
    fecha_devolucion = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default="activo")
```

**Relación clave del negocio:** `Prestamo` une a un `Lector` con un `Libro`. El campo
`disponible` del libro se pone en `False` al prestarlo y vuelve a `True` al devolverlo.
Ese cambio de estado lo hace la **vista** (no el template), con `libro.save()`.

---

## 🚏 Vistas y rutas

### App `libros` (catálogo)

| URL | Vista | Plantilla | Función |
|---|---|---|---|
| `/` | `inicio` (`libros/views.py:8`) | `inicio.html` | Lista todos los libros + disponibles + categorías |
| `/libro/<int:libro_id>/` | `detalle_libro` (`libros/views.py:22`) | `detalle_libro.html` | Detalle del libro y sus préstamos activos |
| `/categoria/<int:categoria_id>/` | `libros_por_categoria` (`libros/views.py:34`) | `por_categoria.html` | Libros filtrados por categoría |
| `/autor/<int:autor_id>/` | `libros_por_autor` (`libros/views.py:46`) | `por_autor.html` | Libros filtrados por autor |
| `/libro/<int:libro_id>/resenas/` | `resenas_libro` (`libros/views.py:58`) | `resenas.html` | Reseñas del libro traídas del **microservicio externo** |

### App `prestamos` (préstamos)

| URL | Vista | Plantilla | Función |
|---|---|---|---|
| `/prestamos/lectores/` | `lista_lectores` (`prestamos/views.py:10`) | `lectores.html` | Lista todos los lectores y su cantidad de préstamos |
| `/prestamos/lector/<int:lector_id>/` | `detalle_lector` (`prestamos/views.py:20`) | `detalle_lector.html` | Datos del lector + historial de préstamos |
| `/prestamos/estado/<str:estado>/` | `prestamos_por_estado` (`prestamos/views.py:32`) | `prestamos.html` | Préstamos filtrados por estado |
| `/prestamos/devolver/<int:prestamo_id>/` | `registrar_devolucion` (`prestamos/views.py:47`) | `devolucion.html` | Marca devuelto y libera el libro |
| `/prestamos/prestar/<int:libro_id>/` | `crear_prestamo` (`prestamos/views.py:65`) | `crear_prestamo.html` | Registra un préstamo (GET = form, POST = guarda) |

Las URLs de las apps se incluyen en el enrutador principal:

```python
# biblioteca/urls.py:22-23
path('', include('libros.urls')),
path('prestamos/', include('prestamos.urls')),
```

---

## 🛠️ Funcionalidades

1. **Ver el catálogo** — en `/` se listan todos los libros con su estado
   (Disponible / Prestado) y las categorías disponibles.
2. **Ver detalle de un libro** — en `/libro/ID/` se muestra ISBN, año, páginas,
   categoría, autores y si tiene préstamos activos.
3. **Filtrar por categoría** — desde `/categoria/ID/` (los enlaces de categoría de
   la home también llevan ahí).
4. **Filtrar por autor** — desde `/autor/ID/`, accesible desde el detalle de un libro.
5. **Registrar un préstamo** — en `/prestar/ID/` se elige el lector en un formulario;
   al confirmar, el libro pasa a no disponible. Si el libro ya está prestado, avisa.
6. **Registrar una devolución** — en `/devolver/ID/`; el préstamo pasa a "devuelto",
   se guarda la fecha y el libro vuelve a estar disponible.
7. **Ver préstamos por estado** — en `/estado/activo|devuelto|vencido/`.
8. **Ver el historial de un lector** — en `/lector/ID/` con botón de devolución
   cuando corresponde.
9. **Administrar datos** — el panel de Django (`/admin/`) permite CRUD completo de
   todos los modelos con búsqueda y filtros.

---

## 🚀 Cómo montar el proyecto desde cero

Estos pasos sirven para cualquier máquina con Python instalado (se explica por si
el profesor quiere reproducirlo en otra computadora).

### 1. Crear el entorno virtual

```bash
python3 -m venv venv
```

### 2. Activar el entorno virtual

**macOS / Linux:**

```bash
source venv/bin/activate
```

**Windows:**

```bash
venv\Scripts\activate
```

### 3. Instalar Django

```bash
pip install django
```

> Verificar la instalación: `python -m django --version` → debe mostrar 6.1.x.

### 4. Crear el proyecto y las apps

```bash
django-admin startproject biblioteca .
python manage.py startapp libros
python manage.py startapp prestamos
```

### 5. Registrar las apps en `biblioteca/settings.py`

Agregar al final de `INSTALLED_APPS`:

```python
'libros',
'prestamos',
```

### 6. Crear las migraciones y aplicarlas

```bash
python manage.py makemigrations
python manage.py migrate
```

### 7. Cargar datos de ejemplo

```bash
python seed.py
```

### 8. (Opcional) Crear un superusuario manualmente

```bash
python manage.py createsuperuser
```

---

## ▶️ Cómo ejecutar el proyecto

Ya con el entorno montado (o usando el `venv/` que viene en el zip):

```bash
python manage.py runserver
```

Abrir en el navegador:

| Página | URL |
|---|---|
| Inicio / catálogo | http://127.0.0.1:8000/ |
| Panel de administración | http://127.0.0.1:8000/admin/ |

---

## 📊 Datos de ejemplo

El script `seed.py` carga:

- **3 categorías**: Ficción, Ciencia, Historia
- **3 autores**: Jorge Luis Borges, Julio Verne, Stephen Hawking
- **6 libros** repartidos en las categorías
- **2 lectores**: Ana García, Carlos Pérez
- **2 préstamos**: uno activo (Ficciones) y uno devuelto (El Aleph)

Además crea el **usuario admin**:

```
usuario:   admin
contraseña: admin123
```

Se vuelve a correr tantas veces como se quiera sin duplicar datos
(usa `get_or_create`).

---

## 🛡️ Panel de administración

Con `admin` / `admin123` (o el superusuario que crees) podés entrar a
`/admin/` y:

- Crear, editar y borrar autores, categorías, libros, lectores y préstamos.
- Buscar libros por título/ISBN y filtrar por disponibilidad y categoría.
- Ver los préstamos de un lector desde el panel de ese lector.

---

## 🧪 Tests

El proyecto incluye tests automáticos en `prestamos/tests.py` y `libros/tests.py`:

| Test | Qué verifica |
|---|---|
| `test_detalle_libro_muestra_datos` | La vista `/libro/ID/` responde 200 y muestra el título |
| `test_filtrar_por_categoria` | La vista `/categoria/ID/` responde 200 y muestra el libro |
| `test_prestar_y_devolver` | El flujo completo: prestar → libro no disponible → devolver → libro disponible |
| `test_muestra_las_resenas_que_devuelve_el_microservicio` | La vista de reseñas renderiza lo que responde el servicio externo |
| `test_si_el_microservicio_no_responde_la_pagina_igual_carga` | Si el microservicio falla, la vista responde 200 con un aviso — nunca un 500 |

Para correrlos:

```bash
python manage.py test
```

Salida esperada:

```
Found 5 test(s).
System check identified no issues (0 silenced).
OK
```

Los dos tests de reseñas usan `unittest.mock.patch` sobre `libros.servicios`:
**no hacen llamadas de red reales**. Un test que dependa de un servicio remoto
falla cuando se cae internet, y eso no es una falla del código.

### Chequeo rápido sin correr el servidor

Antes de entregar conviene validar que el proyecto no tiene errores de configuración:

```bash
python manage.py check
```

Salida esperada: `System check identified no issues (0 silenced).`

---

## 🌐 Microservicio externo de reseñas

Las reseñas de los libros **no están en SQLite**. Viven en un microservicio
propio, escrito en FastAPI, desplegado en **Render**, que guarda los datos en
**Supabase** (PostgreSQL administrado). Django los consume por HTTP.

```
Navegador
   │
   ▼
Django (SQLite, local)
   │  Libro, Autor, Categoria, Prestamo  ──► ORM ──► db.sqlite3
   │
   └─ vista resenas_libro() ──HTTP GET──► microservicio-resenas (Render)
                                              │
                                              └── tabla resenas ──► Supabase (PostgreSQL)
```

El código del servicio está en [`microservicio_resenas/`](microservicio_resenas/),
con sus pasos de despliegue en [su README](microservicio_resenas/README.md).

### Quién habla con quién

| Dato | Dónde vive | Cómo lo obtiene Django |
|---|---|---|
| Libros, autores, categorías, préstamos | SQLite local | ORM de Django |
| Reseñas y puntajes | Supabase (nube) | HTTP contra el microservicio |

Django **no** tiene credenciales de Supabase ni conoce su esquema. Solo conoce
una URL. Si mañana el microservicio cambia Postgres por otra base, Django no se
entera.

### Las tres capas del lado Django

1. **`libros/servicios.py`** — el cliente HTTP. Único módulo que sabe que las
   reseñas son remotas. Usa `urllib` de la biblioteca estándar, así que el
   proyecto sigue sin dependencias externas. Traduce cualquier falla de red a
   una excepción propia, `MicroservicioNoDisponible`.
2. **`libros/views.py` → `resenas_libro()`** — la vista. Mismo patrón de
   siempre: consume datos, arma el `context`, lo manda al template. La
   diferencia es que consume dos fuentes: el ORM para el `Libro` y el
   microservicio para las reseñas.
3. **`libros/templates/libros/resenas.html`** — el template. No sabe de dónde
   salieron los datos: recibe una lista en el context, como cualquier otra vista.

```python
# libros/views.py:58
def resenas_libro(request, libro_id):
    """Combina un Libro del ORM con sus reseñas traídas del microservicio externo."""
    libro = get_object_or_404(Libro, pk=libro_id)     # ← base local
    ...
    try:
        datos = servicios.obtener_resenas(libro.id)   # ← servicio remoto
        error = ""
    except servicios.MicroservicioNoDisponible as fallo:
        datos = {}
        error = f"El microservicio de reseñas no está disponible ({fallo})"
```

### Por qué el `try/except` no es opcional

Una consulta al ORM local falla casi solo si hay un bug. Una llamada HTTP a otra
máquina falla por motivos que no controlás: se cayó la red, Render durmió el
servicio, Supabase está lento, cambió la URL. **Toda llamada remota se asume
falible.** Si el microservicio no responde, la página se sigue mostrando con un
aviso; no devuelve un error 500. Eso es *degradación controlada*, y es la
diferencia práctica entre leer de una base local y leer de un servicio externo.

Por lo mismo hay un **timeout** de 5 segundos: sin timeout, una vista queda
colgada esperando a un servidor que quizá nunca conteste.

### Configuración

```python
# biblioteca/settings.py
MICROSERVICIO_RESENAS_URL = os.environ.get(
    'MICROSERVICIO_RESENAS_URL',
    'http://127.0.0.1:8001',
).rstrip('/')

MICROSERVICIO_RESENAS_TIMEOUT = 5  # segundos
```

La URL se lee de una variable de entorno. En local apunta al servicio corriendo
en el puerto 8001; en la entrega apunta a Render:

```bash
export MICROSERVICIO_RESENAS_URL="https://microservicio-resenas.onrender.com"
venv/bin/python manage.py runserver
```

### Endpoint que se consume

`GET /libros/{libro_id}/resenas` devuelve:

```json
{
  "libro_id": 1,
  "cantidad": 2,
  "promedio": 4.5,
  "resenas": [
    {"id": 1, "libro_id": 1, "lector": "Ana Gómez", "puntaje": 5,
     "comentario": "Imperdible.", "creada_en": "2026-09-18T10:00:00+00:00"}
  ]
}
```

El formulario de la página también hace `POST /resenas` contra el mismo
servicio: la reseña se escribe en Supabase, nunca en SQLite.

### Nota sobre el plan free de Render

El servicio se duerme tras 15 minutos sin tráfico y el primer request puede
tardar ~30-50 segundos en despertarlo — más que el timeout de 5 segundos. Antes
de mostrar el proyecto, abrí la URL del microservicio una vez para despertarlo.

---

## 🧰 Tecnologías utilizadas

| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.14 | Lenguaje de programación |
| Django | 6.1.1 | Framework web (ORM, URLs, vistas, templates, admin) |
| SQLite | — | Base de datos local de Django (archivo `db.sqlite3`) |
| FastAPI | 0.141.1 | Microservicio de reseñas (repo: `microservicio_resenas/`) |
| Supabase | — | PostgreSQL en la nube, base del microservicio |
| Render | — | Hosting del microservicio |
| HTML | — | Plantillas: `base.html` + una por vista, sin CSS ni JS |
| Git / zip | — | Entrega del trabajo práctico |