import { create } from "zustand";

import { toDateKey } from "@/utils/date";

export type CalendarMode = "month" | "week";

type CalendarState = {
  mode: CalendarMode;
  selectedDate: string;
  visibleDate: string;
  setMode: (mode: CalendarMode) => void;
  selectDate: (date: string) => void;
  setVisibleDate: (date: string) => void;
};

const today = toDateKey(new Date());

export const useCalendarStore = create<CalendarState>((set) => ({
  mode: "month",
  selectedDate: today,
  visibleDate: today,
  setMode: (mode) => set({ mode }),
  selectDate: (date) => set({ selectedDate: date }),
  setVisibleDate: (date) => set({ visibleDate: date }),
}));
