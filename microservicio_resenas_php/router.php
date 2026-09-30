<?php

declare(strict_types=1);

/*
 * Microservicio de reseñas y libros en PHP.
 *
 * Punto de entrada del servidor embebido de PHP (php -S 127.0.0.1:8004 router.php).
 * Enruta /api/* y delega cada operación a las funciones de este archivo, que
 * hablan con Supabase a través de su API REST (PostgREST). Sin frameworks, sin
 * Composer: solo la biblioteca estándar de PHP.
 */

// ---------------------------------------------------------------------------
// Configuración desde variables de entorno (se leen al arrancar el router)
// ---------------------------------------------------------------------------

$SUPABASE_URL = getenv('SUPABASE_URL');
$SUPABASE_SERVICE_KEY = getenv('SUPABASE_SERVICE_KEY');

// Sin las dos credenciales el servicio no puede funcionar: se avisa en la
// consola del servidor y todo request responde 500 con un mensaje claro.
$SIN_CONFIGURACION = (
    $SUPABASE_URL === false || $SUPABASE_URL === ''
    || $SUPABASE_SERVICE_KEY === false || $SUPABASE_SERVICE_KEY === ''
);

if ($SIN_CONFIGURACION) {
    error_log('[microservicio_resenas_php] Faltan SUPABASE_URL o SUPABASE_SERVICE_KEY.');
    error_log('[microservicio_resenas_php] Cargalas en el shell antes de arrancar: set -a; . ./.env; set +a');
}

$PUERTO = getenv('PORT') ?: '8004';

// ---------------------------------------------------------------------------
// Utilidades
// ---------------------------------------------------------------------------

/**
 * Responde JSON con el código de estado indicado y termina la petición.
 */
function responder_json(int $estado, array $datos): void
{
    http_response_code($estado);
    header('Content-Type: application/json; charset=utf-8');
    echo json_encode($datos);
    exit;
}

/**
 * Llama a la API REST de Supabase (PostgREST).
 *
 * @param string $metodo GET, POST, PATCH o DELETE.
 * @param string $ruta   Ruta de la API, arranca con el nombre de la tabla
 *                       (ej.: /resenas?select=* o /resenas?id=eq.5).
 * @param array|null $cuerpo Cuerpo JSON a enviar (solo para POST/PATCH/DELETE).
 *
 * @return array{estado: int, datos: mixed|null, error: string|null}
 *         - estado: código HTTP real que devolvió Supabase.
 *         - datos:  JSON decodificado de la respuesta, o null si hubo error.
 *         - error:  mensaje de error si algo falló (red, JSON inválido o
 *                   código fuera de 2xx), o null si todo salió bien.
 */
