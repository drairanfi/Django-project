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
| Base de datos | SQLite (solo lectores/préstamos) y Supabase (libros y reseñas) |
| Microservicios | 4 réplicas del CRUD de libros + reseñas: FastAPI/Python, NodeJS, Java, PHP |

Sin CSS, sin librerías de frontend, sin framework JS. **Las llamadas HTTP
salientes usan `urllib` de la biblioteca estándar, no `requests`.** El único JS
del proyecto es el que guarda en `localStorage` la elección de microservicio en
los formularios de crear/editar/eliminar libro.

`requirements.txt` tiene solo lo que el despliegue necesita: Django, `psycopg`
(driver de PostgreSQL), `dj-database-url` (parsea `DATABASE_URL`) y `whitenoise`
(archivos estáticos). No sumes nada más sin pedido explícito.

`microservicio_resenas/` es la excepción: es un servicio aparte, con su propio
`requirements.txt` y su propio ciclo de vida. Sus dependencias NO se instalan en el
`venv/` de Django. Lo mismo para `microservicio_resenas_nodejs/`,
`microservicio_resenas_java/` y `microservicio_resenas_php/` (sin dependencias
externas: Node usa solo `node:http`, Java solo el JDK, PHP solo el servidor embebido).

## Cómo funciona el CRUD de libros

Los libros NO viven en SQLite: viven en la tabla `libros` de Supabase y los
exponen 4 microservicios en lenguajes distintos (`microservicio_resenas/` en
Python, `microservicio_resenas_nodejs/`, `microservicio_resenas_java/`,
`microservicio_resenas_php/`). Cada uno tiene los mismos endpoints: GET/POST
`/api/libros`, PUT/DELETE `/api/libros/{id}`.

- El usuario elige con qué microservicio se ejecuta cada operación (crear,
  editar, eliminar) desde botones en el formulario; la elección se guarda en
  `localStorage`.
- La lectura del catálogo es **resiliente**: `servicios.obtener_libros()` recorre
  `MICROSERVICIOS_LIBROS_ORDEN_LECTURA` (python → nodejs → java → php) y usa el
  primero que responda. Si el primario (Python) se cae, el sitio sigue mostrando
  libros desde NodeJS.
- `Prestamo` guarda `libro_id` suelto (sin ForeignKey): el título se pide al
  microservicio al renderizar.
- No existe modelo `Libro`, `Autor` ni `Categoria` en el ORM. `models.py` de
  `libros/` está vacío a propósito.

## Comandos

Cada servicio tiene su propio entorno virtual en su carpeta, y ninguno está
versionado (`.gitignore` excluye `venv/`, `db.sqlite3`, `.env` y `staticfiles/`).

El archivo `.env` de la raíz tiene la configuración local de **los dos** servicios.
Se carga en la shell con `set -a; . ../.env; set +a`.

La clave del **asistente con IA** va aparte, en `sitio/biblioteca/.env`, porque
`settings.py` la lee solo (no hace falta cargarla en la shell).

```bash
cd sitio
python3 -m venv venv                     # solo la primera vez
venv/bin/pip install -r requirements.txt

venv/bin/python manage.py check          # validar configuración
venv/bin/python manage.py test           # correr los tests (usan SQLite)
venv/bin/python manage.py runserver      # levantar en http://127.0.0.1:8000/
venv/bin/python manage.py makemigrations # tras tocar models.py
venv/bin/python manage.py migrate
venv/bin/python seed.py                  # datos de ejemplo (idempotente)
```

Para probar el CRUD de libros en local hay que levantar al menos el microservicio
Python (FastAPI, puerto 8001) y, si se quiere ver la resiliencia, el de NodeJS
(puerto 8002): el sitio cae a NodeJS cuando Python no responde.

Los comandos de Django hay que correrlos **desde `sitio/`**: el descubrimiento de
tests parte del directorio actual, y desde la raíz del repo no encuentra ninguno.

