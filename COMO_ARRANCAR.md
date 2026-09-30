# Cómo arrancar cada servicio

Este repo tiene 5 procesos que se levantan por separado: el sitio Django y los
4 microservicios de libros/reseñas (Python, NodeJS, Java y PHP).

## Puertos

| Servicio | Carpeta | Puerto | Lenguaje |
|---|---|---|---|
| Sitio Django | `sitio/` | 8000 | Python |
| Microservicio primario | `microservicio_resenas/` | 8001 | Python (FastAPI) |
| Microservicio respaldo 1 | `microservicio_resenas_nodejs/` | 8002 | NodeJS |
| Microservicio respaldo 2 | `microservicio_resenas_java/` | 8003 | Java |
| Microservicio respaldo 3 | `microservicio_resenas_php/` | 8004 | PHP |

El sitio habla con los microservicios por HTTP (ver `sitio/biblioteca/settings.py`
→ `MICROSERVICIOS_LIBROS`). En local las URLs apuntan a estos puertos.

## Antes de arrancar

Cada microservicio lee `SUPABASE_URL` y `SUPABASE_SERVICE_KEY` de su `.env`
(no se versiona). El `.env` se carga en la shell con:

```bash
set -a; . ./.env; set +a
```

> Los 4 microservicios usan la MISMA base de Supabase (tablas `resenas` y
> `libros`). Si la tabla `libros` no existe todavía, corré
> `microservicio_resenas/schema_libros.sql` en el SQL Editor de Supabase.

## Arrancar el sitio Django (puerto 8000)

```bash
cd sitio
../venv/bin/python manage.py migrate      # solo la primera vez
../venv/bin/python seed.py                # solo la primera vez (carga libros en Supabase)
../venv/bin/python manage.py runserver    # http://127.0.0.1:8000/
```

## Arrancar el microservicio Python (puerto 8001)

```bash
cd microservicio_resenas
set -a; . ./.env; set +a
python3 -m venv venv                      # solo la primera vez
venv/bin/pip install -r requirements.txt  # solo la primera vez
venv/bin/python -m uvicorn main:app --port 8001
```

## Arrancar el microservicio NodeJS (puerto 8002)

```bash
cd microservicio_resenas_nodejs
set -a; . ./.env; set +a
node server.js
```

## Arrancar el microservicio Java (puerto 8003)

El openjdk de Homebrew es *keg-only*: no queda en el PATH solo. Una vez por
máquina hay que agregarlo:

```bash
echo 'export PATH="/Users/daniel.rairan/.homebrew/opt/openjdk/bin:$PATH"' >> ~/.zshrc
source ~/.zshrc
```

Después, a arrancar:

```bash
cd microservicio_resenas_java
set -a; . ./.env; set +a
java MicroservicioResenas.java            # requiere OpenJDK 21+ (la ejecución de fuente única)
```

## Arrancar el microservicio PHP (puerto 8004)

```bash
cd microservicio_resenas_php
set -a; . ./.env; set +a
php -S 127.0.0.1:8004 router.php
```

## Resiliencia: si se cae uno, sigue otro

La lectura del catálogo (`inicio`, detalle, por categoría/autor) no depende de
un solo servicio. `servicios.obtener_libros()` recorre este orden y usa el
primero que responda:

```python
# sitio/biblioteca/settings.py
MICROSERVICIOS_LIBROS_ORDEN_LECTURA = ["python", "nodejs", "java", "php"]
```

Es decir: **con el de Python levantado alcanza**, pero si se cae, el sitio pasa
solo a NodeJS; si ese también, a Java; y así. Por eso conviene levantar los 4:
así el sitio nunca se queda sin datos aunque caigan varios.

### La forma más simple

1. Arrancá el sitio (8000) y el microservicio Python (8001). El sitio funciona.
2. Si querés ver la resiliencia, arrancá también el NodeJS (8002), después
   matá el Python (Ctrl+C o `kill`), y recargá el catálogo: sigue mostrando los
   libros, ahora con `Datos servidos por el microservicio: nodejs`.

### Cómo saber cuál está sirviendo

En `inicio` y `detalle_libro` el template muestra qué microservicio respondió
(`servicio_origen`). Si el primario está caído, ahí dice `nodejs` en vez de
`python`.

### Nota sobre el arranque simultáneo

Cada comando ocupa una terminal (bloquea mientras corre). Si preferís uno solo,
levantá el sitio y el Python en terminales separadas y listo; los otros tres son
opcionales y solo se necesitan cuando querés ver el failover.

## Desplegar los microservicios en Vercel

Vercel soporta los runtimes de **Node.js** y **PHP** (este último con un runtime
comunitario). **Java no se puede desplegar en Vercel** (no existe runtime). Los
microservicios de NodeJS y PHP ya tienen su `vercel.json` y su entrypoint
(`api/index.js` y `api/index.php`) listos para desplegarse como proyectos
separados.

### NodeJS (recomendado)

1. Entrá a [vercel.com](https://vercel.com) → **Add New → Project** y elegí este
   repo.
2. **Root Directory** → `microservicio_resenas_nodejs` (así Vercel usa el
   `vercel.json` de esa carpeta).
3. Environment Variables → Production, Preview, Development:
   - `SUPABASE_URL` → tu Project URL
   - `SUPABASE_SERVICE_KEY` → tu service_role key
4. Deploy. Te da una URL tipo `https://tu-node.vercel.app`. Verificá:

```bash
curl https://tu-node.vercel.app/api/salud
# {"estado":"ok"}
curl https://tu-node.vercel.app/api/libros
```

### PHP (runtime comunitario)

Igual que arriba pero Root Directory → `microservicio_resenas_php`. Ojo: el
runtime `vercel-php@0.5.2` es de la comunidad (no soporte oficial de Vercel);
si el build falla, revisá el log, porque puede cambiar entre versiones.

### Apuntar el sitio a los servicios desplegados

En el proyecto de Vercel del **sitio** (Django), Settings → Environment
Variables, cargá las URLs de los microservicios:

| Variable | Valor |
|---|---|
| `MICROSERVICIO_LIBROS_NODEJS_URL` | `https://tu-node.vercel.app/api` |
| `MICROSERVICIO_LIBROS_PHP_URL` | `https://tu-php.vercel.app/api` |
| `MICROSERVICIO_LIBROS_JAVA_URL` | la URL donde desplegues Java (Render, p. ej.) |

Con eso la resiliencia pasa a producción: si el Python (que ya está en el mismo
deploy del sitio) se cae, el sitio cae a NodeJS desplegado.