function llamar_supabase(string $metodo, string $ruta, ?array $cuerpo = null): array
{
    global $SUPABASE_URL, $SUPABASE_SERVICE_KEY;

    $url = rtrim($SUPABASE_URL, '/') . '/rest/v1' . $ruta;

    // Cabeceras que exige Supabase en TODA llamada.
    $cabeceras = [
        'apikey: ' . $SUPABASE_SERVICE_KEY,
        'Authorization: Bearer ' . $SUPABASE_SERVICE_KEY,
    ];
    if ($cuerpo !== null) {
        $cabeceras[] = 'Content-Type: application/json';
        // return=representation: PostgREST devuelve la fila afectada en el body.
        $cabeceras[] = 'Prefer: return=representation';
    }

    $opciones = [
        'http' => [
            'method' => $metodo,
            'header' => implode("\r\n", $cabeceras),
            // Ignorar el "Failed to open stream" ante códigos HTTP de error:
            // el estado real se lee de $http_response_header.
            'ignore_errors' => true,
            'timeout' => 5,
        ],
    ];
    if ($cuerpo !== null) {
        $opciones['http']['content'] = json_encode($cuerpo);
    }

    $contexto = stream_context_create($opciones);
    $respuesta = @file_get_contents($url, false, $contexto);

    // El código de estado real viene en la primera línea de las cabeceras de
    // respuesta, con forma "HTTP/1.1 200 OK". En PHP 8.5 se lee con
    // http_get_last_response_headers() (la variable $http_response_header está
    // deprecada desde 8.4).
    $cabeceras_respuesta = function_exists('http_get_last_response_headers')
        ? http_get_last_response_headers()
        : null;

    $estado = 502;
    if (is_array($cabeceras_respuesta) && isset($cabeceras_respuesta[0])
        && preg_match('/\s(\d{3})\s/', $cabeceras_respuesta[0], $partes)) {
        $estado = (int) $partes[1];
    }

    // Fallo de red (Supabase inaccesible, DNS, conexión rechazada): file_get_contents
    // devuelve false y $http_response_header ni siquiera se arma.
    if ($respuesta === false) {
        $ultimo_error = error_get_last();
        $mensaje = $ultimo_error['message'] ?? 'no se pudo conectar con Supabase';
        return ['estado' => $estado, 'datos' => null, 'error' => $mensaje];
    }

    $datos = json_decode($respuesta, true);
    if (json_last_error() !== JSON_ERROR_NONE) {
        return ['estado' => $estado, 'datos' => null, 'error' => 'Supabase devolvió un JSON inválido'];
    }

    // Un estado fuera de 2xx (p. ej. 500 de PostgREST) también cuenta como error.
    if ($estado < 200 || $estado >= 300) {
        return ['estado' => $estado, 'datos' => $datos, 'error' => 'HTTP ' . $estado . ': ' . $respuesta];
    }

    return ['estado' => $estado, 'datos' => $datos, 'error' => null];
}

/**
 * Convierte un fallo de Supabase en una respuesta 502 con el detalle esperado
 * (mismo formato que el microservicio original en Python).
 */
function responder_error_supabase(array $respuesta): void
{
    responder_json(502, ['detail' => 'Error de Supabase: ' . $respuesta['error']]);
}

// ---------------------------------------------------------------------------
// Validaciones
// ---------------------------------------------------------------------------

/**
 * Valida el cuerpo de una reseña nueva (POST /api/resenas).
 *
 * @return array{ok: bool, detail?: string, datos?: array} Con ok=true devuelve
 *         los datos ya normalizados; con ok=false devuelve el mensaje de error.
 */
function validar_resena(array $cuerpo): array
{
    $errores = [];

    if (!array_key_exists('libro_id', $cuerpo)) {
        $errores[] = 'El campo libro_id es obligatorio';
    } elseif (filter_var($cuerpo['libro_id'], FILTER_VALIDATE_INT) === false || $cuerpo['libro_id'] < 1) {
        $errores[] = 'El campo libro_id debe ser un entero mayor o igual a 1';
    }

    if (!array_key_exists('lector', $cuerpo)) {
        $errores[] = 'El campo lector es obligatorio';
    } elseif (!is_string($cuerpo['lector']) || trim($cuerpo['lector']) === '') {
        $errores[] = 'El campo lector no puede estar vacío';
    } elseif (mb_strlen($cuerpo['lector']) > 100) {
        $errores[] = 'El campo lector no puede superar los 100 caracteres';
    }

    if (!array_key_exists('puntaje', $cuerpo)) {
        $errores[] = 'El campo puntaje es obligatorio';
    } elseif (filter_var($cuerpo['puntaje'], FILTER_VALIDATE_INT) === false || $cuerpo['puntaje'] < 1 || $cuerpo['puntaje'] > 5) {
        $errores[] = 'El campo puntaje debe ser un entero entre 1 y 5';
    }

    if ($errores) {
        return ['ok' => false, 'detail' => implode('; ', $errores)];
    }

    return [
        'ok' => true,
        'datos' => [
            'libro_id' => (int) $cuerpo['libro_id'],
            'lector' => $cuerpo['lector'],
            'puntaje' => (int) $cuerpo['puntaje'],
            'comentario' => array_key_exists('comentario', $cuerpo) ? (string) $cuerpo['comentario'] : '',
        ],
    ];
}

/**
 * Valida el cuerpo de una actualización parcial (PATCH /api/resenas/{id}).
 * Solo se aceptan los campos lector, puntaje y comentario.
 *
 * @return array{ok: bool, detail?: string, datos?: array} Igual que validar_resena.
 */
