import React from "react";

import { ScheduleSection, WeekScheduleSection } from "../components/ScheduleSection";
import { displayDate, weekDateKeys } from "../date";
import type { DayState } from "../date";
import { getDateWithCache, readCachedDate } from "../month-cache";
import type { CalendarDateData } from "../types";

export function Today({ day }: { day: DayState }) {
  const [today, setToday] = React.useState<CalendarDateData | null>(null);
  const [week, setWeek] = React.useState<CalendarDateData[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    const weekDates = weekDateKeys(day.today);
    // Show cached days immediately, then replace them with live data if available.
    const cached = weekDates.flatMap((date) => {
      const data = readCachedDate(date);
      return data ? [data] : [];
    });
    setToday(cached.find((data) => data.date === day.today) || null);
    setWeek(cached);
    void Promise.allSettled(weekDates.map((date) => getDateWithCache(date, true)))
      .then((results) => {
        if (!alive) return;
        const days = results.flatMap((result) => result.status === "fulfilled" ? [result.value] : []);
        setToday(days.find((data) => data.date === day.today) || null);
        setWeek(days);
        if (days.length !== 7) setError("일부 일정을 가져오지 못했습니다. 네트워크 상태를 확인해주세요.");
      })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [day]);

  return (
    <section className="screen">
      <header className="screen-header">
        <p className="eyebrow">Today</p>
        <h1>{displayDate(day.today)}</h1>
      </header>
      {loading ? <p className="status-text">불러오는 중입니다.</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      <ScheduleSection title="오늘 일정" data={today?.date === day.today ? today : null} />
      <WeekScheduleSection days={week.filter((data) => data.date > day.today)} />
    </section>
  );
}
