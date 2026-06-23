create policy "Users can view their own goals"
on public.goals
for select
using (auth.uid() = user_id);

create policy "Users can insert their own goals"
on public.goals
for insert
with check (auth.uid() = user_id);

create policy "Users can update their own goals"
on public.goals
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can delete their own goals"
on public.goals
for delete
using (auth.uid() = user_id);

create policy "Users can view their own milestones"
on public.milestones
for select
using (auth.uid() = user_id);

create policy "Users can insert their own milestones"
on public.milestones
for insert
with check (auth.uid() = user_id);

create policy "Users can update their own milestones"
on public.milestones
for update
using (auth.uid() = user_id)
with check (auth.uid() = user_id);

create policy "Users can delete their own milestones"
on public.milestones
for delete
using (auth.uid() = user_id);

