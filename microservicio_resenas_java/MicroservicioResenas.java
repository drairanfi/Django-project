import com.sun.net.httpserver.HttpExchange;
import com.sun.net.httpserver.HttpServer;
import java.io.IOException;
import java.net.InetSocketAddress;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.Executors;

/**
 * Microservicio de reseñas (replica en Java del original en Python/FastAPI).
 *
 * Expone una API HTTP sobre una tabla de Supabase (PostgreSQL en la nube) sin
 * usar driver JDBC: accede a la tabla por la API REST PostgREST de Supabase con
 * la service_role key. Django NO habla con esta base de datos: habla con esta
 * API por HTTP.
 *
 * No usa Maven, Gradle ni frameworks: un solo archivo que corre con la ejecución
 * de fuente única del JDK:
 *
 *     java MicroservicioResenas.java
 *
 * Stack: OpenJDK 27, com.sun.net.httpserver (servidor HTTP) y
 * java.net.http.HttpClient (llamadas salientes), ambos del JDK.
 */
public class MicroservicioResenas {

    /** Nombre de la tabla en Supabase (columna de la base, no código de Django). */
    static final String TABLA = "resenas";

    /** Nombre de la tabla de libros en Supabase (CRUD agregado al microservicio). */
    static final String TABLA_LIBROS = "libros";

    /** Puerto por defecto si no está definida la variable de entorno PORT. */
    static final int PUERTO_DEFECTO = 8003;

    /** URL base de la API REST de Supabase: {SUPABASE_URL}/rest/v1. */
    static String baseREST;

    /** Service_role key de Supabase: se manda como apikey y como Bearer. */
    static String claveAPI;

    /** Cliente HTTP compartido para todas las llamadas a Supabase. */
    static HttpClient clienteHttp;

    public static void main(String[] args) throws IOException {
        // 1. Leer credenciales del entorno. Nunca se escriben en el código.
        //    Si falta alguna, el servicio no arranca: es preferible fallar al
        //    inicio con un mensaje claro y no a mitad de un request.
        String supabaseUrl = System.getenv("SUPABASE_URL");
        String supabaseKey = System.getenv("SUPABASE_SERVICE_KEY");
        if (supabaseUrl == null || supabaseUrl.isBlank()
                || supabaseKey == null || supabaseKey.isBlank()) {
            System.err.println("Falta la variable de entorno SUPABASE_URL o SUPABASE_SERVICE_KEY.");
            System.err.println("Cargalas en el panel de despliegue o desde el archivo .env:");
            System.err.println("    set -a; . ./.env; set +a");
            System.exit(1);
        }

        // 2. Leer el puerto (PORT, por defecto 8003).
        int puerto = PUERTO_DEFECTO;
        String puertoEnv = System.getenv("PORT");
        if (puertoEnv != null && !puertoEnv.isBlank()) {
            try {
                puerto = Integer.parseInt(puertoEnv.trim());
            } catch (NumberFormatException e) {
                System.err.println("La variable de entorno PORT no es un número válido: " + puertoEnv);
                System.exit(1);
                return;
            }
        }

        // 3. Configurar el acceso a Supabase.
        //    Se quita la barra final por si la URL del panel la trae.
        baseREST = supabaseUrl.replaceAll("/+$", "") + "/rest/v1";
        claveAPI = supabaseKey;
        clienteHttp = HttpClient.newBuilder()
                .connectTimeout(Duration.ofSeconds(5))
                .build();

        // 4. Armar el servidor HTTP sobre el contexto /api, igual que el
        //    original: en el despliegue el servicio recibe la ruta completa con
        //    /api incluido, así que el prefijo se declara acá también.
        HttpServer servidor = HttpServer.create(new InetSocketAddress(puerto), 0);
        servidor.createContext("/api", MicroservicioResenas::manejarPeticion);
        // Hilos virtuales (JEP 444): cada request en su propio hilo, liviano.
        servidor.setExecutor(Executors.newVirtualThreadPerTaskExecutor());
        servidor.start();

        System.out.println("Microservicio de reseñas (Java) escuchando en http://127.0.0.1:" + puerto + "/api");
        System.out.println("Base PostgREST: " + baseREST);
        System.out.println("Probá con: curl http://127.0.0.1:" + puerto + "/api/salud");
    }

    // ---------------------------------------------------------------------
    // Capa HTTP: enrutar la petición y enviar la respuesta
    // ---------------------------------------------------------------------

    /** Respuesta HTTP mínima: código de estado y cuerpo JSON como texto. */
    static record Respuesta(int codigo, String cuerpo) {}

