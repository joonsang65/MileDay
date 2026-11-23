import { expect, it } from "vitest";

import fixture from "../../../tests/fixtures/calendar-month.json";
import type { CalendarMonthData } from "@/api/types";
import { toCalendarMonthView } from "./calendarUpdates";

it("applies goal defaults without changing the response's top-level milestone color", () => {
  const { id, title, deadline, color, created_at, updated_at } = fixture.data.goals[0];
  const goal = { id, title, deadline, color, created_at, updated_at };
  const month: CalendarMonthData = {
    ...fixture.data,
    goals: [goal],
    days: [{ ...fixture.data.days[0], goals: [goal] }],
    milestones: [{ ...fixture.data.milestones[0], color: null }],
  };

  const view = toCalendarMonthView(month);
  const completedShape = { ...goal, is_completed: false, is_recurring: false, recurrence_type: null };
  expect(view.goals).toEqual([completedShape]);
  expect(view.days[0].goals).toEqual([completedShape]);
  expect(view.milestones).toEqual(month.milestones);
  expect(month.goals).toEqual([goal]);
});
