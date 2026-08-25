/// <reference types="vite/client" />

import type { LocalUiFontSizePayload, LocalUiSettings } from "@/types/localUiSettings";
import type { ResizeDirection } from "@/types/windowResize";

declare global {
  interface Window {
    mileday?: {
      platform: string;
      autoLaunch?: {
        get: () => Promise<{ openAtLogin: boolean }>;
        set: (openAtLogin: boolean) => Promise<{ openAtLogin: boolean }>;
      };
      authToken?: {
        get: () => Promise<string | null>;
        set: (accessToken: string) => Promise<boolean>;
        clear: () => Promise<boolean>;
        isEncryptionAvailable: () => Promise<boolean>;
      };
      uiSettings?: {
        get: () => Promise<LocalUiSettings>;
        setFontSizes: (payload: LocalUiFontSizePayload) => Promise<LocalUiSettings>;
        setResizeEnabled: (resizeEnabled: boolean) => Promise<LocalUiSettings>;
        setOpacity: (opacity: number) => Promise<LocalUiSettings>;
      };
      windowResize?: {
        start: (payload: { direction: ResizeDirection; screenX: number; screenY: number }) => Promise<boolean>;
        update: (payload: { screenX: number; screenY: number }) => Promise<boolean>;
        end: () => Promise<boolean>;
      };
      windowMove?: {
        start: (payload: { screenX: number; screenY: number }) => Promise<boolean>;
        update: (payload: { screenX: number; screenY: number }) => Promise<boolean>;
        end: () => Promise<boolean>;
      };
      windowFocus?: {
        setKeyboardFocusRequired: (required: boolean) => Promise<boolean>;
      };
    };
  }
}

export {};
