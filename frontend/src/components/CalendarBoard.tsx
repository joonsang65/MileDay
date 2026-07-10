import { format, isSameMonth } from "date-fns";

import type { CalendarDay, HolidayDisplay } from "@/api/types";
import type { CalendarMode } from "@/store/calendarStore";
import { getMonthGridDays, getWeekDays, getWeekdayLabels, parseDateKey, toDateKey } from "@/utils/date";

type CalendarBoardProps = {
  mode: CalendarMode;
  visibleDate: string;
  selectedDate: string;
  days: CalendarDay[];
  weekStartsOn: 0 | 1;
  holidayDisplay: HolidayDisplay;
  onSelectDate: (date: string) => void;
};

type GoalTaskGroup = {
  id: string;
  title: string;
  color: string;
  total: number;
  completed: number;
};

function getGoalTaskGroups(day?: CalendarDay): GoalTaskGroup[] {
  if (!day) {
    return [];
  }

  const groups = new Map<string, GoalTaskGroup>();
  for (const goal of day.goals) {
    groups.set(goal.id, {
      id: goal.id,
      title: goal.title,
      color: goal.color,
      total: 0,
      completed: 0,
    });
  }

  for (const milestone of day.milestones) {
    const group = groups.get(milestone.goal_id) ?? {
      id: milestone.goal_id,
      title: milestone.goal_title ?? "목표 없음",
      color: milestone.color,
      total: 0,
      completed: 0,
    };
    group.total += 1;
    if (milestone.is_completed) {
      group.completed += 1;
    }
    groups.set(milestone.goal_id, group);
  }

  return Array.from(groups.values());
}

export function CalendarBoard({
  mode,
  visibleDate,
  selectedDate,
  days,
  weekStartsOn,
  holidayDisplay,
  onSelectDate,
}: CalendarBoardProps) {
  const visible = parseDateKey(visibleDate);
  const dayMap = new Map(days.map((day) => [day.date, day]));
  const cells =
    mode === "month" ? getMonthGridDays(visible, weekStartsOn) : getWeekDays(parseDateKey(visibleDate));
  const weekdayLabels = getWeekdayLabels(weekStartsOn);

  return (
    <section className="calendar-surface" aria-label="캘린더">
      <div className="weekday-row">
        {weekdayLabels.map((label) => (
          <span key={label}>{label}</span>
        ))}
      </div>
      <div className={mode === "month" ? "calendar-grid month" : "calendar-grid week"}>
        {cells.map((cellDate) => {
          const dateKey = toDateKey(cellDate);
          const day = dayMap.get(dateKey);
          const isSelected = selectedDate === dateKey;
          const isMuted = mode === "month" && !isSameMonth(cellDate, visible);
          const isWeekend = cellDate.getDay() === 0 || cellDate.getDay() === 6;
          const shouldShowHoliday = holidayDisplay === "normal" && day?.is_holiday;
          const shouldMarkHoliday =
            shouldShowHoliday || (holidayDisplay === "weekend_like" && day?.is_holiday);
          const goalGroups = getGoalTaskGroups(day);
          const milestoneCount = day?.milestone_count ?? 0;
          const completedMilestoneCount = day?.completed_milestone_count ?? 0;

          return (
            <button
              type="button"
              key={dateKey}
              data-date={dateKey}
              className={[
                "day-cell",
                day?.is_today ? "today" : "",
                isSelected ? "selected" : "",
                isMuted ? "muted" : "",
                isWeekend || shouldMarkHoliday ? "holiday" : "",
              ]
                .filter(Boolean)
                .join(" ")}
              onClick={() => onSelectDate(dateKey)}
            >
              <span className="day-number">{format(cellDate, "d")}</span>
              <span className="day-metrics">
                {goalGroups.length ? <span className="metric goal">목표 {goalGroups.length}</span> : null}
                {milestoneCount ? (
                  <span className="metric milestone">
                    작업 {completedMilestoneCount}/{milestoneCount}
                  </span>
                ) : null}
              </span>
              {shouldShowHoliday ? (
                <span className="holiday-name">{day?.holiday_name}</span>
              ) : null}
              <span className="event-list" aria-hidden="true">
                {goalGroups.slice(0, 3).map((goal) => (
                  <span key={goal.id} className="event-text goal-event">
                    {goal.total > 0
                      ? `${goal.title} 작업 ${goal.completed}/${goal.total}`
                      : goal.title}
                  </span>
                ))}
              </span>
              <span className="dot-row" aria-hidden="true">
                {goalGroups.slice(0, 5).map((goal) => (
                  <span key={goal.id} className="dot goal-dot" style={{ background: goal.color }} />
                ))}
              </span>
            </button>
          );
        })}
      </div>
    </section>
  );
}
