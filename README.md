# 📚 Biblioteca Comunitaria — Proyecto Django

Aplicación web en **Django 6.1** que gestiona una biblioteca comunitaria: catálogo
de libros, autores, categorías, lectores y el préstamo/devolución de ejemplares.

> Trabajo práctico de la materia **Desarrollo Web** — Python / Django.

---

## Índice

1. [Problemática identificada](#-problemática-identificada)
2. [Solución propuesta](#-solución-propuesta)
3. [Requisitos de la consigna y dónde se aplican](#-requisitos-de-la-consigna-y-dónde-se-aplican)
4. [Arquitectura del proyecto](#-arquitectura-del-proyecto)
5. [Modelos y relaciones](#-modelos-y-relaciones)
6. [Vistas y rutas](#-vistas-y-rutas)
7. [Funcionalidades](#-funcionalidades)
8. [Cómo montar el proyecto desde cero](#-cómo-montar-el-proyecto-desde-cero)
9. [Cómo ejecutar el proyecto](#-cómo-ejecutar-el-proyecto)
10. [Datos de ejemplo](#-datos-de-ejemplo)
11. [Panel de administración](#-panel-de-administración)
12. [Tests](#-tests)
13. [Tecnologías utilizadas](#-tecnologías-utilizadas)

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
| **Múltiples vistas en una App** | `libros/views.py` → 4 vistas (`inicio`, `detalle_libro`, `libros_por_categoria`, `libros_por_autor`) — `prestamos/views.py` → 5 vistas (`lista_lectores`, `detalle_lector`, `prestamos_por_estado`, `registrar_devolucion`, `crear_prestamo`) | Ambas apps tienen **más de una vista** que responde por distintas URLs. |
| **Múltiples Apps en un proyecto** | `biblioteca/settings.py` → `INSTALLED_APPS` incluye `'libros'` y `'prestamos'` | El proyecto se divide en **2 aplicaciones** con responsabilidades separadas. |
| **Modelos consultados desde las vistas** | `libros/views.py:6-43` y `prestamos/views.py:10-79` usan `Libro.objects.all()`, `Libro.objects.filter(categoria=categoria)`, `get_object_or_404(...)` | Cada vista **consulta la base de datos** a través del ORM y pasa los resultados al template. |
| **Rutas dinámicas con parámetros y vistas que hacen algo con esa info** | `libros/urls.py:9-11` (`<int:libro_id>`, `<int:categoria_id>`, `<int:autor_id>`) y `prestamos/urls.py:9-12` (`<int:lector_id>`, `<str:estado>`, `<int:libro_id>`, `<int:prestamo_id>`) | Las URLs **capturan parámetros** y las vistas los reciben en su firma para filtrar datos, crear o actualizar registros. |

### Detalle: rutas dinámicas → cómo fluye la información

1. **La URL captura el parámetro** (con `path`):

   ```python
   # prestamos/urls.py:9
   path("lector/<int:lector_id>/", views.detalle_lector, name="detalle_lector"),
   ```

2. **La vista recibe el parámetro** como argumento:

   ```python
   # prestamos/views.py:17
   def detalle_lector(request, lector_id):
   ```

3. **La vista usa ese parámetro** para consultar la base de datos:

   ```python
   # prestamos/views.py:18-20
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
│   ├── views.py               → 4 vistas basadas en funciones
│   ├── urls.py                → Rutas de la app libros
│   ├── admin.py               → Registro de modelos en el admin
│   ├── migrations/            → Migraciones de la app
│   └── templates/libros/      → Plantillas HTML de la app
├── prestamos/                 → App 2: gestión de préstamos
│   ├── models.py              → Lector, Prestamo
│   ├── views.py               → 5 vistas basadas en funciones
│   ├── urls.py                → Rutas de la app prestamos
│   ├── admin.py               → Registro de modelos en el admin
│   ├── tests.py               → Tests automáticos
│   ├── migrations/            → Migraciones de la app
│   └── templates/prestamos/   → Plantillas HTML de la app
├── templates/
│   └── base.html              → Plantilla base con navegación y estilos
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
| `/` | `inicio` (`libros/views.py:6`) | `inicio.html` | Lista todos los libros + disponibles + categorías |
| `/libro/<int:libro_id>/` | `detalle_libro` (`libros/views.py:17`) | `detalle_libro.html` | Detalle del libro y sus préstamos activos |
| `/categoria/<int:categoria_id>/` | `libros_por_categoria` (`libros/views.py:26`) | `por_categoria.html` | Libros filtrados por categoría |
| `/autor/<int:autor_id>/` | `libros_por_autor` (`libros/views.py:35`) | `por_autor.html` | Libros filtrados por autor |

### App `prestamos` (préstamos)

| URL | Vista | Plantilla | Función |
|---|---|---|---|
| `/prestamos/lectores/` | `lista_lectores` (`prestamos/views.py:10`) | `lectores.html` | Lista todos los lectores y su cantidad de préstamos |
| `/prestamos/lector/<int:lector_id>/` | `detalle_lector` (`prestamos/views.py:17`) | `detalle_lector.html` | Datos del lector + historial de préstamos |
| `/prestamos/estado/<str:estado>/` | `prestamos_por_estado` (`prestamos/views.py:26`) | `prestamos.html` | Préstamos filtrados por estado |
| `/prestamos/devolver/<int:prestamo_id>/` | `registrar_devolucion` (`prestamos/views.py:37`) | `devolucion.html` | Marca devuelto y libera el libro |
| `/prestamos/prestar/<int:libro_id>/` | `crear_prestamo` (`prestamos/views.py:50`) | `crear_prestamo.html` | Registra un préstamo (GET = form, POST = guarda) |

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
3. **Filtrar por categoría** — desde `/categoria/ID/` (los tags de la home también
   llevan ahí).
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

El proyecto incluye tests automáticos en `prestamos/tests.py`:

| Test | Qué verifica |
|---|---|
| `test_detalle_libro_muestra_datos` | La vista `/libro/ID/` responde 200 y muestra el título |
| `test_filtrar_por_categoria` | La vista `/categoria/ID/` responde 200 y muestra el libro |
| `test_prestar_y_devolver` | El flujo completo: prestar → libro no disponible → devolver → libro disponible |

Para correrlos:

```bash
python manage.py test
```

Salida esperada:

```
Found 3 test(s).
System check identified no issues (0 silenced).
OK
```

---

## 🧰 Tecnologías utilizadas

| Tecnología | Versión | Uso |
|---|---|---|
| Python | 3.14 | Lenguaje de programación |
| Django | 6.1.1 | Framework web (ORM, URLs, vistas, templates, admin) |
| SQLite | — | Base de datos (archivo `db.sqlite3`) |
| HTML + CSS | — | Plantillas `base.html` y vistas |
| Git / zip | — | Entrega del trabajo práctico |