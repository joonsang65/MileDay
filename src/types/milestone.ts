export interface Milestone {
  id: string;
  goal_id: string;
  user_id: string;
  title: string;
  scheduled_date: string;
  is_completed: boolean;
  created_at: string;
  updated_at: string;
}

export interface CreateMilestoneInput {
  goal_id: string;
  title: string;
  scheduled_date: string;
}

export interface UpdateMilestoneInput {
  title?: string;
  scheduled_date?: string;
  is_completed?: boolean;
}