function validar_patch(array $cuerpo): array
{
    $errores = [];
    $datos = [];

    if (array_key_exists('lector', $cuerpo)) {
        if (!is_string($cuerpo['lector']) || trim($cuerpo['lector']) === '') {
            $errores[] = 'El campo lector no puede estar vacío';
        } elseif (mb_strlen($cuerpo['lector']) > 100) {
            $errores[] = 'El campo lector no puede superar los 100 caracteres';
        } else {
            $datos['lector'] = $cuerpo['lector'];
        }
    }

    if (array_key_exists('puntaje', $cuerpo)) {
        if (filter_var($cuerpo['puntaje'], FILTER_VALIDATE_INT) === false || $cuerpo['puntaje'] < 1 || $cuerpo['puntaje'] > 5) {
            $errores[] = 'El campo puntaje debe ser un entero entre 1 y 5';
        } else {
            $datos['puntaje'] = (int) $cuerpo['puntaje'];
        }
    }

    if (array_key_exists('comentario', $cuerpo)) {
        $datos['comentario'] = (string) $cuerpo['comentario'];
    }

    if ($errores) {
        return ['ok' => false, 'detail' => implode('; ', $errores)];
    }
    if (!$datos) {
        return ['ok' => false, 'detail' => 'No se enviaron campos válidos para actualizar (lector, puntaje o comentario)'];
    }

    return ['ok' => true, 'datos' => $datos];
}

/**
 * Valida el cuerpo de un libro nuevo (POST /api/libros).
 * Los únicos campos obligatorios son titulo e isbn; el resto tiene default en
 * la tabla (disponible true, categoria '', anio_publicacion y paginas null).
 *
 * @return array{ok: bool, detail?: string, datos?: array} Igual que validar_resena.
 */
function validar_libro(array $cuerpo): array
{
    $errores = [];

    if (!array_key_exists('titulo', $cuerpo)) {
        $errores[] = 'El campo titulo es obligatorio';
    } elseif (!is_string($cuerpo['titulo']) || trim($cuerpo['titulo']) === '') {
        $errores[] = 'El campo titulo no puede estar vacío';
    }

    if (!array_key_exists('isbn', $cuerpo)) {
        $errores[] = 'El campo isbn es obligatorio';
    } elseif (!is_string($cuerpo['isbn']) || trim($cuerpo['isbn']) === '') {
        $errores[] = 'El campo isbn no puede estar vacío';
    }

    // Los campos numéricos admiten null (no se enviaron) o un entero.
    foreach (['anio_publicacion', 'paginas'] as $campo) {
        if (array_key_exists($campo, $cuerpo)
            && $cuerpo[$campo] !== null
            && filter_var($cuerpo[$campo], FILTER_VALIDATE_INT) === false) {
            $errores[] = 'El campo ' . $campo . ' debe ser un entero o null';
        }
    }

    if (array_key_exists('disponible', $cuerpo) && !is_bool($cuerpo['disponible'])) {
        $errores[] = 'El campo disponible debe ser un booleano';
    }

    if ($errores) {
        return ['ok' => false, 'detail' => implode('; ', $errores)];
    }

    return [
        'ok' => true,
        'datos' => [
            'titulo' => $cuerpo['titulo'],
            'isbn' => $cuerpo['isbn'],
            'anio_publicacion' => array_key_exists('anio_publicacion', $cuerpo) && $cuerpo['anio_publicacion'] !== null
                ? (int) $cuerpo['anio_publicacion']
                : null,
            'paginas' => array_key_exists('paginas', $cuerpo) && $cuerpo['paginas'] !== null
                ? (int) $cuerpo['paginas']
                : null,
            'disponible' => array_key_exists('disponible', $cuerpo) ? $cuerpo['disponible'] : true,
            'categoria' => array_key_exists('categoria', $cuerpo) ? (string) $cuerpo['categoria'] : '',
        ],
    ];
}

