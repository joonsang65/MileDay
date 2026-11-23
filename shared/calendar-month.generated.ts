export type CalendarMonthResponse = {
  success: boolean;
  data: CalendarMonthData;
};

export type CalendarMonthData = {
  year: number;
  month: number;
  days: Array<CalendarDayData>;
  goals: Array<Goal>;
  milestones: Array<Milestone>;
};

export type CalendarDayData = {
  date: string;
  is_today: boolean;
  is_holiday?: boolean;
  holiday_name?: string | null;
  goal_count: number;
  milestone_count: number;
  completed_milestone_count: number;
  goals: Array<Goal>;
  milestones: Array<CalendarMilestoneSummary>;
};

export type Goal = {
  title: string;
  deadline: string;
  is_completed?: boolean;
  is_recurring?: boolean;
  recurrence_type?: "daily" | "weekly" | "monthly" | null;
  color: string;
  id: string;
  user_id?: string | null;
  created_at: string;
  updated_at: string;
};

export type Milestone = {
  title: string;
  color?: string | null;
  scheduled_date: string;
  id: string;
  goal_id: string;
  user_id: string;
  goal_title?: string | null;
  is_completed: boolean;
  created_at: string;
  updated_at: string;
};

export type CalendarMilestoneSummary = {
  id: string;
  goal_id: string;
  goal_title?: string | null;
  title: string;
  color: string;
  scheduled_date: string;
  is_completed: boolean;
};