    /**
     * Atiende una petición entrante: lee el cuerpo, la enruta y responde.
     * Nunca deja morir al servidor: cualquier error se traduce en una
     * respuesta HTTP con su código correspondiente.
     */
    static void manejarPeticion(HttpExchange intercambio) {
        String cuerpo = "";
        try {
            cuerpo = new String(intercambio.getRequestBody().readAllBytes(), StandardCharsets.UTF_8);
        } catch (IOException e) {
            // Sin cuerpo legible: las rutas GET no lo necesitan y las de
            // escritura responderán 422 al validar.
        }

        Respuesta respuesta;
        try {
            respuesta = enrutar(intercambio.getRequestMethod(),
                    intercambio.getRequestURI().getPath(), cuerpo);
        } catch (ErrorValidacion e) {
            // Datos mal validados por el cliente: 422 con el detalle claro.
            respuesta = new Respuesta(422,
                    "{\"detail\":\"" + Json.escapar(e.getMessage()) + "\"}");
        } catch (ErrorSupabase e) {
            // Supabase caído o respuesta inesperada: 502, igual que el original.
            respuesta = new Respuesta(502,
                    "{\"detail\":\"" + Json.escapar("Error de Supabase: " + e.getMessage()) + "\"}");
        } catch (Exception e) {
            // Cualquier otra cosa: 500 genérico, el servidor sigue vivo.
            respuesta = new Respuesta(500, "{\"detail\":\"Error interno del servidor\"}");
        }
        enviar(intercambio, respuesta);
    }

    /** Escribe la respuesta JSON en el intercambio y lo cierra. */
    static void enviar(HttpExchange intercambio, Respuesta respuesta) {
        try {
            byte[] bytes = respuesta.cuerpo().getBytes(StandardCharsets.UTF_8);
            intercambio.getResponseHeaders().set("Content-Type", "application/json; charset=utf-8");
            intercambio.sendResponseHeaders(respuesta.codigo(), bytes.length);
            try (var salida = intercambio.getResponseBody()) {
                salida.write(bytes);
            }
        } catch (IOException e) {
            // El cliente se desconectó a mitad de la respuesta: no hay nada más que hacer.
        } finally {
            intercambio.close();
        }
    }

    /**
     * Decide qué operación ejecutar según el método HTTP y el path.
     * Todas las rutas cuelgan de /api. Paths inválidos o métodos no
     * permitidos responden 404/405 como hace FastAPI en el original.
     */
    static Respuesta enrutar(String metodo, String ruta, String cuerpo) {
        String[] s = ruta.split("/");
        // s[0] = "" (la barra inicial), s[1] = "api"
        if (s.length < 3 || !s[1].equals("api")) {
            return noEncontrado();
        }

        if (s.length == 3 && s[2].equals("salud")) {
            if (metodo.equals("GET")) {
                return new Respuesta(200, "{\"estado\":\"ok\"}");
            }
            return metodoNoPermitido();
        }

        if (s.length == 3 && s[2].equals("resenas")) {
            if (metodo.equals("GET")) {
                return listarResenas();
            }
            if (metodo.equals("POST")) {
                return crearResena(cuerpo);
            }
            return metodoNoPermitido();
        }

        if (s.length == 4 && s[2].equals("resenas")) {
            long id = parsearId(s[3]);
            if (id < 0) {
                throw new ErrorValidacion("El id de la reseña debe ser un entero positivo");
            }
            if (metodo.equals("PATCH")) {
                return actualizarResena(id, cuerpo);
            }
            if (metodo.equals("DELETE")) {
                return borrarResena(id);
            }
            return metodoNoPermitido();
        }

        if (s.length == 3 && s[2].equals("libros")) {
            if (metodo.equals("GET")) {
                return listarLibros();
            }
            if (metodo.equals("POST")) {
                return crearLibro(cuerpo);
            }
            return metodoNoPermitido();
        }

        if (s.length == 4 && s[2].equals("libros")) {
            long id = parsearId(s[3]);
            if (id < 0) {
                throw new ErrorValidacion("El id del libro debe ser un entero positivo");
            }
            if (metodo.equals("GET")) {
                return obtenerLibro(id);
            }
            if (metodo.equals("PUT")) {
                return actualizarLibro(id, cuerpo);
            }
            if (metodo.equals("DELETE")) {
                return borrarLibro(id);
            }
            return metodoNoPermitido();
        }

        if (s.length == 5 && s[2].equals("libros") && s[4].equals("resenas")) {
            long libroId = parsearId(s[3]);
            if (libroId < 0) {
                throw new ErrorValidacion("El id del libro debe ser un entero positivo");
            }
            if (metodo.equals("GET")) {
                return resenasDeLibro(libroId);
            }
            return metodoNoPermitido();
        }

        return noEncontrado();
    }

    /** Path que no existe: 404, igual que FastAPI. */
    static Respuesta noEncontrado() {
        return new Respuesta(404, "{\"detail\":\"Not Found\"}");
    }

    /** Método no permitido en un path conocido: 405, igual que FastAPI. */
    static Respuesta metodoNoPermitido() {
        return new Respuesta(405, "{\"detail\":\"Method Not Allowed\"}");
    }

