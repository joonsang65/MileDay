-- 반복하지 않는 목표는 recurrence_type을 null로 저장하는 것이 앱 계약이다.
-- 기존 DB에 남아 있을 수 있는 NOT NULL 제약을 제거한다.
alter table if exists public.goals
alter column recurrence_type drop not null;

-- 반복 여부와 반복 유형의 조합을 DB에서도 백엔드 검증과 동일하게 보장한다.
do $$
begin
  if not exists (
    select 1
    from pg_constraint
    where conname = 'goals_recurrence_type_state'
      and conrelid = 'public.goals'::regclass
  ) then
    alter table public.goals
    add constraint goals_recurrence_type_state
    check (
      (is_recurring = true and recurrence_type in ('daily', 'weekly', 'monthly'))
      or
      (is_recurring = false and recurrence_type is null)
    );
  end if;
end;
$$;

-- Supabase REST(PostgREST)가 제약/컬럼 변경을 바로 인식하도록 schema cache를 갱신한다.
notify pgrst, 'reload schema';