Los tests tienen que correr contra SQLite. Si `DATABASE_URL` está cargada en la
shell, Django crea una base de test en Supabase: lento y deja basura. Para
evitarlo: `env -u DATABASE_URL venv/bin/python manage.py test`.

Credenciales del admin que crea el seed: `admin` / `admin123`.

### Smoke test de las vistas

`ALLOWED_HOSTS` no incluye `testserver`, así que el `Client` de tests falla con
`DisallowedHost` si lo usás fuera de `manage.py test`. Para un smoke test manual
hay que parchearlo:

```python
from django.conf import settings
settings.ALLOWED_HOSTS = ["testserver"]
```

## Convenciones de código

### Vistas: siempre el patrón de tres pasos

Toda vista sigue esta estructura, sin excepciones. Es el patrón que el trabajo
práctico tiene que demostrar:

```python
def libros_por_categoria(request, categoria):
    """Una línea explicando qué hace la vista."""
    # 1. consumir los datos (del microservicio para libros)
    libros = [l for l in servicios.obtener_libros()[0].get("libros", [])
              if l.get("categoria") == categoria]

    # 2. armar el context como variable con nombre
    context = {
        "categoria": categoria,
        "libros": libros,
    }

    # 3. enviarlo al template
    return render(request, "libros/por_categoria.html", context)
```

Los libros ya no se leen con el ORM: vienen de un microservicio (Supabase) a
través de `libros/servicios.py`. El patrón de los tres pasos se mantiene: la
vista consume datos (por HTTP), arma el `context` y lo manda al template. Las
vistas de `prestamos` (Lector, Prestamo) sí siguen usando el ORM.

Reglas duras:

- **Vistas basadas en funciones.** No conviertas nada a Class-Based Views.
- **`context` siempre como variable nombrada**, nunca un dict inline dentro de
  `render()`. El patrón tiene que verse.
- **Usá los shortcuts**: `render()` y `get_object_or_404()`. Nada de `HttpResponse`
  crudo, `loader.get_template()` ni `raise Http404` a mano.
- **Docstring de una línea** por vista, en español.
- La lógica de negocio (cambiar `libro.disponible`, guardar fechas) va en la vista,
  nunca en el template.
- Toda llamada remota va en `try/except MicroservicioNoDisponible`: si el servicio
  se cae, la vista muestra un aviso o degrada, nunca un 500.

`get_object_or_404` es para buscar **un** objeto por PK en el ORM (Lector,
Prestamo). Para los libros del microservicio, el 404 lo decide el servicio:
`obtener_libro()` levanta `LibroNoEncontrado` cuando ninguno lo tiene.

### Templates: HTML plano, sin estilos

Se eliminó deliberadamente todo el CSS para que el proyecto se vea básico.

- **No agregues CSS, clases, `<style>`, frameworks ni JS.** Si te parece que "queda
  feo", así tiene que quedar.
- Todos los templates extienden `sitio/templates/base.html`.
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
vercel.json             define los dos servicios y el enrutado por dominio
.env                    configuración local de ambos (no se versiona)

sitio/                  SERVICIO 1 - el sitio web (Django)
  biblioteca/           configuración del proyecto (settings, urls raíz)
    .env                clave de la API de IA (no se versiona)
  libros/               app 1: modelos vacíos (los libros viven en Supabase) → 9 vistas
  prestamos/            app 2: Lector, Prestamo → 5 vistas
  templates/            base.html (compartido)
  requirements.txt      dependencias del sitio
  seed.py               datos de ejemplo, idempotente

microservicio_resenas/          SERVICIO 2 - CRUD de libros y reseñas (FastAPI/Python)
  main.py               endpoints, todos bajo /api
  requirements.txt      dependencias de la API
  schema.sql            tabla resenas en Supabase
  schema_libros.sql     tabla libros en Supabase

microservicio_resenas_nodejs/   SERVICIO 3 - el mismo CRUD en NodeJS (node:http, sin deps)
  server.js             endpoints, todos bajo /api

