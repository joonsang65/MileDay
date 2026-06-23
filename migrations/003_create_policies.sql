-- 본인 목표 데이터에만 접근 가능 --
create policy "Users can view their own goals"
on public.goals
for select
using (auth.uid() = user_id);

-- 본인 목표 데이터만 추가 가능 --
create policy "Users can insert their own goals"
on public.goals
for insert
with check (auth.uid() = user_id);

-- 본인 목표 데이터만 수정 가능 --
create policy "Users can update their own goals"
on public.goals
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

-- 본인 목표 데이터만 삭제 가능 --
create policy "Users can delete their own goals"
on public.goals
for delete
using (auth.uid() = user_id);


-- 본인 마일스톤만 접근 가능 --
create policy "Users can view their own milestones"
on public.milestones
for select
using (auth.uid() = user_id);

-- 본인 마일스톤만 추가 가능 --
create policy "Users can insert their own milestones"
on public.milestones
for insert
with check (auth.uid() = user_id);

-- 본인 마일스톤만 수정 가능 --
create policy "Users can update their own milestones"
on public.milestones
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

-- 본인 마일스톤만 삭제 가능 --
create policy "Users can delete their own milestones"
on public.milestones
for delete
using (auth.uid() = user_id);

