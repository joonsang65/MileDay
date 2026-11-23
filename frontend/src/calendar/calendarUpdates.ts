import type { CalendarDateData, CalendarDay, CalendarMonthData, CalendarWeekData, Goal, Milestone } from "@/api/types";

type CalendarMilestone = Omit<Milestone, "color"> & Pick<CalendarMonthData["milestones"][number], "color">;

type CalendarMonthView = Omit<CalendarMonthData, "goals" | "days" | "milestones"> & {
  goals: Goal[];
  days: CalendarDay[];
  milestones: CalendarMilestone[];
};

type CalendarWeekView = Omit<CalendarWeekData, "milestones"> & { milestones: CalendarMilestone[] };

export type CalendarData = CalendarMonthView | CalendarWeekView;

export function toCalendarMonthView(month: CalendarMonthData): CalendarMonthView {
  function withGoalDefaults(goal: CalendarMonthData["goals"][number]): Goal {
    return {
      ...goal,
      is_completed: goal.is_completed ?? false,
      is_recurring: goal.is_recurring ?? false,
      recurrence_type: goal.recurrence_type ?? null,
    };
  }

  return {
    ...month,
    goals: month.goals.map(withGoalDefaults),
    days: month.days.map((day) => ({ ...day, goals: day.goals.map(withGoalDefaults) })),
  };
}

export function countCompletedMilestones(milestones: { is_completed: boolean }[]) {
  return milestones.filter((milestone) => milestone.is_completed).length;
}

function upsertMilestoneList<T extends { id: string }>(milestones: T[], milestone: T): T[] {
  return milestones.some((item) => item.id === milestone.id)
    ? milestones.map((item) => item.id === milestone.id ? milestone : item)
    : [...milestones, milestone];
}

export function upsertGoalInCalendar(calendar: CalendarData, goal: Goal): CalendarData {
  return {
    ...calendar,
    goals: [...calendar.goals.filter((item) => item.id !== goal.id), goal],
    milestones: calendar.milestones.map((m) =>
      m.goal_id === goal.id ? { ...m, goal_title: goal.title } : m,
    ),
    days: calendar.days.map((day) => {
      const goals = day.goals.filter((item) => item.id !== goal.id);
      if (day.date === goal.deadline) {
        goals.push(goal);
      }
      const milestones = day.milestones.map((m) =>
        m.goal_id === goal.id ? { ...m, goal_title: goal.title } : m,
      );
      return {
        ...day,
        goals,
        milestones,
        goal_count: goals.length,
      };
    }),
  };
}

export function upsertGoalInDateDetail(detail: CalendarDateData, goal: Goal): CalendarDateData {
  const goals = detail.goals.filter((item) => item.id !== goal.id);
  if (detail.date === goal.deadline) {
    goals.push(goal);
  }
  const milestones = detail.milestones.map((m) =>
    m.goal_id === goal.id ? { ...m, goal_title: goal.title } : m,
  );
  return {
    ...detail,
    goals,
    milestones,
    goal_count: goals.length,
  };
}

