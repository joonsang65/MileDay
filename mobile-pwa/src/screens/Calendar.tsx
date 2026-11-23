import React from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";

import { ScheduleSection } from "../components/ScheduleSection";
import { displayDate, isInMonth, monthGrid, monthLabel, moveMonth, parseDateKey, rollCalendarDay, toDateKey } from "../date";
import type { DayState } from "../date";
import { getMonthWithCache, readCachedMonth } from "../month-cache";
import type { CalendarMonthData } from "../types";

export function Calendar({ day }: { day: DayState }) {
  const [calendar, setCalendar] = React.useState(() => ({ visibleMonth: parseDateKey(day.today), selectedDate: day.today }));
  const { visibleMonth, selectedDate } = calendar;
  const previousToday = React.useRef(day.today);
  const [month, setMonth] = React.useState<CalendarMonthData | null>(null);
  const selected = month?.days.find((day) => day.date === selectedDate) || null;

  React.useEffect(() => {
    const previous = previousToday.current;
    previousToday.current = day.today;
    setCalendar((current) => rollCalendarDay(current, previous, day.today));
  }, [day.today]);

  React.useEffect(() => {
    let alive = true;
    const year = visibleMonth.getFullYear();
    const monthNumber = visibleMonth.getMonth() + 1;
    const cached = readCachedMonth(year, monthNumber);
    if (cached) {
      setMonth(cached);
    } else {
      setMonth(null);
    }
    getMonthWithCache(year, monthNumber).then((data) => { if (alive) setMonth(data); }).catch(() => undefined);
    return () => { alive = false; };
  }, [visibleMonth, day]);

  return (
    <section className="screen">
      <header className="calendar-top">
        <button className="icon-button" onClick={() => setCalendar((current) => ({ ...current, visibleMonth: moveMonth(current.visibleMonth, -1) }))} aria-label="이전 달">
          <ChevronLeft />
        </button>
        <h1>{monthLabel(visibleMonth)}</h1>
        <button className="icon-button" onClick={() => setCalendar((current) => ({ ...current, visibleMonth: moveMonth(current.visibleMonth, 1) }))} aria-label="다음 달">
          <ChevronRight />
        </button>
      </header>
      <div className="weekday-grid">
        {["일", "월", "화", "수", "목", "금", "토"].map((day) => <span key={day}>{day}</span>)}
      </div>
      <div className="month-grid">
        {monthGrid(visibleMonth).map((date) => {
          const key = toDateKey(date);
          const data = month?.days.find((item) => item.date === key);
          return (
            <button
              key={key}
              className={[
                "date-cell",
                key === day.today ? "today" : "",
                key === selectedDate ? "selected" : "",
                !isInMonth(date, visibleMonth) ? "muted" : "",
                data && data.goal_count + data.milestone_count > 0 ? "has-events" : "",
              ].filter(Boolean).join(" ")}
              aria-current={key === day.today ? "date" : undefined}
              aria-pressed={key === selectedDate}
              onClick={() => setCalendar((current) => ({ ...current, selectedDate: key }))}
            >
              <span>{date.getDate()}</span>
              <i />
            </button>
          );
        })}
      </div>
      <ScheduleSection title={displayDate(selectedDate)} data={selected} />
    </section>
  );
}
