/// <reference types="vite/client" />

interface Window {
  mileday?: {
    platform: string;
    autoLaunch?: {
      get: () => Promise<{ openAtLogin: boolean }>;
      set: (openAtLogin: boolean) => Promise<{ openAtLogin: boolean }>;
    };
  };
}