    /** Parsea un id de la URL; devuelve -1 si no es un entero válido. */
    static long parsearId(String texto) {
        try {
            return Long.parseLong(texto);
        } catch (NumberFormatException e) {
            return -1;
        }
    }

    // ---------------------------------------------------------------------
    // Operaciones de la API
    // ---------------------------------------------------------------------

    /** GET /api/resenas: todas las reseñas, de la más nueva a la más vieja. */
    static Respuesta listarResenas() {
        Valor lista = leerListaSupabase("/" + TABLA + "?select=*&order=creada_en.desc");
        return new Respuesta(200,
                "{\"cantidad\":" + lista.lista().size()
                        + ",\"resenas\":" + Json.serializar(lista) + "}");
    }

    /**
     * GET /api/libros/{libro_id}/resenas: reseñas de un libro con su promedio
     * de puntaje redondeado a 2 decimales (o null si no hay reseñas).
     * Este es el endpoint que consume la vista de Django.
     */
    static Respuesta resenasDeLibro(long libroId) {
        Valor lista = leerListaSupabase(
                "/" + TABLA + "?select=*&libro_id=eq." + libroId + "&order=creada_en.desc");

        int cantidad = lista.lista().size();
        String promedio = "null";
        if (cantidad > 0) {
            long suma = 0;
            for (Valor fila : lista.lista()) {
                suma += fila.get("puntaje").comoEntero();
            }
            // Redondeo a 2 decimales: igual al round(x, 2) de Python.
            double p = Math.round(suma * 100.0 / cantidad) / 100.0;
            promedio = Double.toString(p);
        }

        return new Respuesta(200,
                "{\"libro_id\":" + libroId
                        + ",\"cantidad\":" + cantidad
                        + ",\"promedio\":" + promedio
                        + ",\"resenas\":" + Json.serializar(lista) + "}");
    }

    /** POST /api/resenas: valida, inserta en Supabase y devuelve la fila creada. */
    static Respuesta crearResena(String cuerpo) {
        ResenaNueva nueva = validarResenaNueva(cuerpo);

        // Body JSON hacia PostgREST. Solo los números van sin comillas; el
        // texto se escapa por si trae comillas o caracteres especiales.
        String body = "{\"libro_id\":" + nueva.libroId()
                + ",\"lector\":\"" + Json.escapar(nueva.lector()) + "\""
                + ",\"puntaje\":" + nueva.puntaje()
                + ",\"comentario\":\"" + Json.escapar(nueva.comentario()) + "\"}";

        Valor fila = leerFilaSupabase("POST", "/" + TABLA, body, true);
        // 201: recurso creado, igual que el status_code=201 del original.
        return new Respuesta(201, Json.serializar(fila));
    }

    /** PATCH /api/resenas/{id}: actualiza los campos que vengan y devuelve la fila. */
    static Respuesta actualizarResena(long id, String cuerpo) {
        String body = validarActualizacion(cuerpo);
        Valor fila = leerFilaSupabase("PATCH", "/" + TABLA + "?id=eq." + id, body, true);
        return new Respuesta(200, Json.serializar(fila));
    }

    /** DELETE /api/resenas/{id}: borra la fila y la devuelve. */
    static Respuesta borrarResena(long id) {
        Valor fila = leerFilaSupabase("DELETE", "/" + TABLA + "?id=eq." + id, null, true);
        return new Respuesta(200, Json.serializar(fila));
    }

    // ---- CRUD de libros (misma tabla, mismo contrato PostgREST) ----

    /** GET /api/libros: todos los libros, de la más nuevo al más viejo. */
    static Respuesta listarLibros() {
        Valor lista = leerListaSupabase("/" + TABLA_LIBROS + "?select=*&order=creada_en.desc");
        return new Respuesta(200,
                "{\"cantidad\":" + lista.lista().size()
                        + ",\"libros\":" + Json.serializar(lista) + "}");
    }

    /** GET /api/libros/{id}: un libro por id, o 404 si no existe. */
    static Respuesta obtenerLibro(long id) {
        Valor lista = leerListaSupabase("/" + TABLA_LIBROS + "?select=*&id=eq." + id);
        if (lista.lista().isEmpty()) {
            return libroNoEncontrado();
        }
        return new Respuesta(200, Json.serializar(lista.lista().get(0)));
    }

    /** POST /api/libros: valida, inserta en Supabase y devuelve la fila creada. */
    static Respuesta crearLibro(String cuerpo) {
        String body = cuerpoLibro(cuerpo, true);
        Valor fila = leerFilaSupabase("POST", "/" + TABLA_LIBROS, body, true);
        // 201: recurso creado, igual que el POST de reseñas.
        return new Respuesta(201, Json.serializar(fila));
    }

