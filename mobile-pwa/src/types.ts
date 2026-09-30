export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  user: {
    id: string;
    email: string;
  };
};

export type Goal = {
  id: string;
  title: string;
  deadline: string;
  is_completed: boolean;
  is_recurring: boolean;
  recurrence_type: "daily" | "weekly" | "monthly" | null;
  color: string;
  created_at: string;
  updated_at: string;
};

export type Milestone = {
  id: string;
  goal_id: string;
  goal_title?: string | null;
  title: string;
  color: string;
  scheduled_date: string;
  is_completed: boolean;
};

export type CalendarDay = {
  date: string;
  is_today: boolean;
  goal_count: number;
  milestone_count: number;
  completed_milestone_count: number;
  goals: Goal[];
  milestones: Milestone[];
};

export type CalendarMonthData = {
  year: number;
  month: number;
  days: CalendarDay[];
  goals: Goal[];
  milestones: Milestone[];
};

export type CalendarDateData = {
  date: string;
  is_today: boolean;
  goal_count: number;
  milestone_count: number;
  completed_milestone_count: number;
  goals: Goal[];
  milestones: Milestone[];
};

export type NotificationSettings = {
  user_id: string;
  enabled: boolean;
  notification_time: string;
  timezone: string;
};

export type PushConfig = {
  vapid_public_key: string | null;
  configured: boolean;
};
