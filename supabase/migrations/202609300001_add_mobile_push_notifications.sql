create table if not exists public.push_subscriptions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  endpoint text not null,
  p256dh text not null,
  auth text not null,
  user_agent text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  last_used_at timestamptz
);

create table if not exists public.notification_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  enabled boolean not null default false,
  notification_time time not null default '08:00',
  timezone text not null default 'Asia/Seoul',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.notification_delivery_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  delivery_date date not null,
  notification_type text not null,
  sent_at timestamptz not null default now()
);

create unique index if not exists push_subscriptions_user_endpoint_key
  on public.push_subscriptions(user_id, endpoint);

create index if not exists push_subscriptions_user_id_idx
  on public.push_subscriptions(user_id);

create index if not exists notification_settings_enabled_idx
  on public.notification_settings(enabled);

create unique index if not exists notification_delivery_log_once_per_day_key
  on public.notification_delivery_log(user_id, delivery_date, notification_type);

drop trigger if exists set_push_subscriptions_updated_at on public.push_subscriptions;
create trigger set_push_subscriptions_updated_at
before update on public.push_subscriptions
for each row execute function public.set_updated_at();

drop trigger if exists set_notification_settings_updated_at on public.notification_settings;
create trigger set_notification_settings_updated_at
before update on public.notification_settings
for each row execute function public.set_updated_at();

alter table public.push_subscriptions enable row level security;
alter table public.notification_settings enable row level security;
alter table public.notification_delivery_log enable row level security;

drop policy if exists push_subscriptions_select_own on public.push_subscriptions;
create policy push_subscriptions_select_own on public.push_subscriptions
for select using (auth.uid() = user_id);

drop policy if exists push_subscriptions_insert_own on public.push_subscriptions;
create policy push_subscriptions_insert_own on public.push_subscriptions
for insert with check (auth.uid() = user_id);

drop policy if exists push_subscriptions_update_own on public.push_subscriptions;
create policy push_subscriptions_update_own on public.push_subscriptions
for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists push_subscriptions_delete_own on public.push_subscriptions;
create policy push_subscriptions_delete_own on public.push_subscriptions
for delete using (auth.uid() = user_id);

drop policy if exists notification_settings_select_own on public.notification_settings;
create policy notification_settings_select_own on public.notification_settings
for select using (auth.uid() = user_id);

drop policy if exists notification_settings_insert_own on public.notification_settings;
create policy notification_settings_insert_own on public.notification_settings
for insert with check (auth.uid() = user_id);

drop policy if exists notification_settings_update_own on public.notification_settings;
create policy notification_settings_update_own on public.notification_settings
for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists notification_delivery_log_select_own on public.notification_delivery_log;
create policy notification_delivery_log_select_own on public.notification_delivery_log
for select using (auth.uid() = user_id);
