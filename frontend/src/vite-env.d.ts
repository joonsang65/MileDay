/// <reference types="vite/client" />

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
      get: () => Promise<{
        baseFontSize: number;
        goalFontSize: number;
        resizeEnabled: boolean;
      }>;
      setFontSizes: (payload: { baseFontSize: number; goalFontSize: number }) => Promise<{
        baseFontSize: number;
        goalFontSize: number;
        resizeEnabled: boolean;
      }>;
      setResizeEnabled: (resizeEnabled: boolean) => Promise<{
        baseFontSize: number;
        goalFontSize: number;
        resizeEnabled: boolean;
      }>;
    };
    windowResize?: {
      start: (payload: { direction: string; screenX: number; screenY: number }) => Promise<boolean>;
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