    /**
     * PUT /api/libros/{id}: actualiza los campos que vengan y devuelve la fila.
     * Si el id no existe, 404. La actualización contra Supabase se hace con
     * PATCH: PUT es el verbo del contrato HTTP, PATCH el de PostgREST.
     */
    static Respuesta actualizarLibro(long id, String cuerpo) {
        String body = cuerpoLibro(cuerpo, false);
        Valor fila = leerFilaSupabase("PATCH", "/" + TABLA_LIBROS + "?id=eq." + id, body, false);
        if (fila == null) {
            return libroNoEncontrado();
        }
        return new Respuesta(200, Json.serializar(fila));
    }

    /** DELETE /api/libros/{id}: borra la fila y la devuelve. Si no existe, 404. */
    static Respuesta borrarLibro(long id) {
        Valor fila = leerFilaSupabase("DELETE", "/" + TABLA_LIBROS + "?id=eq." + id, null, false);
        if (fila == null) {
            return libroNoEncontrado();
        }
        return new Respuesta(200, Json.serializar(fila));
    }

    /** 404 para un libro que no existe. */
    static Respuesta libroNoEncontrado() {
        return new Respuesta(404, "{\"detail\":\"no encontrado\"}");
    }

    // ---------------------------------------------------------------------
    // Validación de los cuerpos que manda el cliente
    // ---------------------------------------------------------------------

    /** Datos ya validados de una reseña nueva. */
    static record ResenaNueva(long libroId, String lector, int puntaje, String comentario) {}

    /** Lanza ErrorValidacion (-> 422) con un mensaje claro si algo está mal. */
    static ErrorValidacion error422(String mensaje) {
        return new ErrorValidacion(mensaje);
    }

    /** Parsea el cuerpo como JSON; si no es JSON válido, 422. */
    static Valor parsearCuerpo(String cuerpo) {
        try {
            return Json.parsear(cuerpo);
        } catch (RuntimeException e) {
            throw error422("El cuerpo no es un JSON válido: " + e.getMessage());
        }
    }

    /** Valida el cuerpo de POST /api/resenas contra el contrato de la API. */
    static ResenaNueva validarResenaNueva(String cuerpo) {
        Valor v = parsearCuerpo(cuerpo);
        if (!v.esObjeto()) {
            throw error422("El cuerpo debe ser un objeto JSON");
        }

        // libro_id: obligatorio, entero >= 1.
        Valor libro = v.get("libro_id");
        if (libro == null || libro.esNull()) {
            throw error422("Falta el campo 'libro_id'");
        }
        if (!libro.esNumero()) {
            throw error422("'libro_id' debe ser un entero");
        }
        long libroId = libro.comoEntero();
        if (libroId < 1) {
            throw error422("'libro_id' debe ser un entero mayor o igual a 1");
        }

        // lector: obligatorio, no vacío y de hasta 100 caracteres.
        Valor lectorV = v.get("lector");
        if (lectorV == null || lectorV.esNull()) {
            throw error422("Falta el campo 'lector'");
        }
        if (!lectorV.esString()) {
            throw error422("'lector' debe ser un texto");
        }
        String lector = lectorV.comoString();
        if (lector.trim().isEmpty()) {
            throw error422("'lector' no puede estar vacío");
        }
        if (lector.length() > 100) {
            throw error422("'lector' no puede superar los 100 caracteres");
        }

        // puntaje: obligatorio, entero entre 1 y 5.
        Valor puntajeV = v.get("puntaje");
        if (puntajeV == null || puntajeV.esNull()) {
            throw error422("Falta el campo 'puntaje'");
        }
        if (!puntajeV.esNumero()) {
            throw error422("'puntaje' debe ser un entero");
        }
        long puntaje = puntajeV.comoEntero();
        if (puntaje < 1 || puntaje > 5) {
            throw error422("'puntaje' debe ser un entero entre 1 y 5");
        }

        // comentario: opcional, por defecto una cadena vacía.
        String comentario = "";
        Valor comV = v.get("comentario");
        if (comV != null && !comV.esNull()) {
            if (!comV.esString()) {
                throw error422("'comentario' debe ser un texto");
            }
            comentario = comV.comoString();
        }

        return new ResenaNueva(libroId, lector, (int) puntaje, comentario);
    }

