create or replace function public.complete_goal_with_milestones(
  p_goal_id uuid,
  p_user_id uuid,
  p_is_completed boolean
)
returns table (
  id uuid,
  user_id uuid,
  title text,
  deadline date,
  is_completed boolean,
  is_recurring boolean,
  recurrence_type text,
  color text,
  created_at timestamptz,
  updated_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
begin
  update public.goals as g
  set is_completed = p_is_completed
  where g.id = p_goal_id
    and g.user_id = p_user_id;

  if not found then
    return;
  end if;

  update public.milestones as m
  set is_completed = p_is_completed
  where m.goal_id = p_goal_id
    and m.user_id = p_user_id;

  return query
  select
    g.id,
    g.user_id,
    g.title,
    g.deadline,
    g.is_completed,
    g.is_recurring,
    g.recurrence_type,
    g.color,
    g.created_at,
    g.updated_at
  from public.goals as g
  where g.id = p_goal_id
    and g.user_id = p_user_id;
end;
$$;

create or replace function public.complete_milestone_and_sync_goal(
  p_milestone_id uuid,
  p_user_id uuid,
  p_is_completed boolean
)
returns table (
  id uuid,
  goal_id uuid,
  user_id uuid,
  title text,
  color text,
  scheduled_date date,
  is_completed boolean,
  created_at timestamptz,
  updated_at timestamptz
)
language plpgsql
security definer
set search_path = public
as $$
declare
  v_goal_id uuid;
begin
  update public.milestones as m
  set is_completed = p_is_completed
  where m.id = p_milestone_id
    and m.user_id = p_user_id
  returning m.goal_id into v_goal_id;

  if v_goal_id is null then
    return;
  end if;

  update public.goals as g
  set is_completed = not exists (
    select 1
    from public.milestones as m
    where m.goal_id = v_goal_id
      and m.user_id = p_user_id
      and m.is_completed is not true
  )
  where g.id = v_goal_id
    and g.user_id = p_user_id;

  return query
  select
    m.id,
    m.goal_id,
    m.user_id,
    m.title,
    m.color,
    m.scheduled_date,
    m.is_completed,
    m.created_at,
    m.updated_at
  from public.milestones as m
  where m.id = p_milestone_id
    and m.user_id = p_user_id;
end;
$$;

revoke all on function public.complete_goal_with_milestones(uuid, uuid, boolean)
from public, anon, authenticated;

revoke all on function public.complete_milestone_and_sync_goal(uuid, uuid, boolean)
from public, anon, authenticated;

grant execute on function public.complete_goal_with_milestones(uuid, uuid, boolean)
to service_role;

grant execute on function public.complete_milestone_and_sync_goal(uuid, uuid, boolean)
to service_role;

notify pgrst, 'reload schema';
