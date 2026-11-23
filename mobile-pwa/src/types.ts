import type { CalendarMilestoneSummary, Goal as CalendarGoal } from "../../shared/calendar-month.generated";

export type { CalendarMonthData } from "../../shared/calendar-month.generated";

export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
};

export type AuthSession = {
  access_token: string;
  refresh_token: string;
  expires_at: number;
  token_type: "bearer";
  user: {
    id: string;
    email: string;
  };
};

export type Goal = CalendarGoal;

export type Milestone = CalendarMilestoneSummary;

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
