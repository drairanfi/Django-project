# AGENTS.md

Instrucciones para agentes de IA que trabajen en este repositorio.

## Qué es este proyecto

Trabajo práctico académico de la materia **Desarrollo Web**: una biblioteca
comunitaria en Django con dos apps (`libros` y `prestamos`).

**El objetivo es didáctico, no productivo.** El código tiene que ser legible para
alguien que recién arranca con Django y tiene que mostrar los patrones del framework
de forma explícita. Un código más corto o más "inteligente" que esconda el patrón es
un código peor para este repo.

## Stack

| Componente | Versión |
|---|---|
| Python | 3.14.7 |
| Django | 6.1.1 |
| Base de datos | SQLite en local, PostgreSQL (Supabase) en el despliegue |
| Microservicio | FastAPI + Supabase, en `microservicio_resenas/` (deps propias) |

Sin CSS, sin JavaScript, sin frontend build. **No agregues librerías de frontend**
(ni Bootstrap, ni Tailwind, ni HTMX) salvo pedido explícito. Las llamadas HTTP
salientes usan `urllib` de la biblioteca estándar, no `requests`.

`requirements.txt` tiene solo lo que el despliegue necesita: Django, `psycopg`
(driver de PostgreSQL), `dj-database-url` (parsea `DATABASE_URL`) y `whitenoise`
(archivos estáticos). No sumes nada más sin pedido explícito.

`microservicio_resenas/` es la excepción: es un servicio aparte, con su propio
`requirements.txt` y su propio ciclo de vida. Sus dependencias NO se instalan en el
`venv/` de Django.

## Comandos

El entorno virtual vive en `venv/` y **no** está versionado (`.gitignore` lo excluye,
igual que `db.sqlite3` y `staticfiles/`). Para recrearlo: `python3 -m venv venv` y
`venv/bin/pip install -r requirements.txt`. Después usá su intérprete directamente:

```bash
venv/bin/python manage.py check          # validar configuración
venv/bin/python manage.py test           # correr los 5 tests
venv/bin/python manage.py runserver      # levantar en http://127.0.0.1:8000/
venv/bin/python manage.py makemigrations # tras tocar models.py
venv/bin/python manage.py migrate
venv/bin/python seed.py                  # datos de ejemplo (idempotente)
```

Credenciales del admin que crea el seed: `admin` / `admin123`.

### Smoke test de las vistas

`ALLOWED_HOSTS` está vacío, así que el `Client` de tests falla con `DisallowedHost`
si lo usás fuera de `manage.py test`. Para un smoke test manual hay que parchearlo:

```python
from django.conf import settings
settings.ALLOWED_HOSTS = ["testserver"]
```

## Convenciones de código

### Vistas: siempre el patrón de tres pasos

Toda vista sigue esta estructura, sin excepciones. Es el patrón que el trabajo
práctico tiene que demostrar:

```python
def libros_por_categoria(request, categoria_id):
    """Una línea explicando qué hace la vista."""
    # 1. consumir el modelo
    categoria = get_object_or_404(Categoria, pk=categoria_id)
    libros = Libro.objects.filter(categoria=categoria)

    # 2. armar el context como variable con nombre
    context = {
        "categoria": categoria,
        "libros": libros,
    }

    # 3. enviarlo al template
    return render(request, "libros/por_categoria.html", context)
```

Reglas duras:

- **Vistas basadas en funciones.** No conviertas nada a Class-Based Views.
- **`context` siempre como variable nombrada**, nunca un dict inline dentro de
  `render()`. El patrón tiene que verse.
- **Usá los shortcuts**: `render()` y `get_object_or_404()`. Nada de `HttpResponse`
  crudo, `loader.get_template()` ni `raise Http404` a mano.
- **Docstring de una línea** por vista, en español.
- La lógica de negocio (cambiar `libro.disponible`, guardar fechas) va en la vista,
  nunca en el template.

`get_object_or_404` es para buscar **un** objeto por PK. Para filtrar un queryset usá
`.filter()` normal — una lista vacía es un resultado válido, no un 404.

### Templates: HTML plano, sin estilos

Se eliminó deliberadamente todo el CSS para que el proyecto se vea básico.

- **No agregues CSS, clases, `<style>`, frameworks ni JS.** Si te parece que "queda
  feo", así tiene que quedar.
