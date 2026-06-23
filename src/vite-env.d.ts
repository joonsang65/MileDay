/// <reference types="vite/client" />

interface MileDayWidgetSettings {
  window: {
    x?: number;
    y?: number;
    width: number;
    height: number;
  };
  widget: {
    alwaysOnTop: boolean;
  };
}

interface Window {
  mileDayWidget?: {
    getSettings: () => Promise<MileDayWidgetSettings>;
    getWidgetSettings: () => Promise<MileDayWidgetSettings['widget']>;
    updateWidgetSettings: (
      settings: Partial<MileDayWidgetSettings['widget']>,
    ) => Promise<MileDayWidgetSettings>;
    setAlwaysOnTop: (alwaysOnTop: boolean) => Promise<MileDayWidgetSettings>;
    getWindowBounds: () => Promise<MileDayWidgetSettings['window']>;
    resizeWindow: (
      width: number,
      height: number,
    ) => Promise<MileDayWidgetSettings>;
    show: () => Promise<void>;
    hide: () => Promise<void>;
  };
}
