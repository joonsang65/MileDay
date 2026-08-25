import { create } from "zustand";

export type OverlayMode = "none" | "manual-create" | "ai-create" | "settings" | "day-view" | "goal-list";

type UiState = {
  overlayMode: OverlayMode;
  openManualCreate: () => void;
  openAiCreate: () => void;
  openSettings: () => void;
  openDayView: () => void;
  openGoalList: () => void;
  closeOverlay: () => void;
};

export const useUiStore = create<UiState>((set) => ({
  overlayMode: "none",
  openManualCreate: () => set({ overlayMode: "manual-create" }),
  openAiCreate: () => set({ overlayMode: "ai-create" }),
  openSettings: () => set({ overlayMode: "settings" }),
  openDayView: () => set({ overlayMode: "day-view" }),
  openGoalList: () => set({ overlayMode: "goal-list" }),
  closeOverlay: () => set({ overlayMode: "none" }),
}));
