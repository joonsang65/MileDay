import { create } from "zustand";

import { toDateKey } from "@/utils/date";

export type CalendarMode = "month" | "week";

type CalendarState = {
  mode: CalendarMode;
  selectedDate: string;
  visibleDate: string;
  weekStartsOn: 0 | 1;
  setMode: (mode: CalendarMode) => void;
  setWeekStartsOn: (weekStartsOn: 0 | 1) => void;
  selectDate: (date: string) => void;
  setVisibleDate: (date: string) => void;
};

const today = toDateKey(new Date());

export const useCalendarStore = create<CalendarState>((set) => ({
  mode: "month",
  selectedDate: today,
  visibleDate: today,
  weekStartsOn: 1,
  setMode: (mode) => set({ mode }),
  setWeekStartsOn: (weekStartsOn) => set({ weekStartsOn }),
  selectDate: (date) => set({ selectedDate: date }),
  setVisibleDate: (date) => set({ visibleDate: date }),
}));
