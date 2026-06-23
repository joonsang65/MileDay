import { BrowserWindow, app, ipcMain, screen } from 'electron';
import path from 'node:path';
import { isQuitting } from './lifecycle';
import {
  loadSettings,
  getWindowBounds,
  getWidgetSettings,
  saveWindowState,
  updateWidgetSettings,
} from './store';
import type { AppSettings, WidgetSettings } from './store';

let mainWindow: BrowserWindow | null = null;

const getPreloadPath = (): string =>
  path.join(__dirname, '../preload/index.js');

const getRendererPath = (): string =>
  path.join(__dirname, '../../dist/index.html');

const minWindowWidth = 320;
const minWindowHeight = 420;

const getValidatedWindowBounds = (bounds: AppSettings['window']) => {
  const width = Math.max(minWindowWidth, bounds.width);
  const height = Math.max(minWindowHeight, bounds.height);
  const display = screen.getDisplayMatching({
    x: bounds.x ?? 0,
    y: bounds.y ?? 0,
    width,
    height,
  });
  const workArea = display.workArea;
  const x = Math.min(
    Math.max(bounds.x ?? workArea.x, workArea.x),
    workArea.x + workArea.width - width,
  );
  const y = Math.min(
    Math.max(bounds.y ?? workArea.y, workArea.y),
    workArea.y + workArea.height - height,
  );

  return {
    x,
    y,
    width,
    height,
  };
};

export const getMainWindow = (): BrowserWindow | null => mainWindow;

export const createMainWindow = (): BrowserWindow => {
  const settings = loadSettings();
  const bounds = getValidatedWindowBounds(settings.window);

  mainWindow = new BrowserWindow({
    x: bounds.x,
    y: bounds.y,
    width: bounds.width,
    height: bounds.height,
    minWidth: minWindowWidth,
    minHeight: minWindowHeight,
    frame: false,
    transparent: false,
    resizable: true,
    show: false,
    title: 'MileDay',
    alwaysOnTop: settings.widget.alwaysOnTop,
    webPreferences: {
      preload: getPreloadPath(),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  const persistWindowState = () => {
    if (mainWindow && !mainWindow.isDestroyed()) {
      saveWindowState(mainWindow);
    }
  };

  mainWindow.on('ready-to-show', () => {
    mainWindow?.show();
  });

  mainWindow.on('move', persistWindowState);
  mainWindow.on('resize', persistWindowState);
  mainWindow.on('moved', persistWindowState);
  mainWindow.on('resized', persistWindowState);

  mainWindow.on('close', (event) => {
    if (!isQuitting()) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  const devServerUrl = process.env.VITE_DEV_SERVER_URL;

  if (devServerUrl) {
    void mainWindow.loadURL(devServerUrl);
  } else {
    void mainWindow.loadFile(getRendererPath());
  }

  return mainWindow;
};

export const showMainWindow = (): void => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createMainWindow();
    return;
  }

  mainWindow.show();
};

export const hideMainWindow = (): void => {
  mainWindow?.hide();
};

export const setMainWindowAlwaysOnTop = (alwaysOnTop: boolean): AppSettings => {
  const nextSettings = updateWidgetSettings({ alwaysOnTop });
  mainWindow?.setAlwaysOnTop(alwaysOnTop);
  return nextSettings;
};

export const resizeMainWindow = (width: number, height: number): AppSettings => {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return loadSettings();
  }

  const bounds = mainWindow.getBounds();
  const nextWidth = Math.max(minWindowWidth, Math.round(width));
  const nextHeight = Math.max(minWindowHeight, Math.round(height));

  mainWindow.setBounds({
    ...bounds,
    width: nextWidth,
    height: nextHeight,
  });

  return saveWindowState(mainWindow);
};

export const updateMainWindowWidgetSettings = (
  settings: Partial<WidgetSettings>,
): AppSettings => {
  const nextSettings = updateWidgetSettings(settings);
  mainWindow?.setAlwaysOnTop(nextSettings.widget.alwaysOnTop);
  return nextSettings;
};

export const registerWindowIpc = (): void => {
  ipcMain.handle('widget:get-settings', () => loadSettings());
  ipcMain.handle('widget:get-widget-settings', () => getWidgetSettings());
  ipcMain.handle('widget:update-widget-settings', (_, settings: Partial<WidgetSettings>) =>
    updateMainWindowWidgetSettings(settings),
  );
  ipcMain.handle('widget:set-always-on-top', (_, alwaysOnTop: boolean) =>
    setMainWindowAlwaysOnTop(alwaysOnTop),
  );
  ipcMain.handle('widget:get-window-bounds', () => getWindowBounds());
  ipcMain.handle(
    'widget:resize-window',
    (_, width: number, height: number) => resizeMainWindow(width, height),
  );
  ipcMain.handle('widget:show', () => showMainWindow());
  ipcMain.handle('widget:hide', () => hideMainWindow());
};
