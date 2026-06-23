import { format } from 'date-fns';
import { CalendarHeader } from './CalendarHeader';
import { CalendarDay } from './CalendarDay';
import { getMonthCalendarDays, getTodayDateString } from '../../lib/date';
import type { Goal } from '../../types/goal';
import type { Milestone } from '../../types/milestone';

interface CalendarProps {
  currentMonth: Date;
  selectedDate: string;
  goals: Goal[];
  milestones: Milestone[];
  onPreviousMonth: () => void;
  onNextMonth: () => void;
  onSelectDate: (date: string) => void;
}

const weekDays = ['M', 'T', 'W', 'T', 'F', 'S', 'S'];

export function Calendar({
  currentMonth,
  selectedDate,
  goals,
  milestones,
  onPreviousMonth,
  onNextMonth,
  onSelectDate,
}: CalendarProps) {
  const today = getTodayDateString();
  const days = getMonthCalendarDays(
    currentMonth.getFullYear(),
    currentMonth.getMonth(),
  );
  const deadlineDates = new Set(goals.map((goal) => goal.deadline));
  const milestoneDates = new Set(
    milestones.map((milestone) => milestone.scheduled_date),
  );
  const incompleteMilestoneDates = new Set(
    milestones
      .filter((milestone) => !milestone.is_completed)
      .map((milestone) => milestone.scheduled_date),
  );

  return (
    <section className="min-h-0 shrink-0 space-y-1 overflow-hidden">
      <CalendarHeader
        label={format(currentMonth, 'MMMM yyyy')}
        onPreviousMonth={onPreviousMonth}
        onNextMonth={onNextMonth}
      />
      <div className="calendar-grid grid px-1 text-center text-[10px] font-medium text-zinc-500">
        {weekDays.map((day, index) => (
          <div key={`${day}-${index}`}>{day}</div>
        ))}
      </div>
      <div className="calendar-grid grid">
        {days.map((day) => (
          <CalendarDay
            key={day.date}
            day={day}
            isToday={day.date === today}
            isSelected={day.date === selectedDate}
            hasDeadline={deadlineDates.has(day.date)}
            hasMilestone={milestoneDates.has(day.date)}
            hasIncompleteMilestone={incompleteMilestoneDates.has(day.date)}
            onSelectDate={onSelectDate}
          />
        ))}
      </div>
      <div className="calendar-legend flex items-center gap-3 px-1 text-[10px] text-zinc-500">
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full border border-amber-300" />
          Deadline
        </span>
        <span className="inline-flex items-center gap-1">
          <span className="h-1.5 w-1.5 rounded-full bg-rose-400" />
          Milestone
        </span>
      </div>
    </section>
  );
}