microservicio_resenas_java/     SERVICIO 4 - el mismo CRUD en Java (HttpServer del JDK)
  MicroservicioResenas.java  endpoints, todos bajo /api

microservicio_resenas_php/      SERVICIO 5 - el mismo CRUD en PHP (php -S, sin deps)
  router.php            endpoints, todos bajo /api
```

Cada app tiene su `urls.py` con `app_name` definido y se incluye desde
`sitio/biblioteca/urls.py` con `include()`.

## Al modificar el código

1. Corré `venv/bin/python manage.py check` y `venv/bin/python manage.py test`.
2. **El README referencia números de línea** (ej. `sitio/libros/views.py:32`). Si agregás o
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
- Toda llamada HTTP pasa por `sitio/libros/servicios.py`. Las vistas no arman URLs ni
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
| `MICROSERVICIO_RESENAS_FALLBACK_URL` | `http://127.0.0.1:8002` | la URL del servicio de respaldo |
| `MICROSERVICIO_LIBROS_{LENGUAJE}_URL` | `http://127.0.0.1:{puerto}` | URL del microservicio de ese lenguaje |
| `IA_API_KEY` | el asistente avisa que no hay clave | la IA responde preguntas del catálogo |

`IA_API_KEY` (y opcionalmente `IA_API_URL` e `IA_MODEL`) se leen de
`sitio/biblioteca/.env`, que `settings.py` parsea solo, sin dependencias. En
Vercel se cargan como variables de entorno: el archivo no se despliega.

Reglas:

- **No escribas credenciales en `settings.py`.** Van por variable de entorno.
- **No quites el fallback a SQLite.** Los tests y el desarrollo local dependen de él.
- `conn_max_age=0` es a propósito: cada invocación serverless es efímera, las
  conexiones persistentes no sobreviven y agotan el pool de Postgres.

## Despliegue

Son **dos aplicaciones separadas en un solo despliegue**, usando Vercel Services.
`vercel.json` las declara y las enruta bajo el mismo dominio:

| Servicio | Carpeta | Ruta pública | Entrypoint |
|---|---|---|---|
| `sitio` | `sitio/` | `/` | `manage.py` → `biblioteca/wsgi.py` |
| `api` | `microservicio_resenas/` | `/api` | `main:app` |

Detalles que importan:

- **Las carpetas son hermanas a propósito.** Una no puede contener a la otra:
  cada servicio se construye por separado desde su propia raíz.
- **El servicio recibe la ruta completa.** Una petición a `/api/salud` le llega a
  FastAPI como `/api/salud`, no como `/salud`. Por eso las rutas de `main.py`
  cuelgan de un `APIRouter(prefix="/api")`. Si sacás el prefijo, todo da 404.
- Vercel detecta Django por `manage.py`, resuelve el entrypoint desde
  `WSGI_APPLICATION` y corre `collectstatic` solo porque `STATIC_ROOT` está
  definido. No hace falta build command.
- Django deduce la URL de la API desde `VERCEL_URL`: comparten dominio, así que no
  hay que configurar nada.

### Variables que hay que cargar en Vercel

Settings → Environment Variables, en Production, Preview y Development:

| Variable | Valor |
|---|---|
| `DATABASE_URL` | connection string del **Session pooler** de Supabase |
| `DJANGO_SECRET_KEY` | clave generada con `get_random_secret_key()` |
| `DJANGO_DEBUG` | `False` |
| `SUPABASE_URL` | Project URL de Supabase |
| `SUPABASE_SERVICE_KEY` | la `service_role` key, no la `anon` |
| `IA_API_KEY` | la clave de Google AI Studio (opcional: sin ella, el asistente avisa que no hay clave) |

`MICROSERVICIO_RESENAS_URL` **no se carga**: Django la deduce del dominio del
proyecto. Solo se define para apuntar a un servicio distinto.

La `IA_API_KEY` se lee de una variable de entorno en Vercel: el archivo
`sitio/biblioteca/.env` no se despliega. Sin la variable, el asistente muestra
un aviso en vez de fallar; el resto del sitio no se entera.

