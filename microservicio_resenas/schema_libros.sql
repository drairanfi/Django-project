-- Tabla de libros en Supabase (PostgreSQL) para el CRUD de libros via microservicio.
-- Pegá este script en el SQL Editor de Supabase y ejecutalo.
-- Comparte la base con la tabla `resenas`: ambos datos viven fuera de SQLite.

create table if not exists public.libros (
    id                bigint generated always as identity primary key,
    titulo            text        not null,
    isbn              text        not null unique,
    anio_publicacion  integer,
    paginas           integer,
    disponible        boolean     not null default true,
    categoria         text        not null default '',
    autores           text        not null default '',
    creada_en         timestamptz not null default now()
);

-- Row Level Security activado y SIN políticas públicas: nadie lee ni escribe
-- con la clave anónima. Solo los microservicios, que usan la service_role key
-- guardada como variable de entorno, atraviesan RLS.
alter table public.libros enable row level security;