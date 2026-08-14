import { app, BrowserWindow, ipcMain, safeStorage, screen } from "electron";
import { existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { getAutoLaunchState, setAutoLaunchState } from "./autoLaunch";
import { createMainWindowOptions } from "./windowOptions";

let mainWindow: BrowserWindow | null = null;

type LocalUiSettings = {
  baseFontSize: number;
  goalFontSize: number;
  resizeEnabled: boolean;
  windowBounds?: {
    x?: number;
    y?: number;
    width: number;
    height: number;
  };
};

type ResizeDirection = "n" | "e" | "s" | "w" | "ne" | "nw" | "se" | "sw";

type ResizeSession = {
  direction: ResizeDirection;
  startX: number;
  startY: number;
  bounds: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
};

const MIN_WINDOW_WIDTH = 560;
const MIN_WINDOW_HEIGHT = 440;

const DEFAULT_UI_SETTINGS: LocalUiSettings = {
  baseFontSize: 14,
  goalFontSize: 13,
  resizeEnabled: false,
};

let resizeSession: ResizeSession | null = null;

function getUiSettingsPath(): string {
  return join(app.getPath("userData"), "ui-settings.json");
}

function getAccessTokenPath(): string {
  return join(app.getPath("userData"), "access-token.bin");
}

function readUiSettings(): LocalUiSettings {
  const path = getUiSettingsPath();
  if (!existsSync(path)) {
    return DEFAULT_UI_SETTINGS;
  }

  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as Partial<LocalUiSettings>;
    return {
      baseFontSize: normalizeFontSize(parsed.baseFontSize, DEFAULT_UI_SETTINGS.baseFontSize),
      goalFontSize: normalizeFontSize(parsed.goalFontSize, DEFAULT_UI_SETTINGS.goalFontSize),
      resizeEnabled: Boolean(parsed.resizeEnabled),
      windowBounds: normalizeWindowBounds(parsed.windowBounds),
    };
  } catch {
    return DEFAULT_UI_SETTINGS;
  }
}

function writeUiSettings(settings: LocalUiSettings): LocalUiSettings {
  const normalized = {
    baseFontSize: normalizeFontSize(settings.baseFontSize, DEFAULT_UI_SETTINGS.baseFontSize),
    goalFontSize: normalizeFontSize(settings.goalFontSize, DEFAULT_UI_SETTINGS.goalFontSize),
    resizeEnabled: settings.resizeEnabled,
    windowBounds: normalizeWindowBounds(settings.windowBounds),
  };
  writeFileSync(getUiSettingsPath(), JSON.stringify(normalized, null, 2), "utf8");
  return normalized;
}

function updateUiSettings(patch: Partial<LocalUiSettings>): LocalUiSettings {
  return writeUiSettings({
    ...readUiSettings(),
    ...patch,
  });
}

function readStoredAccessToken(): string | null {
  const path = getAccessTokenPath();
  if (!existsSync(path) || !safeStorage.isEncryptionAvailable()) {
    return null;
  }

  try {
    return safeStorage.decryptString(readFileSync(path));
  } catch {
    return null;
  }
}

function writeStoredAccessToken(accessToken: string): boolean {
  if (!safeStorage.isEncryptionAvailable()) {
    return false;
  }

  writeFileSync(getAccessTokenPath(), safeStorage.encryptString(accessToken));
  return true;
}

function clearStoredAccessToken(): boolean {
  const path = getAccessTokenPath();
  if (!existsSync(path)) {
    return true;
  }

  try {
    unlinkSync(path);
    return true;
  } catch {
    return false;
  }
}

function normalizeFontSize(value: unknown, fallback: number): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return fallback;
  }
  return Math.min(32, Math.max(10, Math.round(parsed)));
}

function normalizeWindowBounds(value: unknown): LocalUiSettings["windowBounds"] {
  if (!value || typeof value !== "object") {
    return undefined;
  }
  const bounds = value as { x?: unknown; y?: unknown; width?: unknown; height?: unknown };
  const x = Number(bounds.x);
  const y = Number(bounds.y);
  const width = Number(bounds.width);
  const height = Number(bounds.height);
  if (!Number.isFinite(width) || !Number.isFinite(height)) {
    return undefined;
  }
  return {
    ...(Number.isFinite(x) ? { x: Math.round(x) } : {}),
    ...(Number.isFinite(y) ? { y: Math.round(y) } : {}),
    width: Math.max(MIN_WINDOW_WIDTH, Math.round(width)),
    height: Math.max(MIN_WINDOW_HEIGHT, Math.round(height)),
  };
}

function isResizeDirection(value: unknown): value is ResizeDirection {
  return value === "n" || value === "e" || value === "s" || value === "w" || value === "ne" || value === "nw" || value === "se" || value === "sw";
}

