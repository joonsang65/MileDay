import type { CalendarDay as CalendarDayValue } from '../../lib/date';

interface CalendarDayProps {
  day: CalendarDayValue;
  isToday: boolean;
  isSelected: boolean;
  hasDeadline: boolean;
  hasMilestone: boolean;
  hasIncompleteMilestone: boolean;
  onSelectDate: (date: string) => void;
}

export function CalendarDay({
  day,
  isToday,
  isSelected,
  hasDeadline,
  hasMilestone,
  hasIncompleteMilestone,
  onSelectDate,
}: CalendarDayProps) {
  const dayClasses = [
    'app-no-drag calendar-day-cell relative flex min-h-0 flex-col items-center justify-center rounded transition',
    day.isCurrentMonth ? 'text-zinc-100' : 'text-zinc-600',
    isSelected ? 'bg-sky-500 text-white' : 'hover:bg-zinc-800',
    isToday && !isSelected ? 'ring-1 ring-sky-400' : '',
  ]
    .filter(Boolean)
    .join(' ');

  return (
    <button
      className={dayClasses}
      type="button"
      onClick={() => onSelectDate(day.date)}
    >
      <span>{day.dayOfMonth}</span>
      <span className="absolute bottom-[3px] flex h-1.5 items-center gap-0.5">
        {hasDeadline ? (
          <span className="h-1.5 w-1.5 rounded-full border border-amber-300" />
        ) : null}
        {hasMilestone ? (
          <span
            className={[
              'h-1.5 w-1.5 rounded-full',
              hasIncompleteMilestone ? 'bg-rose-400' : 'bg-emerald-400',
            ].join(' ')}
          />
        ) : null}
      </span>
    </button>
  );
}
