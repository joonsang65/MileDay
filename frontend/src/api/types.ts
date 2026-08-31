export type ApiEnvelope<T> = {
  success: boolean;
  data: T;
};

export type ApiErrorEnvelope = {
  success: false;
  error: {
    code: string;
    message: string;
    detail?: unknown;
  };
  request_id?: string;
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

export type SignUpResult = {
  user_id: string;
  email: string;
};

export type Goal = {
  id: string;
  user_id?: string | null;
  title: string;
  deadline: string;
  is_completed: boolean;
  is_recurring: boolean;
  recurrence_type: "daily" | "weekly" | "monthly" | null;
  color: string;
  created_at: string;
  updated_at: string;
};

export type GoalWithMilestones = Goal & {
  milestones: Milestone[];
};

export type RecurrenceType = "daily" | "weekly" | "monthly";

export type GoalCreatePayload = {
  title: string;
  deadline: string;
  is_completed?: boolean;
  is_recurring: boolean;
  recurrence_type: RecurrenceType | null;
  color: string;
};

export type GoalUpdatePayload = Partial<GoalCreatePayload>;

export type Milestone = {
  id: string;
  goal_id: string;
  user_id?: string;
  goal_title?: string | null;
  title: string;
  color: string;
  scheduled_date: string;
  is_completed: boolean;
  created_at?: string;
  updated_at?: string;
};

export type MilestoneCreatePayload = {
  title: string;
  scheduled_date: string;
  color?: string;
};

export type MilestoneUpdatePayload = Partial<MilestoneCreatePayload> & {
  is_completed?: boolean;
};

export type CalendarView = "month" | "week";
export type HolidayDisplay = "normal" | "weekend_like" | "hidden";
export type Language = "ko" | "en";

export type UserSettings = {
  calendar_view: CalendarView;
  holiday_display: HolidayDisplay;
  week_starts_on: 0 | 1;
  language: Language;
  timezone: string;
  gemini_data_consent: boolean;
};

export type UserSettingsUpdatePayload = Partial<UserSettings>;

export type CalendarDay = {
  date: string;
  is_today: boolean;
  is_holiday?: boolean;
  holiday_name?: string | null;
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

export type CalendarWeekData = {
  start_date: string;
  end_date: string;
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

export type AiScheduleAvailability = {
  date: string;
  available_minutes: number;
};

export type AiScheduleDraftRequest = {
  prompt: string;
  today: string;
  timezone: string;
  availability: AiScheduleAvailability[];
};

export type AiScheduleDraftMilestone = {
  client_id: string;
  title: string;
  scheduled_date: string;
  selected: boolean;
};

export type AiScheduleDraft = {
  goal: {
    title: string;
    deadline: string;
  };
  milestones: AiScheduleDraftMilestone[];
  planning_preference: {
    intensity: "relaxed" | "balanced" | "intensive";
    preferred_days: string[];
  };
  validation: {
    is_valid: boolean;
    failure_codes: string[];
    warnings: string[];
  };
  create_goal_payload: {
    goal: GoalCreatePayload;
    milestones: (MilestoneCreatePayload & { is_completed?: boolean })[];
    write_policy: "user_confirmation_required";
  };
};
