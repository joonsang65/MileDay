import { format, isSameMonth } from "date-fns";

import type { CalendarDay, HolidayDisplay, Language } from "@/api/types";
import type { CalendarMode } from "@/store/calendarStore";
import { getMonthGridDays, getWeekDays, getWeekdayLabels, parseDateKey, toDateKey } from "@/utils/date";

type CalendarBoardProps = {
  mode: CalendarMode;
  visibleDate: string;
  selectedDate: string;
  days: CalendarDay[];
  weekStartsOn: 0 | 1;
  holidayDisplay: HolidayDisplay;
  language?: Language;
  onSelectDate: (date: string) => void;
};

type GoalTaskGroup = {
  id: string;
  title: string;
  color: string;
  total: number;
  completed: number;
};

function getGoalTaskGroups(day: CalendarDay | undefined, noGoalLabel: string): GoalTaskGroup[] {
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
      title: milestone.goal_title ?? noGoalLabel,
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

const holidayNamesEn: Record<string, string> = {
  "1월1일": "New Year's Day",
  "신정": "New Year's Day",
  "설날": "Lunar New Year",
  "설날연휴": "Lunar New Year Holiday",
  "삼일절": "Independence Movement Day",
  "3·1절": "Independence Movement Day",
  "어린이날": "Children's Day",
  "제헌절": "Constitution Day",
  "노동절": "Labor Day",
  "근로자의날": "Labor Day",
  "근로자의 날": "Labor Day",
  "부처님오신날": "Buddha's Birthday",
  "석가탄신일": "Buddha's Birthday",
  "현충일": "Memorial Day",
  "광복절": "Liberation Day",
  "추석": "Chuseok",
  "추석연휴": "Chuseok Holiday",
  "개천절": "National Foundation Day",
  "한글날": "Hangeul Day",
  "크리스마스": "Christmas",
  "기독탄신일": "Christmas",
  "대체공휴일": "Substitute Holiday",
  "공휴일": "Holiday",
};

function getHolidayName(name: string | null | undefined, language: Language) {
  if (!name || language !== "en") {
    return name;
  }
  const substituteMatch = name.match(/^대체공휴일\((.+)\)$/);
  if (substituteMatch) {
    const originalName = holidayNamesEn[substituteMatch[1]] ?? substituteMatch[1];
    return `Substitute Holiday (${originalName})`;
  }
  return holidayNamesEn[name] ?? name;
}

export function CalendarBoard({
  mode,
  visibleDate,
  selectedDate,
  days,
  weekStartsOn,
  holidayDisplay,
  language = "ko",
  onSelectDate,
}: CalendarBoardProps) {
  const visible = parseDateKey(visibleDate);
  const dayMap = new Map(days.map((day) => [day.date, day]));
  const cells =
    mode === "month" ? getMonthGridDays(visible, weekStartsOn) : getWeekDays(parseDateKey(visibleDate));
  const weekdayLabels = getWeekdayLabels(weekStartsOn, language);

  return (
    <section className="calendar-surface" aria-label={language === "en" ? "Calendar" : "캘린더"}>
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
          const goalGroups = getGoalTaskGroups(day, language === "en" ? "No goal" : "목표 없음");

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
              {shouldShowHoliday ? (
                <span className="holiday-name">{getHolidayName(day?.holiday_name, language)}</span>
              ) : null}
              <span className="event-list" aria-hidden="true">
                {goalGroups.slice(0, 3).map((goal) => (
                  <span key={goal.id} className="event-text goal-event">
                    {goal.total > 0
                      ? `${goal.title} ${goal.completed}/${goal.total}`
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
