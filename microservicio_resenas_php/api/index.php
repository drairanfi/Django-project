<?php

declare(strict_types=1);

/*
 * Entrypoint de Vercel para el microservicio de PHP.
 *
 * Vercel es serverless: no hay un `php -S` que escuche en un puerto. vercel-php
 * ejecuta este archivo por cada request y deja las superglobales ($_SERVER,
 * php://input) igual que el servidor embebido. Acá se reutiliza todo el router
 * local, que enruta /api/* según método y ruta.
 *
 * En local no se usa: se corre `php -S 127.0.0.1:8004 router.php`.
 */
require __DIR__ . '/../router.php';