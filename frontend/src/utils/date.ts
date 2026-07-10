import {
  addDays,
  addMonths,
  addWeeks,
  eachDayOfInterval,
  format,
  isSameDay,
  parseISO,
  startOfMonth,
  startOfWeek,
  subMonths,
  subWeeks,
} from "date-fns";

export const DATE_KEY_FORMAT = "yyyy-MM-dd";

export function toDateKey(value: Date): string {
  return format(value, DATE_KEY_FORMAT);
}

export function parseDateKey(value: string): Date {
  return parseISO(value);
}

export function getMonthLabel(value: Date): string {
  return format(value, "yyyy.MM");
}

export function getWeekLabel(startDate: Date): string {
  const endDate = addDays(startDate, 6);
  return `${format(startDate, "MM.dd")} - ${format(endDate, "MM.dd")}`;
}

export function getWeekdayLabels(weekStartsOn: 0 | 1): string[] {
  const labels = ["일", "월", "화", "수", "목", "금", "토"];
  return weekStartsOn === 0 ? labels : [...labels.slice(1), labels[0]];
}

export function getMonthGridDays(monthDate: Date, weekStartsOn: 0 | 1 = 1): Date[] {
  const monthStart = startOfMonth(monthDate);
  const gridStart = startOfWeek(monthStart, { weekStartsOn });
  return eachDayOfInterval({ start: gridStart, end: addDays(gridStart, 41) });
}

export function getWeekDays(startDate: Date): Date[] {
  return eachDayOfInterval({
    start: startDate,
    end: addDays(startDate, 6),
  });
}

export function moveMonth(value: Date, direction: -1 | 1): Date {
  return direction === 1 ? addMonths(value, 1) : subMonths(value, 1);
}

export function moveWeek(value: Date, direction: -1 | 1): Date {
  return direction === 1 ? addWeeks(value, 1) : subWeeks(value, 1);
}

export function getWeekStartDate(dateKey: string, weekStartsOn: 0 | 1): string {
  return toDateKey(startOfWeek(parseDateKey(dateKey), { weekStartsOn }));
}

export function isToday(value: Date, today = new Date()): boolean {
  return isSameDay(value, today);
}
