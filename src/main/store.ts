import { app, BrowserWindow } from 'electron';
import fs from 'node:fs';
import path from 'node:path';

export interface WidgetSettings {
  alwaysOnTop: boolean;
}

export interface WindowState {
  x?: number;
  y?: number;
  width: number;
  height: number;
}

export interface AppSettings {
  window: WindowState;
  widget: WidgetSettings;
}

const defaultSettings: AppSettings = {
  window: {
    width: 360,
    height: 560,
  },
  widget: {
    alwaysOnTop: false,
  },
};

const getSettingsPath = (): string =>
  path.join(app.getPath('userData'), 'widget-settings.json');

const ensureSettingsDirectory = (): void => {
  fs.mkdirSync(path.dirname(getSettingsPath()), { recursive: true });
};

export const loadSettings = (): AppSettings => {
  try {
    const settingsPath = getSettingsPath();

    if (!fs.existsSync(settingsPath)) {
      return defaultSettings;
    }

    const rawSettings = fs.readFileSync(settingsPath, 'utf-8');
    const parsedSettings = JSON.parse(rawSettings) as Partial<AppSettings>;

    return {
      window: {
        ...defaultSettings.window,
        ...parsedSettings.window,
      },
      widget: {
        ...defaultSettings.widget,
        ...parsedSettings.widget,
      },
    };
  } catch (error) {
    console.error('Failed to load widget settings.', error);
    return defaultSettings;
  }
};

export const getWindowBounds = (): WindowState => loadSettings().window;

export const getWidgetSettings = (): WidgetSettings => loadSettings().widget;

export const saveSettings = (settings: AppSettings): void => {
  try {
    ensureSettingsDirectory();
    fs.writeFileSync(getSettingsPath(), JSON.stringify(settings, null, 2));
  } catch (error) {
    console.error('Failed to save widget settings.', error);
  }
};

export const saveWindowState = (window: BrowserWindow): AppSettings => {
  const settings = loadSettings();
  const bounds = window.getBounds();
  const nextSettings: AppSettings = {
    ...settings,
    window: {
      x: bounds.x,
      y: bounds.y,
      width: bounds.width,
      height: bounds.height,
    },
  };

  saveSettings(nextSettings);
  return nextSettings;
};

export const updateWidgetSettings = (
  nextWidgetSettings: Partial<WidgetSettings>,
): AppSettings => {
  const settings = loadSettings();
  const nextSettings: AppSettings = {
    ...settings,
    widget: {
      ...settings.widget,
      ...nextWidgetSettings,
    },
  };

  saveSettings(nextSettings);
  return nextSettings;
};
