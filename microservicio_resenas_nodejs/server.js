// Microservicio de reseñas y libros en NodeJS.
//
// Expone una API HTTP sobre las tablas `resenas` y `libros` de Supabase
// (PostgreSQL en la nube). No usa driver de Postgres: accede a Supabase por su
// API REST PostgREST con la service_role key. Django NO habla con esta base de
// datos: habla con esta API por HTTP.
//
// Sin dependencias externas: solo node:http y el fetch global (Node 20).

import http from "node:http";

const TABLA = "resenas";
const TABLA_LIBROS = "libros";

function variable_obligatoria(nombre) {
  // Lee una variable de entorno obligatoria y falla con un mensaje legible si falta.
  const valor = process.env[nombre];
  if (!valor) {
    console.error(
      `Falta la variable de entorno ${nombre}. ` +
        "Cargala en el panel de la plataforma de despliegue, " +
        "o en el archivo .env si estás corriendo local.",
    );
    process.exit(1);
  }
  return valor;
}

// Las credenciales llegan por variables de entorno. Nunca se escriben en el
// código. Si falta alguna, el servicio no arranca: es preferible fallar al
// inicio y no en medio de un request.
const SUPABASE_URL = variable_obligatoria("SUPABASE_URL");
const SUPABASE_SERVICE_KEY = variable_obligatoria("SUPABASE_SERVICE_KEY");
const BASE_SUPABASE = `${SUPABASE_URL}/rest/v1`;
const PUERTO = process.env.PORT || 8002;

// Cabeceras que exige PostgREST en TODA llamada. Content-Type solo va cuando
// el request lleva body.
function cabeceras(conBody = false) {
  const cabeceras = {
    apikey: SUPABASE_SERVICE_KEY,
    Authorization: `Bearer ${SUPABASE_SERVICE_KEY}`,
  };
  if (conBody) cabeceras["Content-Type"] = "application/json";
  return cabeceras;
}

function respuestaJson(res, codigo, datos) {
  res.writeHead(codigo, { "Content-Type": "application/json" });
  res.end(JSON.stringify(datos));
}

function errorSupabase(res, error) {
  // Mismo contrato que el microservicio original de Python: 502 con el detalle.
  respuestaJson(res, 502, { detail: `Error de Supabase: ${error}` });
}

function leerBody(req) {
  return new Promise((resolver, rechazar) => {
    let datos = "";
    req.on("data", (trozo) => {
      datos += trozo;
    });
    req.on("end", () => resolver(datos));
    req.on("error", rechazar);
  });
}

function parsearBody(datos) {
  // Devuelve el objeto parseado, o null si no hay body o el JSON es inválido.
  if (!datos) return null;
  try {
    return JSON.parse(datos);
  } catch {
    return null;
  }
}

function validarCrear(resena) {
  if (typeof resena.libro_id !== "number" || !Number.isInteger(resena.libro_id) || resena.libro_id < 1) {
    return "libro_id debe ser un entero mayor o igual a 1";
  }
  if (
    typeof resena.lector !== "string" ||
    resena.lector.trim() === "" ||
    resena.lector.length > 100
  ) {
    return "lector debe ser un texto no vacío de hasta 100 caracteres";
  }
  if (typeof resena.puntaje !== "number" || !Number.isInteger(resena.puntaje) || resena.puntaje < 1 || resena.puntaje > 5) {
    return "puntaje debe ser un entero entre 1 y 5";
  }
  return null;
}

function validarLibro(libro, parcial) {
  // Valida los campos de un libro. Si `parcial` es true (PUT) solo se validan
  // los campos presentes; si es false (POST) titulo e isbn son obligatorios.
  // Devuelve un mensaje de error o null si el libro es válido.
  if ((libro.titulo !== undefined || !parcial) && (typeof libro.titulo !== "string" || libro.titulo.trim() === "")) {
    return "titulo debe ser un texto no vacío";
  }
  if ((libro.isbn !== undefined || !parcial) && (typeof libro.isbn !== "string" || libro.isbn.trim() === "")) {
    return "isbn debe ser un texto no vacío";
  }
  for (const campo of ["anio_publicacion", "paginas"]) {
    const valor = libro[campo];
    if (valor !== undefined && valor !== null && !Number.isInteger(valor)) {
      return `${campo} debe ser un entero o null`;
    }
  }
  if (libro.disponible !== undefined && typeof libro.disponible !== "boolean") {
    return "disponible debe ser un booleano";
  }
  if (libro.categoria !== undefined && typeof libro.categoria !== "string") {
    return "categoria debe ser un texto";
  }
  return null;
}

