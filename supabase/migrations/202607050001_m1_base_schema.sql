create extension if not exists pgcrypto;

-- updated_at 자동 갱신 공통 트리거 함수
create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

-- 목표 테이블: 사용자별 목표와 반복 설정
create table if not exists public.goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  deadline date not null,
  is_recurring boolean not null default false,
  recurrence_type text,
  color text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 마일스톤 테이블: 목표 하위 일정 단위
create table if not exists public.milestones (
  id uuid primary key default gen_random_uuid(),
  goal_id uuid not null references public.goals(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  color text not null,
  scheduled_date date not null,
  is_completed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- milestone.user_id와 goal.user_id 일치 보장
create or replace function public.ensure_milestone_goal_owner()
returns trigger
language plpgsql
as $$
begin
  if not exists (
    select 1
    from public.goals
    where goals.id = new.goal_id
      and goals.user_id = new.user_id
  ) then
    raise exception 'milestone user_id must match goal user_id';
  end if;
  return new;
end;
$$;

-- 사용자별 화면/일정 기본 설정
create table if not exists public.user_settings (
  user_id uuid primary key references auth.users(id) on delete cascade,
  calendar_view text not null default 'month',
  theme text not null default 'system',
  accent_color text not null default '#4F46E5',
  font_family text not null default 'system',
  font_size integer not null default 14,
  ai_suggestion boolean not null default false,
  holiday_display text not null default 'normal',
  week_starts_on integer not null default 1,
  completed_milestones boolean not null default true,
  default_goal_color text not null default '#4F46E5',
  default_milestone_color text not null default '#F97316',
  language text not null default 'ko',
  timezone text not null default 'Asia/Seoul',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- 사용자/목표/날짜 기준 조회 최적화
create index if not exists goals_user_id_idx on public.goals(user_id);
create index if not exists milestones_user_id_idx on public.milestones(user_id);
create index if not exists milestones_goal_id_idx on public.milestones(goal_id);
create index if not exists milestones_scheduled_date_idx on public.milestones(scheduled_date);

-- updated_at trigger 재생성으로 migration 재실행 안정성 확보
drop trigger if exists set_goals_updated_at on public.goals;
create trigger set_goals_updated_at
before update on public.goals
for each row execute function public.set_updated_at();

drop trigger if exists set_milestones_updated_at on public.milestones;
create trigger set_milestones_updated_at
before update on public.milestones
for each row execute function public.set_updated_at();

drop trigger if exists ensure_milestone_goal_owner on public.milestones;
create trigger ensure_milestone_goal_owner
before insert or update of goal_id, user_id on public.milestones
for each row execute function public.ensure_milestone_goal_owner();

drop trigger if exists set_user_settings_updated_at on public.user_settings;
create trigger set_user_settings_updated_at
before update on public.user_settings
for each row execute function public.set_updated_at();

-- RLS 기준: auth.uid() = user_id
alter table public.goals enable row level security;
alter table public.milestones enable row level security;
alter table public.user_settings enable row level security;

-- goals 소유자 전용 접근 정책
drop policy if exists goals_select_own on public.goals;
create policy goals_select_own on public.goals
for select using (auth.uid() = user_id);

drop policy if exists goals_insert_own on public.goals;
create policy goals_insert_own on public.goals
for insert with check (auth.uid() = user_id);

drop policy if exists goals_update_own on public.goals;
create policy goals_update_own on public.goals
for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists goals_delete_own on public.goals;
create policy goals_delete_own on public.goals
for delete using (auth.uid() = user_id);

-- milestones 소유자 전용 접근 정책
drop policy if exists milestones_select_own on public.milestones;
create policy milestones_select_own on public.milestones
for select using (auth.uid() = user_id);

drop policy if exists milestones_insert_own on public.milestones;
create policy milestones_insert_own on public.milestones
for insert with check (auth.uid() = user_id);

drop policy if exists milestones_update_own on public.milestones;
create policy milestones_update_own on public.milestones
for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists milestones_delete_own on public.milestones;
create policy milestones_delete_own on public.milestones
for delete using (auth.uid() = user_id);

-- user_settings 소유자 전용 접근 정책
drop policy if exists user_settings_select_own on public.user_settings;
create policy user_settings_select_own on public.user_settings
for select using (auth.uid() = user_id);

drop policy if exists user_settings_insert_own on public.user_settings;
create policy user_settings_insert_own on public.user_settings
for insert with check (auth.uid() = user_id);

drop policy if exists user_settings_update_own on public.user_settings;
create policy user_settings_update_own on public.user_settings
for update using (auth.uid() = user_id) with check (auth.uid() = user_id);

drop policy if exists user_settings_delete_own on public.user_settings;
create policy user_settings_delete_own on public.user_settings
for delete using (auth.uid() = user_id);
