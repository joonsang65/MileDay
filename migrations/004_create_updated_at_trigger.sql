-- 수정했을 때 수정 시점을 업데이트 --
create or replace function public.set_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;


-- goals 테이블 수정 시점에 set_updated_at 동작하게 함 --
drop trigger if exists set_goals_updated_at on public.goals;
create trigger set_goals_updated_at
before update on public.goals
for each row
execute function public.set_updated_at();

-- milestones 테이블 수정 시점에 set_updated_at 동작하게 함 --
drop trigger if exists set_milestones_updated_at on public.milestones;
create trigger set_milestones_updated_at
before update on public.milestones
for each row
execute function public.set_updated_at();