async function atender(req, res) {
  const url = new URL(req.url, `http://${req.headers.host || "localhost"}`);
  const ruta = url.pathname;
  const metodo = req.method;

  // GET /api/salud — health check de la plataforma.
  if (metodo === "GET" && ruta === "/api/salud") {
    return respuestaJson(res, 200, { estado: "ok" });
  }

  // GET /api/resenas — todas las reseñas, de la más nueva a la más vieja.
  if (metodo === "GET" && ruta === "/api/resenas") {
    try {
      const respuesta = await fetch(
        `${BASE_SUPABASE}/${TABLA}?select=*&order=creada_en.desc`,
        { headers: cabeceras() },
      );
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      return respuestaJson(res, 200, { cantidad: filas.length, resenas: filas });
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // GET /api/libros/{libro_id}/resenas — las reseñas de un libro con su promedio.
  const coincidenciaLibros = ruta.match(/^\/api\/libros\/(\d+)\/resenas$/);
  if (metodo === "GET" && coincidenciaLibros) {
    const libroId = Number(coincidenciaLibros[1]);
    try {
      const respuesta = await fetch(
        `${BASE_SUPABASE}/${TABLA}?select=*&libro_id=eq.${libroId}&order=creada_en.desc`,
        { headers: cabeceras() },
      );
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      // Mismo redondeo que el original: round(promedio, 2).
      const promedio = filas.length
        ? Math.round((filas.reduce((suma, fila) => suma + fila.puntaje, 0) / filas.length) * 100) / 100
        : null;
      return respuestaJson(res, 200, {
        libro_id: libroId,
        cantidad: filas.length,
        promedio,
        resenas: filas,
      });
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // POST /api/resenas — inserta una reseña nueva y la devuelve ya guardada.
  if (metodo === "POST" && ruta === "/api/resenas") {
    const datos = await leerBody(req);
    const resena = parsearBody(datos);
    if (resena === null) {
      return respuestaJson(res, 422, { detail: "El body debe ser JSON válido" });
    }
    if (typeof resena !== "object" || Array.isArray(resena)) {
      return respuestaJson(res, 422, { detail: "El body debe ser un objeto JSON" });
    }
    const errorValidacion = validarCrear(resena);
    if (errorValidacion) {
      return respuestaJson(res, 422, { detail: errorValidacion });
    }
    const cuerpo = {
      libro_id: resena.libro_id,
      lector: resena.lector,
      puntaje: resena.puntaje,
      comentario: resena.comentario !== undefined ? resena.comentario : "",
    };
    try {
      const respuesta = await fetch(`${BASE_SUPABASE}/${TABLA}`, {
        method: "POST",
        headers: { ...cabeceras(true), Prefer: "return=representation" },
        body: JSON.stringify(cuerpo),
      });
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      if (!filas.length) {
        return respuestaJson(res, 502, { detail: "Supabase no devolvió la fila insertada" });
      }
      return respuestaJson(res, 201, filas[0]);
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // PATCH /api/resenas/{id} — actualiza solo los campos enviados y devuelve la fila.
  const coincidenciaPatch = ruta.match(/^\/api\/resenas\/(\d+)$/);
  if (metodo === "PATCH" && coincidenciaPatch) {
    const id = Number(coincidenciaPatch[1]);
    const datos = await leerBody(req);
    const cambios = parsearBody(datos);
    if (cambios === null) {
      return respuestaJson(res, 422, { detail: "El body debe ser JSON válido" });
    }
    if (typeof cambios !== "object" || Array.isArray(cambios)) {
      return respuestaJson(res, 422, { detail: "El body debe ser un objeto JSON" });
    }
    const cuerpo = {};
    for (const campo of ["lector", "puntaje", "comentario"]) {
      if (cambios[campo] !== undefined) cuerpo[campo] = cambios[campo];
    }
    if (Object.keys(cuerpo).length === 0) {
      return respuestaJson(res, 422, {
        detail: "Se necesita al menos uno de lector, puntaje o comentario",
      });
    }
    if (
      cuerpo.puntaje !== undefined &&
      (typeof cuerpo.puntaje !== "number" || !Number.isInteger(cuerpo.puntaje) || cuerpo.puntaje < 1 || cuerpo.puntaje > 5)
    ) {
      return respuestaJson(res, 422, { detail: "puntaje debe ser un entero entre 1 y 5" });
    }
    if (
      cuerpo.lector !== undefined &&
      (typeof cuerpo.lector !== "string" || cuerpo.lector.trim() === "" || cuerpo.lector.length > 100)
    ) {
      return respuestaJson(res, 422, { detail: "lector debe ser un texto no vacío de hasta 100 caracteres" });
    }
    try {
      const respuesta = await fetch(`${BASE_SUPABASE}/${TABLA}?id=eq.${id}`, {
        method: "PATCH",
        headers: { ...cabeceras(true), Prefer: "return=representation" },
        body: JSON.stringify(cuerpo),
      });
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      if (!filas.length) {
        return respuestaJson(res, 404, { detail: "no encontrado" });
      }
      return respuestaJson(res, 200, filas[0]);
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // DELETE /api/resenas/{id} — borra la fila y la devuelve.
  const coincidenciaDelete = ruta.match(/^\/api\/resenas\/(\d+)$/);
  if (metodo === "DELETE" && coincidenciaDelete) {
    const id = Number(coincidenciaDelete[1]);
    try {
      const respuesta = await fetch(`${BASE_SUPABASE}/${TABLA}?id=eq.${id}`, {
        method: "DELETE",
        headers: { ...cabeceras(), Prefer: "return=representation" },
      });
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      if (!filas.length) {
        return respuestaJson(res, 404, { detail: "no encontrado" });
      }
      return respuestaJson(res, 200, filas[0]);
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // GET /api/libros — todos los libros, del más nuevo al más viejo.
  if (metodo === "GET" && ruta === "/api/libros") {
    try {
      const respuesta = await fetch(
        `${BASE_SUPABASE}/${TABLA_LIBROS}?select=*&order=creada_en.desc`,
        { headers: cabeceras() },
      );
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      return respuestaJson(res, 200, { cantidad: filas.length, libros: filas });
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // GET /api/libros/{id} — un libro puntual, o 404 si no existe.
  const coincidenciaLibro = ruta.match(/^\/api\/libros\/(\d+)$/);
  if (metodo === "GET" && coincidenciaLibro) {
    const id = Number(coincidenciaLibro[1]);
    try {
      const respuesta = await fetch(
        `${BASE_SUPABASE}/${TABLA_LIBROS}?select=*&id=eq.${id}`,
        { headers: cabeceras() },
      );
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      if (!filas.length) {
        return respuestaJson(res, 404, { detail: "no encontrado" });
      }
      return respuestaJson(res, 200, filas[0]);
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // POST /api/libros — crea un libro y lo devuelve ya guardado.
  if (metodo === "POST" && ruta === "/api/libros") {
    const datos = await leerBody(req);
    const libro = parsearBody(datos);
    if (libro === null) {
      return respuestaJson(res, 422, { detail: "El body debe ser JSON válido" });
    }
    if (typeof libro !== "object" || Array.isArray(libro)) {
      return respuestaJson(res, 422, { detail: "El body debe ser un objeto JSON" });
    }
    const errorValidacion = validarLibro(libro, false);
    if (errorValidacion) {
      return respuestaJson(res, 422, { detail: errorValidacion });
    }
    const cuerpo = {
      titulo: libro.titulo,
      isbn: libro.isbn,
      anio_publicacion: libro.anio_publicacion !== undefined ? libro.anio_publicacion : null,
      paginas: libro.paginas !== undefined ? libro.paginas : null,
      disponible: libro.disponible !== undefined ? libro.disponible : true,
      categoria: libro.categoria !== undefined ? libro.categoria : "",
    };
    try {
      const respuesta = await fetch(`${BASE_SUPABASE}/${TABLA_LIBROS}`, {
        method: "POST",
        headers: { ...cabeceras(true), Prefer: "return=representation" },
        body: JSON.stringify(cuerpo),
      });
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      if (!filas.length) {
        return respuestaJson(res, 502, { detail: "Supabase no devolvió la fila insertada" });
      }
      return respuestaJson(res, 201, filas[0]);
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // PUT /api/libros/{id} — actualiza con cualquier subconjunto de campos y devuelve la fila.
  const coincidenciaPut = ruta.match(/^\/api\/libros\/(\d+)$/);
  if (metodo === "PUT" && coincidenciaPut) {
    const id = Number(coincidenciaPut[1]);
    const datos = await leerBody(req);
    const cambios = parsearBody(datos);
    if (cambios === null) {
      return respuestaJson(res, 422, { detail: "El body debe ser JSON válido" });
    }
    if (typeof cambios !== "object" || Array.isArray(cambios)) {
      return respuestaJson(res, 422, { detail: "El body debe ser un objeto JSON" });
    }
    const errorValidacion = validarLibro(cambios, true);
    if (errorValidacion) {
      return respuestaJson(res, 422, { detail: errorValidacion });
    }
    const cuerpo = {};
    for (const campo of ["titulo", "isbn", "anio_publicacion", "paginas", "disponible", "categoria"]) {
      if (cambios[campo] !== undefined) cuerpo[campo] = cambios[campo];
    }
    if (Object.keys(cuerpo).length === 0) {
      return respuestaJson(res, 422, { detail: "Se necesita al menos un campo para actualizar" });
    }
    try {
      const respuesta = await fetch(`${BASE_SUPABASE}/${TABLA_LIBROS}?id=eq.${id}`, {
        method: "PATCH",
        headers: { ...cabeceras(true), Prefer: "return=representation" },
        body: JSON.stringify(cuerpo),
      });
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      if (!filas.length) {
        return respuestaJson(res, 404, { detail: "no encontrado" });
      }
      return respuestaJson(res, 200, filas[0]);
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // DELETE /api/libros/{id} — borra el libro y devuelve la fila borrada.
  const coincidenciaDeleteLibro = ruta.match(/^\/api\/libros\/(\d+)$/);
  if (metodo === "DELETE" && coincidenciaDeleteLibro) {
    const id = Number(coincidenciaDeleteLibro[1]);
    try {
      const respuesta = await fetch(`${BASE_SUPABASE}/${TABLA_LIBROS}?id=eq.${id}`, {
        method: "DELETE",
        headers: { ...cabeceras(), Prefer: "return=representation" },
      });
      if (!respuesta.ok) throw new Error(`HTTP ${respuesta.status}`);
      const filas = await respuesta.json();
      if (!filas.length) {
        return respuestaJson(res, 404, { detail: "no encontrado" });
      }
      return respuestaJson(res, 200, filas[0]);
    } catch (error) {
      return errorSupabase(res, error);
    }
  }

  // Ruta o método no soportado.
  return respuestaJson(res, 404, { detail: "no encontrado" });
}

// Todas las rutas cuelgan de /api porque el servicio comparte dominio con el
// sitio Django: el sitio vive en / y la API en /api. Vercel enruta por prefijo
// y le entrega al servicio la ruta completa, con /api incluido.
const server = http.createServer(async (req, res) => {
  try {
    await atender(req, res);
  } catch (error) {
    // Ningún error interno debe tirar abajo el proceso.
    console.error("Error interno del servidor:", error);
    respuestaJson(res, 500, { detail: "Error interno del servidor" });
  }
});

server.listen(PUERTO, () => {
  console.log(`Microservicio de reseñas escuchando en http://localhost:${PUERTO}`);
});