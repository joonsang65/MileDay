alter table if exists public.goals
  add column if not exists is_completed boolean not null default false;

notify pgrst, 'reload schema';
