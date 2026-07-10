import { describe, expect, it } from "vitest";

import {
  getMonthGridDays,
  getWeekDays,
  getWeekLabel,
  moveMonth,
  moveWeek,
  parseDateKey,
  toDateKey,
} from "./date";

describe("date utils", () => {
  it("월간 캘린더 격자를 월요일 시작 42칸으로 만든다", () => {
    const days = getMonthGridDays(parseDateKey("2026-07-10"), 1);

    expect(days).toHaveLength(42);
    expect(toDateKey(days[0])).toBe("2026-06-29");
    expect(toDateKey(days[41])).toBe("2026-08-09");
  });

  it("주간 캘린더 범위를 시작일부터 7일로 만든다", () => {
    const days = getWeekDays(parseDateKey("2026-07-08"));

    expect(days.map(toDateKey)).toEqual([
      "2026-07-08",
      "2026-07-09",
      "2026-07-10",
      "2026-07-11",
      "2026-07-12",
      "2026-07-13",
      "2026-07-14",
    ]);
    expect(getWeekLabel(parseDateKey("2026-07-08"))).toBe("07.08 - 07.14");
  });

  it("이전/다음 월과 주를 계산한다", () => {
    expect(toDateKey(moveMonth(parseDateKey("2026-07-10"), -1))).toBe("2026-06-10");
    expect(toDateKey(moveMonth(parseDateKey("2026-07-10"), 1))).toBe("2026-08-10");
    expect(toDateKey(moveWeek(parseDateKey("2026-07-10"), -1))).toBe("2026-07-03");
    expect(toDateKey(moveWeek(parseDateKey("2026-07-10"), 1))).toBe("2026-07-17");
  });
});