/**
 * Valida el cuerpo de una actualización de libro (PUT /api/libros/{id}).
 * Acepta cualquier subconjunto de los campos del libro (por eso se implementa
 * como PATCH contra PostgREST).
 *
 * @return array{ok: bool, detail?: string, datos?: array} Igual que validar_libro.
 */
function validar_put_libro(array $cuerpo): array
{
    $errores = [];
    $datos = [];

    if (array_key_exists('titulo', $cuerpo)) {
        if (!is_string($cuerpo['titulo']) || trim($cuerpo['titulo']) === '') {
            $errores[] = 'El campo titulo no puede estar vacío';
        } else {
            $datos['titulo'] = $cuerpo['titulo'];
        }
    }

    if (array_key_exists('isbn', $cuerpo)) {
        if (!is_string($cuerpo['isbn']) || trim($cuerpo['isbn']) === '') {
            $errores[] = 'El campo isbn no puede estar vacío';
        } else {
            $datos['isbn'] = $cuerpo['isbn'];
        }
    }

    foreach (['anio_publicacion', 'paginas'] as $campo) {
        if (array_key_exists($campo, $cuerpo)) {
            if ($cuerpo[$campo] !== null && filter_var($cuerpo[$campo], FILTER_VALIDATE_INT) === false) {
                $errores[] = 'El campo ' . $campo . ' debe ser un entero o null';
            } else {
                $datos[$campo] = $cuerpo[$campo] !== null ? (int) $cuerpo[$campo] : null;
            }
        }
    }

    if (array_key_exists('disponible', $cuerpo)) {
        if (!is_bool($cuerpo['disponible'])) {
            $errores[] = 'El campo disponible debe ser un booleano';
        } else {
            $datos['disponible'] = $cuerpo['disponible'];
        }
    }

    if (array_key_exists('categoria', $cuerpo)) {
        $datos['categoria'] = (string) $cuerpo['categoria'];
    }

    if ($errores) {
        return ['ok' => false, 'detail' => implode('; ', $errores)];
    }
    if (!$datos) {
        return ['ok' => false, 'detail' => 'No se enviaron campos válidos para actualizar (titulo, isbn, anio_publicacion, paginas, disponible o categoria)'];
    }

    return ['ok' => true, 'datos' => $datos];
}

/**
 * Lee y decodifica el body de la petición. Devuelve null si no es JSON válido.
 */
function leer_cuerpo(): ?array
{
    $cuerpo = json_decode(file_get_contents('php://input'), true);
    return is_array($cuerpo) ? $cuerpo : null;
}

// ---------------------------------------------------------------------------
// Operaciones del microservicio (el contrato /api/* de reseñas)
// ---------------------------------------------------------------------------

function salud(): void
{
    // Health check: la plataforma lo usa para saber si el servicio está vivo.
    responder_json(200, ['estado' => 'ok']);
}

function listar_resenas(): void
{
    // Todas las reseñas, de la más nueva a la más vieja.
    $respuesta = llamar_supabase('GET', '/resenas?select=*&order=creada_en.desc');
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $resenas = $respuesta['datos'] ?? [];
    responder_json(200, ['cantidad' => count($resenas), 'resenas' => $resenas]);
}

function resenas_de_libro(int $libro_id): void
{
    // Reseñas de un libro con su promedio de puntaje (el que consume Django).
    $respuesta = llamar_supabase(
        'GET',
        '/resenas?select=*&libro_id=eq.' . $libro_id . '&order=creada_en.desc'
    );
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $resenas = $respuesta['datos'] ?? [];
    $promedio = null;
    if ($resenas) {
        $suma = 0;
        foreach ($resenas as $resena) {
            $suma += (int) $resena['puntaje'];
        }
        $promedio = round($suma / count($resenas), 2);
    }

    responder_json(200, [
        'libro_id' => $libro_id,
        'cantidad' => count($resenas),
        'promedio' => $promedio,
        'resenas' => $resenas,
    ]);
}

