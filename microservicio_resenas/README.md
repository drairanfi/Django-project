# Microservicio de Reseñas

API HTTP propia que guarda las reseñas de los libros en **Supabase**
(PostgreSQL administrado). La app Django la consume por HTTP: no comparte base
de datos ni código con ella.

```
Navegador ──► Django (SQLite, local)
                 └─ vista resenas_libro() ──HTTP──► este microservicio (Vercel)
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
| GET | `/salud` | Health check de la plataforma |
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
Vercel no hay `.env`, las inyecta la plataforma. Para que el shell las cargue
desde el archivo en local:

```bash
set -a; . ./.env; set +a                             # exporta todo lo del .env

venv/bin/python seed.py                              # datos de ejemplo (idempotente)
venv/bin/uvicorn main:app --reload --port 8001       # http://127.0.0.1:8001/docs
```

`.env` está en el `.gitignore`: la `service_role` key nunca se versiona.

El puerto 8001 es el que Django usa por defecto en local (`MICROSERVICIO_RESENAS_URL`).

## Paso 3 — Desplegar en Vercel

Vercel detecta FastAPI solo: busca un entrypoint (`main.py` con un objeto `app`)
y un `requirements.txt`, y compila todo en **una sola función**.

La clave es que el proyecto de Vercel apunte a esta carpeta, **no a la raíz del
repo**. En la raíz está `manage.py`, y si Vercel lo ve intenta desplegar Django
—que acá no se despliega, corre local contra SQLite— y el build falla con:

```
Failed to read Django application settings from /vercel/path0/manage.py
ModuleNotFoundError: No module named 'django'
```

Configuración del proyecto en Vercel:

| Ajuste | Dónde | Valor |
|---|---|---|
| Root Directory | Settings → Build & Deployment | `microservicio_resenas` |
| SUPABASE_URL | Settings → Environment Variables | tu Project URL |
| SUPABASE_SERVICE_KEY | Settings → Environment Variables | tu `service_role` key |

Las dos variables van marcadas para **Production, Preview y Development**.
`main.py` las lee al importar el módulo: si falta una, la función no arranca.

Después, **Redeploy**. Vercel te da una URL tipo
`https://tu-proyecto.vercel.app`. Verificala:

```bash
curl https://tu-proyecto.vercel.app/salud
# {"estado":"ok"}
```

### Alternativa: Render

[`../render.yaml`](../render.yaml) deja el mismo servicio listo para Render
(**New → Blueprint**), con `rootDir: microservicio_resenas`, build
`pip install -r requirements.txt` y start
`uvicorn main:app --host 0.0.0.0 --port $PORT`.

Diferencia práctica: en Render el plan free **duerme el servicio tras 15 minutos**
sin tráfico y el primer request tarda 30-50 segundos —más que el timeout de 5
segundos de Django, así que la primera carga muestra el aviso de "microservicio
no disponible". En Vercel no pasa: el cold start es de uno o dos segundos.

## Paso 4 — Apuntar Django al servicio desplegado

```bash
export MICROSERVICIO_RESENAS_URL="https://tu-proyecto.vercel.app"
venv/bin/python manage.py runserver
```

Entrá a un libro y seguí el link **"Ver reseñas (microservicio externo)"**.
