import { create } from "zustand";

export type OverlayMode = "none" | "quick-menu" | "manual-create" | "ai-create" | "settings" | "day-view" | "goal-list";

type UiState = {
  overlayMode: OverlayMode;
  openQuickMenu: () => void;
  openManualCreate: () => void;
  openAiCreate: () => void;
  openSettings: () => void;
  openDayView: () => void;
  openGoalList: () => void;
  closeOverlay: () => void;
};

export const useUiStore = create<UiState>((set) => ({
  overlayMode: "none",
  openQuickMenu: () =>
    set((state) => ({ overlayMode: state.overlayMode === "quick-menu" ? "none" : "quick-menu" })),
  openManualCreate: () => set({ overlayMode: "manual-create" }),
  openAiCreate: () => set({ overlayMode: "ai-create" }),
  openSettings: () => set({ overlayMode: "settings" }),
  openDayView: () => set({ overlayMode: "day-view" }),
  openGoalList: () => set({ overlayMode: "goal-list" }),
  closeOverlay: () => set({ overlayMode: "none" }),
}));
