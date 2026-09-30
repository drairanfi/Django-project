# Microservicio de Reseñas (Java)

Replica en **Java** del microservicio de reseñas original que vive en
[`../microservicio_resenas`](../microservicio_resenas) (Python/FastAPI). Expone
la misma API HTTP sobre la misma tabla de **Supabase**, pero como servicio
autónomo: no comparte base de datos ni código con Django.

```
Navegador ──► Django (SQLite, local)
                 └─ vista resenas_libro() ──HTTP──► este microservicio (Java)
                                                       └── Supabase (PostgreSQL)
```

## Stack

| Componente | Versión |
|---|---|
| Java | OpenJDK 27 |
| Servidor HTTP | `com.sun.net.httpserver` (del JDK) |
| Cliente HTTP | `java.net.http.HttpClient` (del JDK) |
| Base de datos | Supabase (PostgreSQL), vía API REST PostgREST |

Sin Maven, sin Gradle, sin frameworks y sin driver JDBC: el acceso a la tabla se
hace por la **API REST PostgREST** de Supabase con la `service_role` key. Todo el
servidor vive en un solo archivo `.java` que corre con la ejecución de fuente
única del JDK.

## Endpoints

Todas las rutas cuelgan de `/api` (en el despliegue el servicio recibe la ruta
completa con `/api` incluido).

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/api/salud` | Health check: `{"estado": "ok"}` |
| GET | `/api/resenas` | Todas las reseñas, ordenadas por `creada_en` descendente |
| GET | `/api/libros/{libro_id}/resenas` | Reseñas de un libro + promedio (el que consume Django) |
| POST | `/api/resenas` | Crea una reseña (201) |
| PATCH | `/api/resenas/{id}` | Actualiza `lector`, `puntaje` o `comentario` |
| DELETE | `/api/resenas/{id}` | Borra una reseña |
| GET | `/api/libros` | Todos los libros, ordenados por `creada_en` descendente |
| GET | `/api/libros/{id}` | Un libro por id, o 404 |
| POST | `/api/libros` | Crea un libro (201) |
| PUT | `/api/libros/{id}` | Actualiza campos del libro, o 404 si no existe |
| DELETE | `/api/libros/{id}` | Borra un libro y lo devuelve, o 404 si no existe |

El CRUD de libros usa la tabla `libros` de Supabase con columnas `id`, `titulo`,
`isbn`, `anio_publicacion`, `paginas`, `disponible` y `categoria`. En el `POST`
son obligatorios `titulo` e `isbn` (no vacíos); el resto es opcional y toma los
defaults de la base (`disponible` true, `categoria` '', años/páginas null). El
`PUT` acepta cualquier subconjunto de esos campos y un `null` explícito en
`anio_publicacion`, `paginas` o `categoria` los limpia. Las validaciones
responden **422** y si el id no existe responden **404** con
`{"detail": "no encontrado"}`.

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

`promedio` es un float redondeado a 2 decimales si hay reseñas, o `null` si no
las hay. El `POST` valida: `libro_id >= 1`, `lector` no vacío y de hasta 100
caracteres, `puntaje` entre 1 y 5; si algo falla responde **422** con
`{"detail": "mensaje claro"}`. Cualquier error contra Supabase responde **502**
con `{"detail": "Error de Supabase: <error>"}`, sin matar al servidor.

## Correrlo en local

El servicio necesita dos variables de entorno para arrancar:

| Variable | Qué es |
|---|---|
| `SUPABASE_URL` | Project URL de tu proyecto Supabase |
| `SUPABASE_SERVICE_KEY` | la `service_role` key, no la `anon` |

Si falta alguna, imprime un mensaje claro y sale con código de error. El puerto
se elige con `PORT` (por defecto **8003**, distinto del 8001 del original para
poder correr ambos a la vez).

```bash
cd microservicio_resenas_java
cp .env.example .env        # y completá los dos valores de Supabase

set -a; . ./.env; set +a   # exporta lo del .env en la shell

/Users/daniel.rairan/.homebrew/opt/openjdk/bin/java MicroservicioResenas.java
```

También podés exportar las variables a mano en vez de usar el archivo:

```bash
export SUPABASE_URL="https://tu-proyecto.supabase.co"
export SUPABASE_SERVICE_KEY="tu-service-role-key"
export PORT=8003
java MicroservicioResenas.java
```

El servidor queda escuchando en `http://127.0.0.1:8003/api`. Comprobalo:

```bash
curl http://127.0.0.1:8003/api/salud
# {"estado":"ok"}
```

`.env` está en el `.gitignore`: la `service_role` key nunca se versiona. Los
archivos `.class` tampoco se versionan (la ejecución de fuente única no genera
ninguno, pero quedan excluidos por si se compila con `javac`).

## Nota sobre la tabla

Este servicio comparte la tabla `resenas` de Supabase con el microservicio de
Python (`../microservicio_resenas`). Ambos usan la misma `service_role` key y
escriben y leen los mismos datos: son dos implementaciones del mismo contrato,
no dos bases distintas.

El CRUD de `libros` también escribe en Supabase (tabla `libros`), pero ese
endpoint es exclusivo de esta versión en Java: el microservicio de Python no
tiene endpoints de libros.