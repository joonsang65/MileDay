alter table if exists public.user_settings
  add column if not exists gemini_data_consent boolean not null default false;

alter table if exists public.user_settings
  alter column week_starts_on set default 0;
