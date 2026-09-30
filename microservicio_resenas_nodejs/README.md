# Microservicio de Reseñas y Libros (NodeJS)

Versión en **NodeJS** del microservicio de reseñas del trabajo práctico. Es un
servicio autónomo que expone una API HTTP sobre las tablas `resenas` y `libros`
de **Supabase** (PostgreSQL administrado), accedidas por su API REST PostgREST
con la `service_role` key. La app Django la consume por HTTP: no comparte base
de datos ni código con ella.

```
Navegador ──► Django (SQLite, local)
                 └─ vista resenas_libro() ──HTTP──► este microservicio
                                                        └── Supabase (PostgreSQL)
```

Existe una versión equivalente en Python/FastAPI en `microservicio_resenas/`.
**Ambos servicios comparten la misma tabla `resenas` de Supabase**: lo que uno
escribe, el otro lo lee. Esta versión replica el mismo contrato HTTP (y agrega
el CRUD de libros), sin dependencias externas.

## Stack

| Componente | Versión |
|---|---|
| NodeJS | 20+ (`node:http` y `fetch` global) |
| Dependencias | ninguna (sin npm install) |

## Endpoints

Todas las rutas cuelgan de `/api` porque el servicio comparte dominio con el
sitio Django: en el despliegue Vercel enruta por prefijo y le entrega al
servicio la ruta completa, con `/api` incluido.

### Reseñas

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/salud` | Health check de la plataforma |
| GET | `/api/resenas` | Todas las reseñas, ordenadas por `creada_en` descendente |
| GET | `/api/libros/{libro_id}/resenas` | Reseñas de un libro + promedio — **el que consume Django** |
| POST | `/api/resenas` | Crea una reseña (status 201) |
| PATCH | `/api/resenas/{id}` | Actualiza `lector`, `puntaje` y/o `comentario` |
| DELETE | `/api/resenas/{id}` | Borra la reseña |

### Libros (CRUD)

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/libros` | Todos los libros, ordenados por `creada_en` descendente |
| GET | `/api/libros/{id}` | Un libro puntual (404 si no existe) |
| POST | `/api/libros` | Crea un libro (status 201) |
| PUT | `/api/libros/{id}` | Actualiza cualquier subconjunto de campos (404 si no existe) |
| DELETE | `/api/libros/{id}` | Borra el libro y devuelve la fila (404 si no existe) |

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

### POST `/api/resenas`

Body:

```json
{
  "libro_id": 1,
  "lector": "Ana Gómez",
  "puntaje": 5,
  "comentario": "Imperdible, lo leí dos veces."
}
```

Validaciones: `libro_id` entero >= 1, `lector` texto no vacío de hasta 100
caracteres, `puntaje` entero entre 1 y 5. `comentario` es opcional (default
`""`). Si algo falta o está mal, responde **422** con `{"detail": "mensaje"}`.

### POST `/api/libros`

Body:

```json
{
  "titulo": "Cien años de soledad",
  "isbn": "978-3-16-148410-0",
  "anio_publicacion": 1967,
  "paginas": 471,
  "disponible": true,
  "categoria": "Novela"
}
```

Validaciones: `titulo` y `isbn` texto no vacío. `anio_publicacion` y `paginas`
son enteros opcionales (aceptan `null`), `disponible` booleano opcional (default
`true`) y `categoria` texto opcional (default `""`). Si algo falta o está mal,
responde **422** con `{"detail": "mensaje"}`. `PUT /api/libros/{id}` acepta
cualquier subconjunto de esos campos.

Ante un error de Supabase (red, autenticación) responde **502** con
`{"detail": "Error de Supabase: <error>"}`. Las rutas desconocidas responden
**404** con `{"detail": "no encontrado"}`. El proceso nunca crashea.

## Correrlo local

Las credenciales se leen de variables de entorno, no del archivo `.env`: en el
despliegue las inyecta la plataforma. Para que el shell las cargue desde el
archivo en local:

```bash
cd microservicio_resenas_nodejs
cp .env.example .env        # y completá los dos valores de Supabase
```

`SUPABASE_URL` es el **Project URL** y `SUPABASE_SERVICE_KEY` la `service_role`
key (la secreta, no la `anon`) de **Settings → API** en Supabase. `.env` está en
el `.gitignore`: la clave nunca se versiona.

```bash
set -a; . ./.env; set +a    # exporta todo lo del .env

node server.js              # http://127.0.0.1:8002/api/salud
```

El puerto por defecto es **8002** (distinto del 8001 del microservicio de
Python, para poder correr ambos a la vez). Se cambia con `PORT`:

```bash
PORT=9000 node server.js
```

Sin variables de entorno el servicio **no arranca** y avisa con un mensaje
claro: es preferible fallar al inicio y no en medio de un request.

## Probar la API

```bash
curl http://127.0.0.1:8002/api/salud
# {"estado":"ok"}

curl http://127.0.0.1:8002/api/resenas
curl http://127.0.0.1:8002/api/libros/1/resenas

curl -X POST http://127.0.0.1:8002/api/resenas \
  -H "Content-Type: application/json" \
  -d '{"libro_id": 1, "lector": "Ana Gómez", "puntaje": 5}'
```

## Notas

- Sin `npm install`, sin `node_modules`: solo `node:http` y el `fetch` global
  de Node 20.
- Comparte la tabla `resenas` de Supabase con el microservicio de Python en
  `microservicio_resenas/`. No toca Django ni el `vercel.json`.