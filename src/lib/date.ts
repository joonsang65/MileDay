import {
  addDays,
  endOfMonth,
  endOfWeek,
  format,
  startOfMonth,
  startOfWeek,
} from 'date-fns';

export interface CalendarDay {
  date: string;
  dayOfMonth: number;
  isCurrentMonth: boolean;
}

export const formatDateToYMD = (date: Date): string => format(date, 'yyyy-MM-dd');

export const getTodayDateString = (): string => formatDateToYMD(new Date());

export const isSameDateString = (a: string, b: string): boolean => a === b;

export const isYMDDateString = (value: string): boolean =>
  /^\d{4}-\d{2}-\d{2}$/.test(value);

export const normalizeDateString = (value: string): string => {
  const normalized = value.trim();

  if (!isYMDDateString(normalized)) {
    throw new Error('Date must be in YYYY-MM-DD format.');
  }

  return normalized;
};

export const getMonthCalendarDays = (
  year: number,
  month: number,
): CalendarDay[] => {
  const monthStart = startOfMonth(new Date(year, month, 1));
  const monthEnd = endOfMonth(monthStart);
  const calendarStart = startOfWeek(monthStart, { weekStartsOn: 1 });
  const calendarEnd = endOfWeek(monthEnd, { weekStartsOn: 1 });
  const days: CalendarDay[] = [];

  for (
    let cursor = calendarStart;
    cursor <= calendarEnd;
    cursor = addDays(cursor, 1)
  ) {
    days.push({
      date: formatDateToYMD(cursor),
      dayOfMonth: Number(format(cursor, 'd')),
      isCurrentMonth: cursor.getMonth() === month,
    });
  }

  return days;
};
