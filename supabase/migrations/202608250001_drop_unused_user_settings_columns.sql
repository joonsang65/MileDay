alter table if exists public.user_settings
  drop column if exists theme,
  drop column if exists accent_color,
  drop column if exists font_family,
  drop column if exists font_size,
  drop column if exists ai_suggestion,
  drop column if exists completed_milestones,
  drop column if exists default_goal_color,
  drop column if exists default_milestone_color;

notify pgrst, 'reload schema';