function crear_resena(): void
{
    // Inserta una reseña nueva y la devuelve ya guardada (status 201).
    $cuerpo = leer_cuerpo();
    if ($cuerpo === null) {
        responder_json(422, ['detail' => 'El cuerpo debe ser un JSON válido']);
    }

    $validacion = validar_resena($cuerpo);
    if (!$validacion['ok']) {
        responder_json(422, ['detail' => $validacion['detail']]);
    }

    $respuesta = llamar_supabase('POST', '/resenas', $validacion['datos']);
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $resenas = $respuesta['datos'] ?? [];
    if (!$resenas) {
        responder_json(502, ['detail' => 'Supabase no devolvió la fila insertada']);
    }

    responder_json(201, $resenas[0]);
}

function actualizar_resena(int $id): void
{
    // Actualiza parcialmente una reseña y devuelve la fila ya modificada.
    $cuerpo = leer_cuerpo();
    if ($cuerpo === null) {
        responder_json(422, ['detail' => 'El cuerpo debe ser un JSON válido']);
    }

    $validacion = validar_patch($cuerpo);
    if (!$validacion['ok']) {
        responder_json(422, ['detail' => $validacion['detail']]);
    }

    $respuesta = llamar_supabase('PATCH', '/resenas?id=eq.' . $id, $validacion['datos']);
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $resenas = $respuesta['datos'] ?? [];
    if (!$resenas) {
        responder_json(404, ['detail' => 'No existe una reseña con id ' . $id]);
    }

    responder_json(200, $resenas[0]);
}

function eliminar_resena(int $id): void
{
    // Borra una reseña y devuelve la fila borrada.
    $respuesta = llamar_supabase('DELETE', '/resenas?id=eq.' . $id);
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $resenas = $respuesta['datos'] ?? [];
    if (!$resenas) {
        responder_json(404, ['detail' => 'No existe una reseña con id ' . $id]);
    }

    responder_json(200, $resenas[0]);
}

// ---------------------------------------------------------------------------
// Operaciones de libros (CRUD de la tabla `libros`)
// ---------------------------------------------------------------------------

function listar_libros(): void
{
    // Todos los libros, del más nuevo al más viejo.
    $respuesta = llamar_supabase('GET', '/libros?select=*&order=creada_en.desc');
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $libros = $respuesta['datos'] ?? [];
    responder_json(200, ['cantidad' => count($libros), 'libros' => $libros]);
}

function obtener_libro(int $id): void
{
    // Un libro puntual por su id.
    $respuesta = llamar_supabase('GET', '/libros?select=*&id=eq.' . $id);
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $libros = $respuesta['datos'] ?? [];
    if (!$libros) {
        responder_json(404, ['detail' => 'Ruta no encontrada']);
    }

    responder_json(200, $libros[0]);
}

function crear_libro(): void
{
    // Inserta un libro nuevo y lo devuelve ya guardado (status 201).
    $cuerpo = leer_cuerpo();
    if ($cuerpo === null) {
        responder_json(422, ['detail' => 'El cuerpo debe ser un JSON válido']);
    }

    $validacion = validar_libro($cuerpo);
    if (!$validacion['ok']) {
        responder_json(422, ['detail' => $validacion['detail']]);
    }

    $respuesta = llamar_supabase('POST', '/libros', $validacion['datos']);
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $libros = $respuesta['datos'] ?? [];
    if (!$libros) {
        responder_json(502, ['detail' => 'Supabase no devolvió la fila insertada']);
    }

    responder_json(201, $libros[0]);
}

function actualizar_libro(int $id): void
{
    // Actualiza con cualquier subconjunto de campos y devuelve la fila ya modificada.
    $cuerpo = leer_cuerpo();
    if ($cuerpo === null) {
        responder_json(422, ['detail' => 'El cuerpo debe ser un JSON válido']);
    }

    $validacion = validar_put_libro($cuerpo);
    if (!$validacion['ok']) {
        responder_json(422, ['detail' => $validacion['detail']]);
    }

    $respuesta = llamar_supabase('PATCH', '/libros?id=eq.' . $id, $validacion['datos']);
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $libros = $respuesta['datos'] ?? [];
    if (!$libros) {
        responder_json(404, ['detail' => 'No existe un libro con id ' . $id]);
    }

    responder_json(200, $libros[0]);
}