La connection string tiene que ser la del **Session pooler**
(`aws-0-*.pooler.supabase.com`). La conexión directa (`db.*.supabase.co`) es
IPv6 y Vercel no la alcanza: falla con un timeout que no dice nada.

## Despliegue: problemas conocidos

Esta sección existe porque cada uno de estos costó horas. Leela antes de
diagnosticar un despliegue roto.

### La URL no cambia pase lo que pase → mirá los alias, no el código

**El síntoma más caro de todos.** Un build puede quedar `Ready` y aun así no
servirse: los alias siguen apuntando al deployment anterior. La URL devuelve
exactamente lo mismo aunque cambies el código veinte veces, porque estás viendo
una versión vieja.

```bash
vercel alias ls | rg django-project      # ¿a qué deployment apuntan?
vercel promote <url-del-deployment> --yes
```

Regla: **si algo no cambia _nunca_ después de varios intentos, dejá de mirar el
código y fijate qué versión está sirviendo el servidor.**

### Builds colgados en `Initializing`

Los builds disparados por Git se cuelgan en `Initializing` de forma indefinida.
Los lanzados por CLI arrancan en segundos.

En el plan Hobby hay **un solo build concurrente**: uno trabado bloquea la cola
entera y todo lo que pushees después queda en `Queued` sin construir. El mensaje
es `Another build is in progress`.

```bash
vercel ls django-project                 # buscar Initializing o Queued
vercel remove <url-trabada> --yes        # destrabar la cola
vercel --prod --yes                      # desplegar por CLI
```

### El error real está en los logs de runtime, no en el HTTP

`FUNCTION_INVOCATION_FAILED` con 500 en **todas** las rutas, incluida una que no
toca la base ni la red, significa que el módulo explota **al importarse**. No es
un problema de ninguna ruta en particular: casi siempre es una variable de
entorno que falta.

Desde afuera todos los 500 se ven iguales. Los logs de runtime del panel (o
`vercel inspect <url>`) dicen la excepción exacta. Sin eso se diagnostica a
ciegas y se pierden horas.

### Qué archivo atiende cada ruta delata la configuración

Si en los logs ves que `/` y `/libro/1/` los atiende `main.py`, el Root Directory
del proyecto está mal: apunta a `microservicio_resenas` y Django ni se despliega.
Con Services, el Root Directory del panel tiene que estar **vacío**, porque el
`vercel.json` de la raíz es el que manda.

Cuidado con la palabra "root", que significa dos cosas distintas:

| Dónde | Valor |
|---|---|
| Panel de Vercel → Root Directory | **vacío** |
| `vercel.json` → `services.sitio.root` | `sitio/` |
| `vercel.json` → `services.api.root` | `microservicio_resenas/` |

### `VERCEL_URL` está protegida, usá `VERCEL_PROJECT_PRODUCTION_URL`

`VERCEL_URL` apunta al deployment concreto, que está detrás de Deployment
Protection: pedirle JSON devuelve un 302 a la página de login SSO. La vista lo
interpreta como servicio caído y muestra el aviso de degradación.

`VERCEL_PROJECT_PRODUCTION_URL` es el dominio público y estable. Es la que usa
`settings.py`.

### El `.env` necesita comillas simples

La `SECRET_KEY` de Django trae paréntesis y símbolos que rompen la shell al
hacer `. ./.env`, con un `parse error` que no dice cuál es la línea. Todos los
valores van entre comillas simples. En Vercel, en cambio, se pega el valor
**sin** comillas.

### No confíes en la documentación del repo sin verificarla

Este archivo llegó a afirmar que `venv/` y `db.sqlite3` estaban versionados.
Los dos eran falsos: el `.gitignore` los excluye. Antes de repetir lo que dice
un doc, comprobalo:

```bash
git ls-files | wc -l
git check-ignore -v venv db.sqlite3
```
