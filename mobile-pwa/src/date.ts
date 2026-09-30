import { addDays, addMonths, eachDayOfInterval, endOfMonth, format, isSameMonth, parseISO, startOfMonth, startOfWeek, subMonths } from "date-fns";

export function todayKey() {
  return format(new Date(), "yyyy-MM-dd");
}

export function toDateKey(value: Date) {
  return format(value, "yyyy-MM-dd");
}

export function parseDateKey(value: string) {
  return parseISO(value);
}

export function monthLabel(value: Date) {
  return format(value, "yyyy.MM");
}

export function displayDate(value: string) {
  return format(parseDateKey(value), "M월 d일");
}

export function monthGrid(value: Date) {
  const start = startOfWeek(startOfMonth(value), { weekStartsOn: 0 });
  return eachDayOfInterval({ start, end: addDays(start, 41) });
}

export function moveMonth(value: Date, direction: -1 | 1) {
  return direction === 1 ? addMonths(value, 1) : subMonths(value, 1);
}

export function isInMonth(value: Date, month: Date) {
  return isSameMonth(value, month);
}

export function monthRange(value: Date) {
  return { start: startOfMonth(value), end: endOfMonth(value) };
}