function eliminar_libro(int $id): void
{
    // Borra un libro y devuelve la fila borrada.
    $respuesta = llamar_supabase('DELETE', '/libros?id=eq.' . $id);
    if ($respuesta['error'] !== null) {
        responder_error_supabase($respuesta);
    }

    $libros = $respuesta['datos'] ?? [];
    if (!$libros) {
        responder_json(404, ['detail' => 'No existe un libro con id ' . $id]);
    }

    responder_json(200, $libros[0]);
}

// ---------------------------------------------------------------------------
// Documentación (Swagger UI)
// ---------------------------------------------------------------------------

function documentacion_swagger(): void
{
    // Página HTML de Swagger UI: carga la spec OpenAPI desde /api/openapi.json.
    // Sin Composer ni librerías locales: el CSS y el JS vienen del CDN de unpkg.
    header('Content-Type: text/html; charset=utf-8');
    echo <<<HTML
<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>API - Swagger UI</title>
  <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
</head>
<body>
  <div id="swagger-ui"></div>
  <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
  <script>
    window.onload = () => {
      window.ui = SwaggerUIBundle({
        url: "/api/openapi.json",
        dom_id: "#swagger-ui",
        deepLinking: true,
      });
    };
  </script>
</body>
</html>
HTML;
    exit;
}

function openapi_json(): void
{
    // Sirve la spec OpenAPI 3.0 del contrato completo (salud, libros y reseñas).
    // __DIR__ hace que funcione tanto local (php -S router.php) como en Vercel,
    // donde el directorio de trabajo puede no ser la carpeta del router.
    $contenido = @file_get_contents(__DIR__ . '/openapi.json');
    if ($contenido === false) {
        responder_json(500, ['detail' => 'No se pudo leer el archivo openapi.json']);
    }

    header('Content-Type: application/json; charset=utf-8');
    echo $contenido;
    exit;
}

// ---------------------------------------------------------------------------
// Router: enruta la petición según método y ruta
// ---------------------------------------------------------------------------

$metodo = $_SERVER['REQUEST_METHOD'];
$ruta = parse_url($_SERVER['REQUEST_URI'], PHP_URL_PATH);

if ($SIN_CONFIGURACION) {
    responder_json(500, ['detail' => 'Falta SUPABASE_URL o SUPABASE_SERVICE_KEY en las variables de entorno']);
}

if ($metodo === 'GET' && $ruta === '/api/salud') {
    salud();
}

if ($metodo === 'GET' && $ruta === '/api/docs') {
    documentacion_swagger();
}

if ($metodo === 'GET' && $ruta === '/api/openapi.json') {
    openapi_json();
}

if ($metodo === 'GET' && $ruta === '/api/resenas') {
    listar_resenas();
}

if ($metodo === 'GET' && preg_match('#^/api/libros/(\d+)/resenas$#', $ruta, $partes)) {
    resenas_de_libro((int) $partes[1]);
}

if ($metodo === 'POST' && $ruta === '/api/resenas') {
    crear_resena();
}

if ($metodo === 'PATCH' && preg_match('#^/api/resenas/(\d+)$#', $ruta, $partes)) {
    actualizar_resena((int) $partes[1]);
}

if ($metodo === 'DELETE' && preg_match('#^/api/resenas/(\d+)$#', $ruta, $partes)) {
    eliminar_resena((int) $partes[1]);
}

if ($metodo === 'GET' && $ruta === '/api/libros') {
    listar_libros();
}

if ($metodo === 'GET' && preg_match('#^/api/libros/(\d+)$#', $ruta, $partes)) {
    obtener_libro((int) $partes[1]);
}

if ($metodo === 'POST' && $ruta === '/api/libros') {
    crear_libro();
}

if ($metodo === 'PUT' && preg_match('#^/api/libros/(\d+)$#', $ruta, $partes)) {
    actualizar_libro((int) $partes[1]);
}

if ($metodo === 'DELETE' && preg_match('#^/api/libros/(\d+)$#', $ruta, $partes)) {
    eliminar_libro((int) $partes[1]);
}

responder_json(404, ['detail' => 'Ruta no encontrada']);