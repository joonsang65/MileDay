export type RecurrenceType = 'none' | 'weekly' | 'monthly';

export interface Goal {
  id: string;
  user_id: string;
  title: string;
  deadline: string;
  is_recurring: boolean;
  recurrence_type: RecurrenceType;
  created_at: string;
  updated_at: string;
}

export interface CreateGoalInput {
  title: string;
  deadline: string;
  is_recurring: boolean;
  recurrence_type: RecurrenceType;
}

export interface UpdateGoalInput {
  title?: string;
  deadline?: string;
  is_recurring?: boolean;
  recurrence_type?: RecurrenceType;
}