    /**
     * Valida el cuerpo de PATCH /api/resenas/{id} y devuelve el JSON con solo
     * los campos presentes (los demás no se tocan).
     */
    static String validarActualizacion(String cuerpo) {
        Valor v = parsearCuerpo(cuerpo);
        if (!v.esObjeto()) {
            throw error422("El cuerpo debe ser un objeto JSON");
        }

        List<String> partes = new ArrayList<>();
        boolean hayCampo = false;

        Valor lectorV = v.get("lector");
        if (lectorV != null && !lectorV.esNull()) {
            if (!lectorV.esString()) {
                throw error422("'lector' debe ser un texto");
            }
            String lector = lectorV.comoString();
            if (lector.trim().isEmpty()) {
                throw error422("'lector' no puede estar vacío");
            }
            if (lector.length() > 100) {
                throw error422("'lector' no puede superar los 100 caracteres");
            }
            partes.add("\"lector\":\"" + Json.escapar(lector) + "\"");
            hayCampo = true;
        }

        Valor puntajeV = v.get("puntaje");
        if (puntajeV != null && !puntajeV.esNull()) {
            if (!puntajeV.esNumero()) {
                throw error422("'puntaje' debe ser un entero");
            }
            long puntaje = puntajeV.comoEntero();
            if (puntaje < 1 || puntaje > 5) {
                throw error422("'puntaje' debe ser un entero entre 1 y 5");
            }
            partes.add("\"puntaje\":" + puntaje);
            hayCampo = true;
        }

        Valor comV = v.get("comentario");
        if (comV != null && !comV.esNull()) {
            if (!comV.esString()) {
                throw error422("'comentario' debe ser un texto");
            }
            partes.add("\"comentario\":\"" + Json.escapar(comV.comoString()) + "\"");
            hayCampo = true;
        }

        if (!hayCampo) {
            throw error422("El cuerpo debe incluir al menos uno de los campos: lector, puntaje, comentario");
        }

        return "{" + String.join(",", partes) + "}";
    }

    // ---- Validación de los cuerpos de libro (POST y PUT comparten reglas) ----

    /**
     * Parsea y valida el cuerpo de un libro (POST o PUT) y devuelve el JSON que
     * se manda a Supabase con los campos que corresponden.
     *
     * En POST, titulo e isbn son obligatorios y el resto es opcional: si no
     * viene, toma los defaults de la base (anio_publicacion/paginas null,
     * disponible true, categoria ''). En PUT alcanza con cualquier subconjunto
     * (al menos un campo) y un null explícito en un campo nullable lo limpia.
     */
    static String cuerpoLibro(String cuerpo, boolean esPost) {
        Valor v = parsearCuerpo(cuerpo);
        if (!v.esObjeto()) {
            throw error422("El cuerpo debe ser un objeto JSON");
        }

        List<String> partes = new ArrayList<>();
        boolean hayCampo = false;

        // titulo: obligatorio en POST; si viene (en PUT) debe ser no vacío.
        Valor tituloV = v.get("titulo");
        if (tituloV != null && !tituloV.esNull()) {
            if (!tituloV.esString()) {
                throw error422("'titulo' debe ser un texto");
            }
            String titulo = tituloV.comoString().trim();
            if (titulo.isEmpty()) {
                throw error422("'titulo' no puede estar vacío");
            }
            partes.add("\"titulo\":\"" + Json.escapar(titulo) + "\"");
            hayCampo = true;
        } else if (esPost) {
            throw error422("Falta el campo 'titulo'");
        }

        // isbn: obligatorio en POST; si viene (en PUT) debe ser no vacío.
        Valor isbnV = v.get("isbn");
        if (isbnV != null && !isbnV.esNull()) {
            if (!isbnV.esString()) {
                throw error422("'isbn' debe ser un texto");
            }
            String isbn = isbnV.comoString().trim();
            if (isbn.isEmpty()) {
                throw error422("'isbn' no puede estar vacío");
            }
            partes.add("\"isbn\":\"" + Json.escapar(isbn) + "\"");
            hayCampo = true;
        } else if (esPost) {
            throw error422("Falta el campo 'isbn'");
        }

        // anio_publicacion: entero opcional (columna nullable).
        Valor anioV = v.get("anio_publicacion");
        if (anioV != null) {
            hayCampo = true;
            if (!anioV.esNull()) {
                partes.add("\"anio_publicacion\":" + enteroDe(anioV, "anio_publicacion"));
            } else if (!esPost) {
                // En PUT, null explícito limpia el valor.
                partes.add("\"anio_publicacion\":null");
            }
        }

        // paginas: entero opcional (columna nullable).
        Valor pagV = v.get("paginas");
        if (pagV != null) {
            hayCampo = true;
            if (!pagV.esNull()) {
                partes.add("\"paginas\":" + enteroDe(pagV, "paginas"));
            } else if (!esPost) {
                partes.add("\"paginas\":null");
            }
        }

        // disponible: booleano opcional (default true). Null no es válido.
        Valor dispV = v.get("disponible");
        if (dispV != null) {
            hayCampo = true;
            if (dispV.esNull() || !dispV.esBooleano()) {
                throw error422("'disponible' debe ser true o false");
            }
            partes.add("\"disponible\":" + dispV.comoTexto());
        }

        // categoria: texto opcional (default '').
        Valor catV = v.get("categoria");
        if (catV != null) {
            hayCampo = true;
            if (!catV.esNull()) {
                if (!catV.esString()) {
                    throw error422("'categoria' debe ser un texto");
                }
                partes.add("\"categoria\":\"" + Json.escapar(catV.comoString()) + "\"");
            } else if (!esPost) {
                partes.add("\"categoria\":null");
            }
        }

        // En PUT hace falta al menos un campo para poder actualizar algo.
        if (!esPost && !hayCampo) {
            throw error422("El cuerpo debe incluir al menos uno de los campos: titulo, isbn, anio_publicacion, paginas, disponible, categoria");
        }

        return "{" + String.join(",", partes) + "}";
    }

