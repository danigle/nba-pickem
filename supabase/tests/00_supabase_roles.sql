-- CI only: the roles Supabase provides, so migrations run on plain Postgres.
create role anon nologin;
create role authenticated nologin;
grant usage on schema public to anon, authenticated;
