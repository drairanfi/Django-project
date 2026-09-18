-- Tabla de reseñas en Supabase (PostgreSQL).
-- Pegá este script en el SQL Editor de Supabase y ejecutalo.

create table if not exists public.resenas (
    id          bigint generated always as identity primary key,
    libro_id    integer     not null,
    lector      text        not null,
    puntaje     integer     not null check (puntaje between 1 and 5),
    comentario  text        not null default '',
    creada_en   timestamptz not null default now()
);

-- El filtro más frecuente es por libro_id, así que lleva índice.
create index if not exists resenas_libro_id_idx on public.resenas (libro_id);

-- Row Level Security activado y SIN políticas públicas: nadie puede leer ni
-- escribir con la clave anónima. Solo el microservicio, que usa la service_role
-- key guardada como variable de entorno en Render, atraviesa RLS.
alter table public.resenas enable row level security;
