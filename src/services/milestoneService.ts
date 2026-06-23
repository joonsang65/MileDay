import { getTodayDateString, normalizeDateString } from '../lib/date';
import { supabase } from '../lib/supabase';
import type {
  CreateMilestoneInput,
  Milestone,
  UpdateMilestoneInput,
} from '../types/milestone';
import { getCurrentUser } from './authService';

const validateTitle = (title: string): string => {
  const normalized = title.trim();

  if (!normalized) {
    throw new Error('Milestone title is required.');
  }

  return normalized;
};

const normalizeCreateMilestoneInput = (
  input: CreateMilestoneInput,
): CreateMilestoneInput => {
  const goalId = input.goal_id.trim();

  if (!goalId) {
    throw new Error('Goal id is required.');
  }

  return {
    goal_id: goalId,
    title: validateTitle(input.title),
    scheduled_date: normalizeDateString(input.scheduled_date),
  };
};

const normalizeUpdateMilestoneInput = (
  input: UpdateMilestoneInput,
): UpdateMilestoneInput => {
  const output: UpdateMilestoneInput = {};

  if (input.title !== undefined) {
    output.title = validateTitle(input.title);
  }

  if (input.scheduled_date !== undefined) {
    output.scheduled_date = normalizeDateString(input.scheduled_date);
  }

  if (input.is_completed !== undefined) {
    output.is_completed = input.is_completed;
  }

  return output;
};

export const getMilestones = async (): Promise<Milestone[]> => {
  await getCurrentUser();

  const { data, error } = await supabase
    .from('milestones')
    .select('*')
    .order('scheduled_date', { ascending: true })
    .order('created_at', { ascending: true });

  if (error) {
    throw error;
  }

  return data ?? [];
};

export const getMilestonesByGoal = async (
  goalId: string,
): Promise<Milestone[]> => {
  await getCurrentUser();

  const { data, error } = await supabase
    .from('milestones')
    .select('*')
    .eq('goal_id', goalId)
    .order('scheduled_date', { ascending: true })
    .order('created_at', { ascending: true });

  if (error) {
    throw error;
  }

  return data ?? [];
};

export const getMilestonesByDate = async (
  date: string,
): Promise<Milestone[]> => {
  await getCurrentUser();
  const scheduledDate = normalizeDateString(date);

  const { data, error } = await supabase
    .from('milestones')
    .select('*')
    .eq('scheduled_date', scheduledDate)
    .order('created_at', { ascending: true });

  if (error) {
    throw error;
  }

  return data ?? [];
};

export const getTodayMilestones = async (): Promise<Milestone[]> =>
  getMilestonesByDate(getTodayDateString());

export const createMilestone = async (
  input: CreateMilestoneInput,
): Promise<Milestone> => {
  const user = await getCurrentUser();
  const normalizedInput = normalizeCreateMilestoneInput(input);

  const { data, error } = await supabase
    .from('milestones')
    .insert({
      ...normalizedInput,
      user_id: user.id,
    })
    .select()
    .single();

  if (error) {
    throw error;
  }

  return data;
};

export const updateMilestone = async (
  milestoneId: string,
  input: UpdateMilestoneInput,
): Promise<Milestone> => {
  await getCurrentUser();
  const normalizedInput = normalizeUpdateMilestoneInput(input);

  const { data, error } = await supabase
    .from('milestones')
    .update(normalizedInput)
    .eq('id', milestoneId)
    .select()
    .single();

  if (error) {
    throw error;
  }

  return data;
};

export const toggleMilestoneComplete = async (
  milestoneId: string,
  isCompleted: boolean,
): Promise<Milestone> =>
  updateMilestone(milestoneId, { is_completed: isCompleted });

export const deleteMilestone = async (milestoneId: string): Promise<void> => {
  await getCurrentUser();

  const { error } = await supabase
    .from('milestones')
    .delete()
    .eq('id', milestoneId);

  if (error) {
    throw error;
  }
};