    /** Interpreta un valor como entero; si no lo es, 422 con el nombre del campo. */
    static long enteroDe(Valor v, String campo) {
        // Solo un valor numérico es válido: un string "2020" no es un entero JSON.
        if (!v.esNumero()) {
            throw error422("'" + campo + "' debe ser un entero");
        }
        try {
            return v.comoEntero();
        } catch (NumberFormatException e) {
            throw error422("'" + campo + "' debe ser un entero");
        }
    }

    // ---------------------------------------------------------------------
    // Comunicación con Supabase (API REST PostgREST)
    // ---------------------------------------------------------------------

    /**
     * Hace una llamada HTTP a la API REST de Supabase y devuelve la respuesta.
     * Todas las llamadas llevan apikey y Authorization con la service_role key.
     * Cualquier fallo (red o código HTTP de error) se convierte en ErrorSupabase,
     * que la capa HTTP traduce a 502.
     */
    static HttpResponse<String> llamarSupabase(String metodo, String ruta, String cuerpo, boolean representacion) {
        try {
            HttpRequest.Builder b = HttpRequest.newBuilder(URI.create(baseREST + ruta))
                    .timeout(Duration.ofSeconds(10))
                    .header("apikey", claveAPI)
                    .header("Authorization", "Bearer " + claveAPI);

            HttpRequest request;
            switch (metodo) {
                case "GET" -> request = b.GET().build();
                case "POST" -> request = b.header("Content-Type", "application/json")
                        .POST(HttpRequest.BodyPublishers.ofString(cuerpo)).build();
                case "PATCH" -> request = b.header("Content-Type", "application/json")
                        .method("PATCH", HttpRequest.BodyPublishers.ofString(cuerpo)).build();
                case "DELETE" -> request = b.DELETE().build();
                default -> throw new IllegalArgumentException("Método no soportado: " + metodo);
            }
            if (representacion) {
                request = HttpRequest.newBuilder(request, (nombre, valor) -> true)
                        .header("Prefer", "return=representation")
                        .build();
            }

            HttpResponse<String> respuesta = clienteHttp.send(request, HttpResponse.BodyHandlers.ofString());
            int codigo = respuesta.statusCode();
            if (codigo < 200 || codigo >= 300) {
                // El detalle incluye el código y el cuerpo que devolvió Supabase.
                throw new ErrorSupabase("HTTP " + codigo + ": " + respuesta.body());
            }
            return respuesta;
        } catch (ErrorSupabase e) {
            throw e;
        } catch (IOException e) {
            throw new ErrorSupabase(e.getMessage() == null ? e.getClass().getSimpleName() : e.getMessage());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new ErrorSupabase("Llamada a Supabase interrumpida");
        }
    }

    /** Lee una lista de filas (las operaciones GET de la API). */
    static Valor leerListaSupabase(String ruta) {
        HttpResponse<String> respuesta = llamarSupabase("GET", ruta, null, false);
        try {
            Valor v = Json.parsear(respuesta.body());
            if (!v.esArray()) {
                throw new ErrorSupabase("Supabase devolvió un JSON que no es una lista");
            }
            return v;
        } catch (ErrorSupabase e) {
            throw e;
        } catch (RuntimeException e) {
            throw new ErrorSupabase("Supabase devolvió un JSON inválido");
        }
    }

    /**
     * Ejecuta POST/PATCH/DELETE con Prefer: return=representation y devuelve la
     * fila afectada. Con exigir=true, si Supabase no devuelve ninguna fila se
     * lanza 502 (igual que el original cuando la inserción no devuelve la fila
     * creada). Con exigir=false devuelve null: el llamador decide si es un 404.
     */
    static Valor leerFilaSupabase(String metodo, String ruta, String cuerpo, boolean exigir) {
        HttpResponse<String> respuesta = llamarSupabase(metodo, ruta, cuerpo, true);
        try {
            Valor v = Json.parsear(respuesta.body());
            if (!v.esArray() || v.lista().isEmpty()) {
                if (exigir) {
                    throw new ErrorSupabase("Supabase no devolvió la fila afectada");
                }
                return null;
            }
            return v.lista().get(0);
        } catch (ErrorSupabase e) {
            throw e;
        } catch (RuntimeException e) {
            throw new ErrorSupabase("Supabase devolvió un JSON inválido");
        }
    }

    // ---------------------------------------------------------------------
    // Errores internos
    // ---------------------------------------------------------------------

    /** Error contra Supabase (red o respuesta inesperada) -> 502. */
    static class ErrorSupabase extends RuntimeException {
        ErrorSupabase(String mensaje) {
            super(mensaje);
        }
    }

    /** Datos del cliente que no pasan la validación -> 422. */
    static class ErrorValidacion extends RuntimeException {
        ErrorValidacion(String mensaje) {
            super(mensaje);
        }
    }

