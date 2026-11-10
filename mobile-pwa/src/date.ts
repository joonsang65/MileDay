import { addDays, addMonths, eachDayOfInterval, endOfMonth, format, isSameMonth, parseISO, startOfMonth, startOfWeek, subMonths } from "date-fns";

export function todayKey() {
  // Date-only API keys, calendar arithmetic, and rollover all use device-local time.
  return toDateKey(new Date());
}

export function weekDateKeys(day: string) {
  return Array.from({ length: 7 }, (_, index) => toDateKey(addDays(parseDateKey(day), index)));
}

export type DayState = { today: string; revision: number };

export function watchDay(onChange: (day: DayState) => void) {
  let today = todayKey();
  let revision = 0;
  let timer: number;
  function check(force = false) {
    const next = todayKey();
    if (force || next !== today) {
      today = next;
      onChange({ today, revision: ++revision });
    }
    window.clearTimeout(timer);
    const now = new Date();
    const midnight = new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1);
    // Recheck clock/timezone changes even when the app stays open all day.
    timer = window.setTimeout(() => check(), Math.min(60_000, Math.max(1, midnight.getTime() - now.getTime())));
  }
  const resume = () => check(true);
  const visible = () => {
    if (document.visibilityState === "visible") resume();
  };
  window.addEventListener("focus", resume);
  window.addEventListener("online", resume);
  document.addEventListener("visibilitychange", visible);
  check(true);
  return () => {
    window.clearTimeout(timer);
    window.removeEventListener("focus", resume);
    window.removeEventListener("online", resume);
    document.removeEventListener("visibilitychange", visible);
  };
}

export function rollCalendarDay(
  state: { selectedDate: string; visibleMonth: Date }, previous: string, next: string,
) {
  if (state.selectedDate !== previous) return state;
  return {
    selectedDate: next,
    visibleMonth: isSameMonth(state.visibleMonth, parseDateKey(previous)) ? parseDateKey(next) : state.visibleMonth,
  };
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
