import { create } from 'zustand';
import { getTodayDateString } from '../lib/date';

interface AppState {
  selectedDate: string;
  setSelectedDate: (date: string) => void;
}

export const useAppStore = create<AppState>((set) => ({
  selectedDate: getTodayDateString(),
  setSelectedDate: (date) => set({ selectedDate: date }),
}));