    // ---------------------------------------------------------------------
    // Helper mínimo de JSON (sin librerías externas)
    // ---------------------------------------------------------------------

    /**
     * Helper mínimo para construir y leer JSON. Alcanza para este servicio:
     * guarda el texto raw de cada valor y lo re-serializa compacto, sin
     * espacios, como lo manda PostgREST.
     */
    static final class Json {

        /** Escapa una cadena para incluirla dentro de un literal JSON. */
        static String escapar(String s) {
            StringBuilder b = new StringBuilder(s.length());
            for (int i = 0; i < s.length(); i++) {
                char c = s.charAt(i);
                switch (c) {
                    case '"' -> b.append("\\\"");
                    case '\\' -> b.append("\\\\");
                    case '\n' -> b.append("\\n");
                    case '\r' -> b.append("\\r");
                    case '\t' -> b.append("\\t");
                    case '\b' -> b.append("\\b");
                    case '\f' -> b.append("\\f");
                    default -> {
                        if (c < 0x20) {
                            b.append(String.format("\\u%04x", (int) c));
                        } else {
                            b.append(c);
                        }
                    }
                }
            }
            return b.toString();
        }

        /** Parsea un documento JSON completo. Lanza RuntimeException si no es válido. */
        static Valor parsear(String texto) {
            Parser p = new Parser(texto);
            Valor v = p.valor();
            p.espacios();
            if (p.pos < p.texto.length()) {
                throw new RuntimeException("JSON inválido: sobra contenido después del documento");
            }
            return v;
        }

        /** Re-serializa un valor JSON compacto. */
        static String serializar(Valor v) {
            return v.serializar();
        }
    }

    /**
     * Un valor JSON ya parseado: objeto, array, string, número, booleano o null.
     * Los strings se guardan desescapados; los números como texto raw para
     * re-emitirlos tal cual (los enteros y timestamps de Supabase no se tocan).
     */
    static final class Valor {
        private static final char OBJETO = 'O';
        private static final char ARRAY = 'A';
        private static final char STRING = 'S';
        private static final char NUMERO = 'N';
        private static final char BOOLEANO = 'B';
        private static final char NULO = 'L';

        private final char tipo;
        private final Map<String, Valor> objeto;
        private final List<Valor> lista;
        private final String texto;

        private Valor(char tipo, Map<String, Valor> objeto, List<Valor> lista, String texto) {
            this.tipo = tipo;
            this.objeto = objeto;
            this.lista = lista;
            this.texto = texto;
        }

        static Valor objeto(Map<String, Valor> m) {
            return new Valor(OBJETO, m, null, null);
        }

        static Valor array(List<Valor> l) {
            return new Valor(ARRAY, null, l, null);
        }

        static Valor string(String s) {
            return new Valor(STRING, null, null, s);
        }

        static Valor numero(String raw) {
            return new Valor(NUMERO, null, null, raw);
        }

        static Valor booleano(String raw) {
            return new Valor(BOOLEANO, null, null, raw);
        }

        static Valor nulo() {
            return new Valor(NULO, null, null, null);
        }

        boolean esObjeto() {
            return tipo == OBJETO;
        }

        boolean esArray() {
            return tipo == ARRAY;
        }

        boolean esString() {
            return tipo == STRING;
        }

        boolean esNumero() {
            return tipo == NUMERO;
        }

        boolean esBooleano() {
            return tipo == BOOLEANO;
        }

        boolean esNull() {
            return tipo == NULO;
        }

        /** Devuelve el valor de una clave de objeto, o null si no existe. */
        Valor get(String clave) {
            if (objeto == null) {
                return null;
            }
            return objeto.get(clave);
        }

        /** Devuelve los elementos si esto es un array. */
        List<Valor> lista() {
            return lista;
        }

        /** Devuelve el texto ya desescapado de un string. */
        String comoString() {
            return texto;
        }

        /** Interpreta un número como entero. */
        long comoEntero() {
            return Long.parseLong(texto);
        }

        /** Devuelve el texto raw de un número o booleano ("true", "2020", ...). */
        String comoTexto() {
            return texto;
        }

        /** Serializa este valor a JSON compacto. */
        String serializar() {
            switch (tipo) {
                case OBJETO -> {
                    StringBuilder b = new StringBuilder("{");
                    boolean primero = true;
                    for (Map.Entry<String, Valor> e : objeto.entrySet()) {
                        if (!primero) {
                            b.append(',');
                        }
                        primero = false;
                        b.append('"').append(Json.escapar(e.getKey()))
                                .append("\":").append(e.getValue().serializar());
                    }
                    return b.append('}').toString();
                }
                case ARRAY -> {
                    StringBuilder b = new StringBuilder("[");
                    boolean primero = true;
                    for (Valor v : lista) {
                        if (!primero) {
                            b.append(',');
                        }
                        primero = false;
                        b.append(v.serializar());
                    }
                    return b.append(']').toString();
                }
                case STRING -> {
                    return "\"" + Json.escapar(texto) + "\"";
                }
                case NUMERO, BOOLEANO -> {
                    return texto;
                }
                default -> {
                    return "null";
                }
            }
        }
    }

