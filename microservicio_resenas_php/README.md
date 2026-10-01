# Microservicio de Reseñas y Libros en PHP

Réplica del microservicio de reseñas (`microservicio_resenas/`, Python/FastAPI)
escrita en **PHP puro**: sin Composer, sin frameworks, sin librerías de terceros.
Además del contrato original de reseñas, expone un CRUD completo de la tabla
`libros`.

Guarda los datos en **Supabase** (PostgreSQL en la nube), en las **mismas tablas
`resenas` y `libros`** que el microservicio de Python: ambos servicios comparten
los datos, ninguno se conecta con PDO. Accede por la **API REST PostgREST** de
Supabase usando la `service_role` key.

```
Navegador ──► Django (SQLite, local)
                 └─ vista resenas_libro() ──HTTP──► este microservicio (PHP)
                                                       └── Supabase (PostgreSQL)
```

## Stack

| Componente | Detalle |
|---|---|
| PHP | 8.5 (servidor embebido `php -S`) |
| Composer | No |
| Frameworks | No |
| HTTP saliente | `file_get_contents` con `stream_context_create` |
| Base de datos | Supabase (PostgreSQL), vía API REST PostgREST |

## Endpoints

### Reseñas

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/salud` | Health check → `{"estado": "ok"}` |
| GET | `/api/docs` | Swagger UI: documentación interactiva del contrato completo |
| GET | `/api/openapi.json` | La spec OpenAPI 3.0 (`openapi.json`), que Swagger UI consume |
| GET | `/api/resenas` | Todas las reseñas, ordenadas por `creada_en` descendente |
| GET | `/api/libros/{libro_id}/resenas` | Reseñas de un libro + promedio (redondeado a 2 decimales, o `null`) |
| POST | `/api/resenas` | Crea una reseña (status 201). Validación: `libro_id >= 1`, `lector` no vacío y ≤ 100 caracteres, `puntaje` 1..5, `comentario` opcional |
| PATCH | `/api/resenas/{id}` | Actualiza `lector`, `puntaje` y/o `comentario` |
| DELETE | `/api/resenas/{id}` | Borra la reseña y devuelve la fila borrada |

### Libros

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/libros` | Todos los libros, ordenados por `creada_en` descendente |
| GET | `/api/libros/{id}` | Un libro puntual, o 404 `{"detail": "Ruta no encontrada"}` |
| POST | `/api/libros` | Crea un libro (status 201). Validación: `titulo` e `isbn` no vacíos; `anio_publicacion` y `paginas` enteros o `null`; `disponible` booleano (default `true`); `categoria` texto (default `''`) |
| PUT | `/api/libros/{id}` | Actualiza con cualquier subconjunto de `{titulo, isbn, anio_publicacion, paginas, disponible, categoria}`. 404 si el id no existe |
| DELETE | `/api/libros/{id}` | Borra el libro y devuelve la fila borrada. 404 si el id no existe |

`GET /api/docs` abre **Swagger UI** (CDN de unpkg, sin Composer), que carga la
spec `openapi.json` desde `/api/openapi.json` y documenta el **contrato completo**:
salud, CRUD de libros y CRUD de reseñas.

Ejemplo de respuesta de `GET /api/libros/1/resenas`:

```json
{
  "libro_id": 1,
  "cantidad": 2,
  "promedio": 4.5,
  "resenas": [
    {
      "id": 1,
      "libro_id": 1,
      "lector": "Ana Gómez",
      "puntaje": 5,
      "comentario": "Imperdible, lo leí dos veces.",
      "creada_en": "2026-09-18T10:00:00+00:00"
    }
  ]
}
```

Errores de validación devuelven **422** con `{"detail": "mensaje claro"}`. Un
fallo de Supabase devuelve **502** con `{"detail": "Error de Supabase: <error>"}`,
igual que el original en Python. Nunca se corta el servidor.

## Cómo correrlo local

Las credenciales se leen de variables de entorno, nunca del código. En local
cargalas desde `.env` en la shell y levantá el servidor embebido:

```bash
cd microservicio_resenas_php
cp .env.example .env      # y completá SUPABASE_URL y SUPABASE_SERVICE_KEY

set -a; . ./.env; set +a  # exporta las variables del .env

php -S 127.0.0.1:8004 router.php
```

También podés exportarlas a mano si preferís:

```bash
export SUPABASE_URL="https://xxxx.supabase.co"
export SUPABASE_SERVICE_KEY="eyJhbGciOi..."
php -S 127.0.0.1:8004 router.php
```

El puerto se cambia con la variable `PORT` (default `8004`). En el despliegue
el servicio recibe la ruta completa con `/api` incluido, por eso todas las rutas
cuelgan de `/api` también en local.

Probá el health check:

```bash
curl http://127.0.0.1:8004/api/salud
# {"estado":"ok"}
```

> `.env` está en el `.gitignore`: la `service_role` key nunca se versiona.
> Sin `SUPABASE_URL` o `SUPABASE_SERVICE_KEY` el servicio responde **500** con un
> mensaje claro y avisa por consola.

## Base de datos

Comparte las tablas `resenas` y `libros` de Supabase con el microservicio de
Python (`microservicio_resenas/`). El esquema de `resenas` (`schema.sql`) vive
en ese repo hermano:

| Columna | Tipo |
|---|---|
| `id` | bigint identity PK |
| `libro_id` | int |
| `lector` | text |
| `puntaje` | int 1..5 |
| `comentario` | text, default `''` |
| `creada_en` | timestamptz, default `now()` |

Tabla `libros`:

| Columna | Tipo |
|---|---|
| `id` | bigint identity PK |
| `titulo` | text not null |
| `isbn` | text not null unique |
| `anio_publicacion` | int, nullable |
| `paginas` | int, nullable |
| `disponible` | boolean, default `true` |
| `categoria` | text, default `''` |
| `creada_en` | timestamptz, default `now()` |

RLS está activado y sin políticas públicas: solo la `service_role` key
(atraviesa RLS) puede leer y escribir. Por eso esa clave **nunca** va al repo.

## Desplegar en Vercel

Esta carpeta es un proyecto Vercel aparte. El entrypoint serverless es
`api/index.php`, que incluye `router.php`; el `vercel.json` usa el runtime
comunitario `vercel-php@0.6.2` y manda `/api/*` a ese archivo.

1. Vercel → **Add New → Project** → elegí este repo.
2. **Root Directory** → `microservicio_resenas_php`.
3. Environment Variables (Production, Preview, Development):
   - `SUPABASE_URL`
   - `SUPABASE_SERVICE_KEY`
4. Deploy y verificá:

```bash
curl https://tu-php.vercel.app/api/salud
curl https://tu-php.vercel.app/api/docs   # Swagger UI
```

> Para que el sitio Django lo use como respaldo en la lectura de libros, cargá
> la URL en el proyecto Vercel del sitio como `MICROSERVICIO_LIBROS_PHP_URL`
> (ver [`COMO_ARRANCAR.md`](../COMO_ARRANCAR.md)).

> Ojo: `vercel-php` es un runtime de la comunidad, no soporte oficial de Vercel.
> Si el build falla, revisá el log: puede cambiar entre versiones.