function clampWindowBounds(bounds: ResizeSession["bounds"]): ResizeSession["bounds"] {
  const workArea = screen.getDisplayMatching(bounds).workArea;
  const width = Math.min(Math.max(MIN_WINDOW_WIDTH, bounds.width), workArea.width);
  const height = Math.min(Math.max(MIN_WINDOW_HEIGHT, bounds.height), workArea.height);
  const maxX = workArea.x + workArea.width - width;
  const maxY = workArea.y + workArea.height - height;

  return {
    x: Math.min(Math.max(bounds.x, workArea.x), Math.max(workArea.x, maxX)),
    y: Math.min(Math.max(bounds.y, workArea.y), Math.max(workArea.y, maxY)),
    width,
    height,
  };
}

function applyResize(direction: ResizeDirection, startBounds: ResizeSession["bounds"], dx: number, dy: number) {
  const nextBounds = { ...startBounds };

  if (direction.includes("e")) {
    nextBounds.width = Math.max(MIN_WINDOW_WIDTH, startBounds.width + dx);
  }

  if (direction.includes("s")) {
    nextBounds.height = Math.max(MIN_WINDOW_HEIGHT, startBounds.height + dy);
  }

  if (direction.includes("w")) {
    const width = Math.max(MIN_WINDOW_WIDTH, startBounds.width - dx);
    nextBounds.x = startBounds.x + (startBounds.width - width);
    nextBounds.width = width;
  }

  if (direction.includes("n")) {
    const height = Math.max(MIN_WINDOW_HEIGHT, startBounds.height - dy);
    nextBounds.y = startBounds.y + (startBounds.height - height);
    nextBounds.height = height;
  }

  mainWindow?.setBounds(clampWindowBounds(nextBounds));
}

function saveCurrentWindowBounds(): void {
  if (!mainWindow) {
    return;
  }
  updateUiSettings({ windowBounds: mainWindow.getBounds() });
}

function createWindow(): void {
  const uiSettings = readUiSettings();
  mainWindow = new BrowserWindow(createMainWindowOptions(__dirname, uiSettings.windowBounds));
  mainWindow.setResizable(uiSettings.resizeEnabled);

  mainWindow.on("resize", () => {
    saveCurrentWindowBounds();
  });

  mainWindow.on("move", () => {
    saveCurrentWindowBounds();
  });

  mainWindow.on("ready-to-show", () => {
    // 다른 앱을 사용할 때 MileDay 위젯이 그 위를 덮지 않도록 비활성 상태로 표시한다.
    mainWindow?.setBounds(clampWindowBounds(mainWindow.getBounds()));
    mainWindow?.showInactive();
  });

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
  }
}

function registerAutoLaunchHandlers(): void {
  ipcMain.handle("auto-launch:get", () => getAutoLaunchState(app));
  ipcMain.handle("auto-launch:set", (_event, openAtLogin: boolean) =>
    setAutoLaunchState({
      app,
      openAtLogin,
      executablePath: process.execPath,
    }),
  );
}

function registerAuthTokenHandlers(): void {
  ipcMain.handle("auth-token:get", () => readStoredAccessToken());
  ipcMain.handle("auth-token:set", (_event, accessToken: string) => writeStoredAccessToken(accessToken));
  ipcMain.handle("auth-token:clear", () => clearStoredAccessToken());
  ipcMain.handle("auth-token:is-encryption-available", () => safeStorage.isEncryptionAvailable());
}

function registerUiSettingsHandlers(): void {
  ipcMain.handle("ui-settings:get", () => readUiSettings());
  ipcMain.handle("ui-settings:set-font-sizes", (_event, payload: { baseFontSize: number; goalFontSize: number }) =>
    updateUiSettings({
      baseFontSize: payload.baseFontSize,
      goalFontSize: payload.goalFontSize,
    }),
  );
  ipcMain.handle("ui-settings:set-resize-enabled", (_event, resizeEnabled: boolean) => {
    mainWindow?.setResizable(resizeEnabled);
    return updateUiSettings({ resizeEnabled });
  });

  ipcMain.handle("window-resize:start", (_event, payload: { direction: unknown; screenX: number; screenY: number }) => {
    if (!mainWindow || !isResizeDirection(payload.direction)) {
      resizeSession = null;
      return false;
    }

    mainWindow.setResizable(true);
    resizeSession = {
      direction: payload.direction,
      startX: payload.screenX,
      startY: payload.screenY,
      bounds: mainWindow.getBounds(),
    };
    return true;
  });

  ipcMain.handle("window-resize:update", (_event, payload: { screenX: number; screenY: number }) => {
    if (!resizeSession) {
      return false;
    }

    applyResize(
      resizeSession.direction,
      resizeSession.bounds,
      payload.screenX - resizeSession.startX,
      payload.screenY - resizeSession.startY,
    );
    return true;
  });

  ipcMain.handle("window-resize:end", () => {
    resizeSession = null;
    return true;
  });
}

app.whenReady().then(() => {
  app.setAppUserModelId("com.mileday.app");
  registerAutoLaunchHandlers();
  registerAuthTokenHandlers();
  registerUiSettingsHandlers();

  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});