    /** Parser recursivo descendente de JSON, sin librerías externas. */
    static final class Parser {
        final String texto;
        int pos = 0;

        Parser(String texto) {
            this.texto = texto;
        }

        /** Saltea espacios en blanco. */
        void espacios() {
            while (pos < texto.length() && Character.isWhitespace(texto.charAt(pos))) {
                pos++;
            }
        }

        /** Mira el carácter actual; '\0' si se acabó el texto. */
        char peek() {
            if (pos >= texto.length()) {
                return '\0';
            }
            return texto.charAt(pos);
        }

        /** Parsea el valor que empieza en la posición actual. */
        Valor valor() {
            espacios();
            if (pos >= texto.length()) {
                throw new RuntimeException("JSON vacío o incompleto");
            }
            return switch (peek()) {
                case '{' -> objeto();
                case '[' -> array();
                case '"' -> string();
                case 't' -> literal("true", 'B');
                case 'f' -> literal("false", 'B');
                case 'n' -> literal("null", 'L');
                default -> numero();
            };
        }

        /** Parsea un objeto { "clave": valor, ... }. */
        Valor objeto() {
            pos++; // consumir '{'
            Map<String, Valor> m = new LinkedHashMap<>();
            espacios();
            if (peek() == '}') {
                pos++;
                return Valor.objeto(m);
            }
            while (true) {
                espacios();
                if (peek() != '"') {
                    throw new RuntimeException("En un objeto, las claves van entre comillas");
                }
                String clave = string().comoString();
                espacios();
                if (peek() != ':') {
                    throw new RuntimeException("Falta ':' después de la clave '" + clave + "'");
                }
                pos++;
                m.put(clave, valor());
                espacios();
                char c = peek();
                if (c == ',') {
                    pos++;
                } else if (c == '}') {
                    pos++;
                    break;
                } else {
                    throw new RuntimeException("Se esperaba ',' o '}' en el objeto");
                }
            }
            return Valor.objeto(m);
        }

        /** Parsea un array [ valor, ... ]. */
        Valor array() {
            pos++; // consumir '['
            List<Valor> l = new ArrayList<>();
            espacios();
            if (peek() == ']') {
                pos++;
                return Valor.array(l);
            }
            while (true) {
                l.add(valor());
                espacios();
                char c = peek();
                if (c == ',') {
                    pos++;
                } else if (c == ']') {
                    pos++;
                    break;
                } else {
                    throw new RuntimeException("Se esperaba ',' o ']' en el array");
                }
            }
            return Valor.array(l);
        }

        /** Parsea un string y devuelve su contenido ya desescapado. */
        Valor string() {
            pos++; // consumir '"' de apertura
            StringBuilder b = new StringBuilder();
            while (pos < texto.length()) {
                char c = texto.charAt(pos++);
                if (c == '"') {
                    return Valor.string(b.toString());
                }
                if (c == '\\') {
                    if (pos >= texto.length()) {
                        throw new RuntimeException("String termina con una barra escapada suelta");
                    }
                    char e = texto.charAt(pos++);
                    switch (e) {
                        case '"' -> b.append('"');
                        case '\\' -> b.append('\\');
                        case '/' -> b.append('/');
                        case 'b' -> b.append('\b');
                        case 'f' -> b.append('\f');
                        case 'n' -> b.append('\n');
                        case 'r' -> b.append('\r');
                        case 't' -> b.append('\t');
                        case 'u' -> {
                            if (pos + 4 > texto.length()) {
                                throw new RuntimeException("Escape \\u incompleto");
                            }
                            b.append((char) Integer.parseInt(texto.substring(pos, pos + 4), 16));
                            pos += 4;
                        }
                        default -> throw new RuntimeException("Escape inválido: \\" + e);
                    }
                } else {
                    b.append(c);
                }
            }
            throw new RuntimeException("String sin cerrar");
        }

        /** Parsea true, false o null. */
        Valor literal(String palabra, char tipo) {
            if (!texto.startsWith(palabra, pos)) {
                throw new RuntimeException("Literal inválido en posición " + pos);
            }
            pos += palabra.length();
            if (tipo == 'L') {
                return Valor.nulo();
            }
            return Valor.booleano(palabra);
        }

        /** Parsea un número y conserva su texto raw (no se toca). */
        Valor numero() {
            int inicio = pos;
            while (pos < texto.length()
                    && "+-0123456789.eE".indexOf(texto.charAt(pos)) >= 0) {
                pos++;
            }
            if (inicio == pos) {
                throw new RuntimeException("Valor inesperado en posición " + inicio);
            }
            return Valor.numero(texto.substring(inicio, pos));
        }
    }
}