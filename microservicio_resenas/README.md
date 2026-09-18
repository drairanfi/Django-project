# Microservicio de Reseñas

API HTTP propia que guarda las reseñas de los libros en **Supabase**
(PostgreSQL administrado). La app Django la consume por HTTP: no comparte base
de datos ni código con ella.

```
Navegador ──► Django (SQLite, local)
                 └─ vista resenas_libro() ──HTTP──► este microservicio (Render)
                                                       └── Supabase (PostgreSQL)
```

## Stack

| Componente | Versión |
|---|---|
| Python | 3.12 |
| FastAPI | 0.141.1 |
| uvicorn | 0.53.0 |
| supabase (cliente) | 2.31.0 |

## Endpoints

| Método | Ruta | Qué hace |
|---|---|---|
| GET | `/` | Describe el servicio |
| GET | `/salud` | Health check que usa Render |
| GET | `/resenas` | Todas las reseñas |
| GET | `/libros/{libro_id}/resenas` | Reseñas de un libro + promedio — **el que consume Django** |
| POST | `/resenas` | Crea una reseña |

Ejemplo de respuesta de `GET /libros/1/resenas`:

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

FastAPI genera la documentación interactiva sola: `/docs`.

## Paso 1 — Crear la base en Supabase

1. Entrá a [supabase.com](https://supabase.com), creá un proyecto (plan free).
2. Andá a **SQL Editor**, pegá el contenido de [`schema.sql`](schema.sql) y ejecutalo.
3. Andá a **Settings → API** y copiá dos valores:
   - **Project URL** → `SUPABASE_URL`
   - **service_role key** (la secreta, no la `anon`) → `SUPABASE_SERVICE_KEY`

> La tabla tiene **RLS activado y sin políticas públicas**: con la clave `anon`
> nadie lee ni escribe. Solo este microservicio, que usa la `service_role` key
> guardada como variable de entorno, puede tocar los datos. Por eso esa clave
> **nunca** va al repo ni al código de Django.

## Paso 2 — Probarlo local

```bash
cd microservicio_resenas
python3 -m venv venv
venv/bin/pip install -r requirements.txt

cp .env.example .env        # y completá los dos valores de Supabase
```

Las credenciales se leen de variables de entorno, no del archivo `.env`: en
Render no hay `.env`, las inyecta la plataforma. Para que el shell las cargue
desde el archivo en local:

```bash
set -a; . ./.env; set +a                             # exporta todo lo del .env

venv/bin/python seed.py                              # datos de ejemplo (idempotente)
venv/bin/uvicorn main:app --reload --port 8001       # http://127.0.0.1:8001/docs
```

`.env` está en el `.gitignore`: la `service_role` key nunca se versiona.

El puerto 8001 es el que Django usa por defecto en local (`MICROSERVICIO_RESENAS_URL`).

## Paso 3 — Desplegar en Render

1. Subí el repo a GitHub.
2. En [render.com](https://render.com): **New → Web Service** → conectá el repo.
3. Configuración:

   | Campo | Valor |
   |---|---|
   | Root Directory | `microservicio_resenas` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn main:app --host 0.0.0.0 --port $PORT` |
   | Health Check Path | `/salud` |
   | Instance Type | Free |

4. En **Environment** cargá `SUPABASE_URL` y `SUPABASE_SERVICE_KEY`.
5. Deploy. Render te da una URL tipo `https://microservicio-resenas.onrender.com`.

El archivo [`../render.yaml`](../render.yaml) tiene esta misma configuración como
Blueprint: si usás **New → Blueprint**, Render la lee y solo te pide las dos
credenciales.

## Paso 4 — Apuntar Django al servicio desplegado

```bash
export MICROSERVICIO_RESENAS_URL="https://microservicio-resenas.onrender.com"
venv/bin/python manage.py runserver
```

Entrá a un libro y seguí el link **"Ver reseñas (microservicio externo)"**.

## Detalle del plan free de Render

El servicio se **duerme tras 15 minutos sin tráfico** y el primer request luego
puede tardar ~30-50 segundos en despertarlo. Django tiene un timeout de 5
segundos (`MICROSERVICIO_RESENAS_TIMEOUT`), así que la primera carga puede
mostrar el mensaje de "microservicio no disponible" y funcionar al recargar.
Antes de mostrar el trabajo, abrí la URL del servicio una vez para despertarlo.