export function upsertMilestoneInCalendar(calendar: CalendarData, milestone: Milestone): CalendarData {
  const existing = calendar.milestones.find((item) => item.id === milestone.id);
  const milestoneToUpsert = existing && milestone.goal_title == null
    ? { ...milestone, goal_title: existing.goal_title }
    : milestone;

  return {
    ...calendar,
    milestones: upsertMilestoneList(calendar.milestones, milestoneToUpsert),
    days: calendar.days.map((day) => {
      const milestones = day.date === milestoneToUpsert.scheduled_date
        ? upsertMilestoneList(day.milestones, milestoneToUpsert)
        : day.milestones.filter((item) => item.id !== milestoneToUpsert.id);
      return {
        ...day,
        milestones,
        milestone_count: milestones.length,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

export function upsertMilestoneInDateDetail(detail: CalendarDateData, milestone: Milestone): CalendarDateData {
  const existing = detail.milestones.find((item) => item.id === milestone.id);
  const milestoneToUpsert = existing && milestone.goal_title == null
    ? { ...milestone, goal_title: existing.goal_title }
    : milestone;

  const milestones = detail.date === milestoneToUpsert.scheduled_date
    ? upsertMilestoneList(detail.milestones, milestoneToUpsert)
    : detail.milestones.filter((item) => item.id !== milestoneToUpsert.id);
  return {
    ...detail,
    milestones,
    milestone_count: milestones.length,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}

export function removeGoalFromCalendar(calendar: CalendarData, goalId: string): CalendarData {
  return {
    ...calendar,
    goals: calendar.goals.filter((goal) => goal.id !== goalId),
    milestones: calendar.milestones.filter((milestone) => milestone.goal_id !== goalId),
    days: calendar.days.map((day) => {
      const goals = day.goals.filter((goal) => goal.id !== goalId);
      const milestones = day.milestones.filter((milestone) => milestone.goal_id !== goalId);
      return {
        ...day,
        goals,
        milestones,
        goal_count: goals.length,
        milestone_count: milestones.length,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

export function removeGoalFromDateDetail(detail: CalendarDateData, goalId: string): CalendarDateData {
  const goals = detail.goals.filter((goal) => goal.id !== goalId);
  const milestones = detail.milestones.filter((milestone) => milestone.goal_id !== goalId);
  return {
    ...detail,
    goals,
    milestones,
    goal_count: goals.length,
    milestone_count: milestones.length,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}

export function removeMilestoneFromCalendar(calendar: CalendarData, milestoneId: string): CalendarData {
  return {
    ...calendar,
    milestones: calendar.milestones.filter((milestone) => milestone.id !== milestoneId),
    days: calendar.days.map((day) => {
      const milestones = day.milestones.filter((milestone) => milestone.id !== milestoneId);
      return {
        ...day,
        milestones,
        milestone_count: milestones.length,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

export function removeMilestoneFromDateDetail(detail: CalendarDateData, milestoneId: string): CalendarDateData {
  const milestones = detail.milestones.filter((milestone) => milestone.id !== milestoneId);
  return {
    ...detail,
    milestones,
    milestone_count: milestones.length,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}

export function updateGoalCompletionInCalendar(calendar: CalendarData, goalId: string, isCompleted: boolean): CalendarData {
  const updateGoal = (goal: Goal): Goal => (
    goal.id === goalId ? { ...goal, is_completed: isCompleted } : goal
  );
  return {
    ...calendar,
    goals: calendar.goals.map(updateGoal),
    days: calendar.days.map((day) => ({
      ...day,
      goals: day.goals.map(updateGoal),
    })),
  };
}

export function updateGoalCompletionInDateDetail(detail: CalendarDateData, goalId: string, isCompleted: boolean): CalendarDateData {
  return {
    ...detail,
    goals: detail.goals.map((goal) => (
      goal.id === goalId ? { ...goal, is_completed: isCompleted } : goal
    )),
  };
}

export function updateGoalMilestonesCompletionInCalendar(calendar: CalendarData, goalId: string, isCompleted: boolean): CalendarData {
  const updateMilestone = <T extends { goal_id: string; is_completed: boolean }>(milestone: T): T => (
    milestone.goal_id === goalId ? { ...milestone, is_completed: isCompleted } : milestone
  );
  return {
    ...calendar,
    milestones: calendar.milestones.map(updateMilestone),
    days: calendar.days.map((day) => {
      const milestones = day.milestones.map(updateMilestone);
      return {
        ...day,
        milestones,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

export function updateGoalMilestonesCompletionInDateDetail(detail: CalendarDateData, goalId: string, isCompleted: boolean): CalendarDateData {
  const milestones = detail.milestones.map((milestone) => (
    milestone.goal_id === goalId ? { ...milestone, is_completed: isCompleted } : milestone
  ));
  return {
    ...detail,
    milestones,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}
