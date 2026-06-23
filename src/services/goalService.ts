import { normalizeDateString } from '../lib/date';
import { supabase } from '../lib/supabase';
import type { CreateGoalInput, Goal, UpdateGoalInput } from '../types/goal';
import { getCurrentUser } from './authService';

const validateTitle = (title: string): string => {
  const normalized = title.trim();

  if (!normalized) {
    throw new Error('Goal title is required.');
  }

  return normalized;
};

const normalizeCreateGoalInput = (input: CreateGoalInput): CreateGoalInput => {
  const recurrenceType = input.is_recurring ? input.recurrence_type : 'none';

  if (input.is_recurring && recurrenceType === 'none') {
    throw new Error('Recurring goals must use weekly or monthly recurrence.');
  }

  return {
    title: validateTitle(input.title),
    deadline: normalizeDateString(input.deadline),
    is_recurring: input.is_recurring,
    recurrence_type: recurrenceType,
  };
};

const normalizeUpdateGoalInput = (input: UpdateGoalInput): UpdateGoalInput => {
  const output: UpdateGoalInput = {};

  if (input.title !== undefined) {
    output.title = validateTitle(input.title);
  }

  if (input.deadline !== undefined) {
    output.deadline = normalizeDateString(input.deadline);
  }

  if (input.is_recurring !== undefined) {
    output.is_recurring = input.is_recurring;
  }

  if (input.recurrence_type !== undefined) {
    output.recurrence_type = input.recurrence_type;
  }

  if (output.is_recurring === false) {
    output.recurrence_type = 'none';
  }

  if (
    output.is_recurring === undefined &&
    output.recurrence_type !== undefined
  ) {
    output.is_recurring = output.recurrence_type !== 'none';
  }

  if (output.is_recurring === true && output.recurrence_type === undefined) {
    throw new Error('Recurring goals must include weekly or monthly recurrence.');
  }

  if (output.is_recurring === true && output.recurrence_type === 'none') {
    throw new Error('Recurring goals must use weekly or monthly recurrence.');
  }

  return output;
};

export const getGoals = async (): Promise<Goal[]> => {
  await getCurrentUser();

  const { data, error } = await supabase
    .from('goals')
    .select('*')
    .order('deadline', { ascending: true })
    .order('created_at', { ascending: true });

  if (error) {
    throw error;
  }

  return data ?? [];
};

export const getGoalById = async (goalId: string): Promise<Goal> => {
  await getCurrentUser();

  const { data, error } = await supabase
    .from('goals')
    .select('*')
    .eq('id', goalId)
    .single();

  if (error) {
    throw error;
  }

  return data;
};

export const createGoal = async (input: CreateGoalInput): Promise<Goal> => {
  const user = await getCurrentUser();
  const normalizedInput = normalizeCreateGoalInput(input);

  const { data, error } = await supabase
    .from('goals')
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

export const updateGoal = async (
  goalId: string,
  input: UpdateGoalInput,
): Promise<Goal> => {
  await getCurrentUser();
  const normalizedInput = normalizeUpdateGoalInput(input);

  const { data, error } = await supabase
    .from('goals')
    .update(normalizedInput)
    .eq('id', goalId)
    .select()
    .single();

  if (error) {
    throw error;
  }

  return data;
};

export const deleteGoal = async (goalId: string): Promise<void> => {
  await getCurrentUser();

  const { error } = await supabase.from('goals').delete().eq('id', goalId);

  if (error) {
    throw error;
  }
};

export const getGoalsByDeadline = async (date: string): Promise<Goal[]> => {
  await getCurrentUser();
  const deadline = normalizeDateString(date);

  const { data, error } = await supabase
    .from('goals')
    .select('*')
    .eq('deadline', deadline)
    .order('created_at', { ascending: true });

  if (error) {
    throw error;
  }

  return data ?? [];
};
