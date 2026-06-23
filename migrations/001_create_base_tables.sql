create table if not exists public.goals (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  deadline date not null,
  is_recurring boolean not null default false,
  recurrence_type text not null default 'none',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint goals_recurrence_type_check
    check (recurrence_type in ('none', 'weekly', 'monthly')),
  constraint goals_recurring_consistency_check
    check (
      (is_recurring = false and recurrence_type = 'none')
      or
      (is_recurring = true and recurrence_type in ('weekly', 'monthly'))
    )
);

create table if not exists public.milestones (
  id uuid primary key default gen_random_uuid(),
  goal_id uuid not null references public.goals(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  title text not null,
  scheduled_date date not null,
  is_completed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists idx_goals_user_id
on public.goals(user_id);

create index if not exists idx_goals_deadline
on public.goals(deadline);

create index if not exists idx_milestones_user_id
on public.milestones(user_id);

create index if not exists idx_milestones_goal_id
on public.milestones(goal_id);

create index if not exists idx_milestones_scheduled_date
on public.milestones(scheduled_date);