- Todos los templates extienden `templates/base.html`.
- Tablas con `border="1"`, separadores con `<hr>`, navegación con `|` entre links.
- URLs siempre con `{% url 'app:nombre' %}`, nunca hardcodeadas.
- Los templates solo muestran datos del context. No consultan la base de datos.

### Idioma

- Modelos, vistas, variables, URLs y templates: **en español** (`Libro`, `Prestamo`,
  `lista_lectores`). El dominio del proyecto es en español y hay que mantenerlo.
- Con tildes correctas en el texto visible y en los docstrings.
- Nombres de campos de modelo sin tildes (`anio_publicacion`, no `año_publicacion`).

## Estructura

```
biblioteca/        configuración del proyecto (settings, urls raíz)
libros/            app 1: Autor, Categoria, Libro → 4 vistas
prestamos/         app 2: Lector, Prestamo → 5 vistas
microservicio_resenas/  servicio aparte: FastAPI + Supabase, se despliega en Vercel
templates/         base.html (compartido)
seed.py            carga de datos de ejemplo, idempotente con get_or_create
README.md          documentación del TP
```

Cada app tiene su `urls.py` con `app_name` definido y se incluye desde
`biblioteca/urls.py` con `include()`.

## Al modificar el código

1. Corré `venv/bin/python manage.py check` y `venv/bin/python manage.py test`.
2. **El README referencia números de línea** (ej. `libros/views.py:32`). Si agregás o
   sacás líneas en `views.py`, esas referencias quedan desactualizadas — actualizalas
   en las tablas de "Requisitos de la consigna" y "Vistas y rutas".
3. Si tocás `models.py`, generá la migración en el mismo cambio.
4. Commits en español, formato conventional commits (`feat:`, `fix:`, `docs:`).

## Microservicio de reseñas

Las reseñas NO son un modelo de Django. Viven en Supabase y se leen por HTTP
desde `microservicio_resenas/`, desplegado en Vercel.

Reglas:

- **No crees un modelo `Resena` en Django.** El punto del ejercicio es que ese
  dato viva fuera de SQLite.
- Toda llamada HTTP pasa por `libros/servicios.py`. Las vistas no arman URLs ni
  parsean JSON: llaman a una función del módulo de servicios.
- Toda llamada remota va envuelta en `try/except MicroservicioNoDisponible` y
  con timeout. Si el servicio se cae, la vista muestra un aviso, nunca un 500.
- Las credenciales de Supabase viven solo en variables de entorno del
  microservicio. Django no las conoce: solo conoce `MICROSERVICIO_RESENAS_URL`.

Para trabajar en local hay que levantar el microservicio en el puerto 8001
(ver `microservicio_resenas/README.md`).

## Configuración por entorno

`settings.py` no tiene valores de producción escritos a mano: los lee de variables
de entorno y cae a valores de desarrollo cuando no están.

| Variable | Sin ella | Con ella |
|---|---|---|
| `DATABASE_URL` | SQLite en `db.sqlite3` | PostgreSQL (Supabase) |
| `DJANGO_SECRET_KEY` | la clave de desarrollo | la clave del servidor |
| `DJANGO_DEBUG` | `True` | `False` si vale otra cosa |
| `MICROSERVICIO_RESENAS_URL` | `http://127.0.0.1:8001` | la URL del servicio desplegado |

Reglas:

- **No escribas credenciales en `settings.py`.** Van por variable de entorno.
- **No quites el fallback a SQLite.** Los tests y el desarrollo local dependen de él.
- `conn_max_age=0` es a propósito: cada invocación serverless es efímera, las
  conexiones persistentes no sobreviven y agotan el pool de Postgres.

## Despliegue

Son **dos aplicaciones separadas**, cada una su propio proyecto en Vercel:

| Qué | Root Directory | Entrypoint |
|---|---|---|
| Sitio Django | raíz del repo | `manage.py` → `biblioteca/wsgi.py` |
| Microservicio de reseñas | `microservicio_resenas` | `main.py` |

Vercel detecta Django por `manage.py`, resuelve el entrypoint desde
`WSGI_APPLICATION` y corre `collectstatic` solo porque `STATIC_ROOT` está definido.
No hace falta `vercel.json` ni build command.
