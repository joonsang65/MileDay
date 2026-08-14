create index if not exists idx_goals_user_deadline
on public.goals (user_id, deadline);

create index if not exists idx_milestones_user_scheduled_date
on public.milestones (user_id, scheduled_date);

create index if not exists idx_milestones_user_goal
on public.milestones (user_id, goal_id);
