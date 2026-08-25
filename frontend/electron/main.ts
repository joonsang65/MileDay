import { app, BrowserWindow, ipcMain, Menu, safeStorage, screen, Tray } from "electron";
import { existsSync, readFileSync, unlinkSync, writeFileSync } from "node:fs";
import { join } from "node:path";

import { getAutoLaunchState, setAutoLaunchState } from "./autoLaunch";
import { createMainWindowOptions, getMaxWindowBounds, WINDOW_SIZE_LIMITS } from "./windowOptions";
import { DEFAULT_LOCAL_UI_SETTINGS, type LocalUiFontSizePayload, type LocalUiSettings } from "../src/types/localUiSettings";
import { isResizeDirection, type ResizeDirection } from "../src/types/windowResize";

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let isQuitting = false;
let isApplyingWindowBounds = false;

type StoredLocalUiSettings = LocalUiSettings & {
  windowBounds?: {
    x?: number;
    y?: number;
    width: number;
    height: number;
  };
};

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

type MoveSession = {
  startX: number;
  startY: number;
  bounds: ResizeSession["bounds"];
};

let resizeSession: ResizeSession | null = null;
let moveSession: MoveSession | null = null;

function getTrayIconPath(): string {
  if (app.isPackaged) {
    return join(process.resourcesPath, "icons", "mileday_icon.ico");
  }

  return join(__dirname, "../../build/mileday_icon.ico");
}

function getUiSettingsPath(): string {
  return join(app.getPath("userData"), "ui-settings.json");
}

function getAccessTokenPath(): string {
  return join(app.getPath("userData"), "access-token.bin");
}

function readUiSettings(): StoredLocalUiSettings {
  const path = getUiSettingsPath();
  if (!existsSync(path)) {
    return DEFAULT_LOCAL_UI_SETTINGS;
  }

  try {
    const parsed = JSON.parse(readFileSync(path, "utf8")) as Partial<StoredLocalUiSettings>;
    return {
      baseFontSize: normalizeFontSize(parsed.baseFontSize, DEFAULT_LOCAL_UI_SETTINGS.baseFontSize),
      goalFontSize: normalizeFontSize(parsed.goalFontSize, DEFAULT_LOCAL_UI_SETTINGS.goalFontSize),
      resizeEnabled: Boolean(parsed.resizeEnabled),
      theme: DEFAULT_LOCAL_UI_SETTINGS.theme,
      fontFamily: DEFAULT_LOCAL_UI_SETTINGS.fontFamily,
      opacity: normalizeOpacity(parsed.opacity),
      windowBounds: normalizeWindowBounds(parsed.windowBounds),
    };
  } catch {
    return DEFAULT_LOCAL_UI_SETTINGS;
  }
}

function writeUiSettings(settings: StoredLocalUiSettings): StoredLocalUiSettings {
  const normalized = {
    baseFontSize: normalizeFontSize(settings.baseFontSize, DEFAULT_LOCAL_UI_SETTINGS.baseFontSize),
    goalFontSize: normalizeFontSize(settings.goalFontSize, DEFAULT_LOCAL_UI_SETTINGS.goalFontSize),
    resizeEnabled: settings.resizeEnabled,
    theme: DEFAULT_LOCAL_UI_SETTINGS.theme,
    fontFamily: DEFAULT_LOCAL_UI_SETTINGS.fontFamily,
    opacity: normalizeOpacity(settings.opacity),
    windowBounds: normalizeWindowBounds(settings.windowBounds),
  };
  writeFileSync(getUiSettingsPath(), JSON.stringify(normalized, null, 2), "utf8");
  return normalized;
}

function updateUiSettings(patch: Partial<StoredLocalUiSettings>): StoredLocalUiSettings {
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
  return Math.min(25, Math.max(1, Math.round(parsed)));
}

function normalizeOpacity(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_LOCAL_UI_SETTINGS.opacity;
  }
  return Math.min(1, Math.max(0.2, parsed));
}

function normalizeWindowBounds(value: unknown): StoredLocalUiSettings["windowBounds"] {
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
    width: Math.max(WINDOW_SIZE_LIMITS.minWidth, Math.round(width)),
    height: Math.max(WINDOW_SIZE_LIMITS.minHeight, Math.round(height)),
  };
}

function clampWindowBounds(
  bounds: ResizeSession["bounds"],
  displaySourceBounds: ResizeSession["bounds"] = bounds,
): ResizeSession["bounds"] {
  const workArea = screen.getDisplayMatching(displaySourceBounds).workArea;
  const maxBounds = getMaxWindowBounds(workArea);
  const width = Math.min(Math.max(WINDOW_SIZE_LIMITS.minWidth, bounds.width), maxBounds.width);
  const height = Math.min(Math.max(WINDOW_SIZE_LIMITS.minHeight, bounds.height), maxBounds.height);
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
    nextBounds.width = Math.max(WINDOW_SIZE_LIMITS.minWidth, startBounds.width + dx);
  }

  if (direction.includes("s")) {
    nextBounds.height = Math.max(WINDOW_SIZE_LIMITS.minHeight, startBounds.height + dy);
  }

  if (direction.includes("w")) {
    const width = Math.max(WINDOW_SIZE_LIMITS.minWidth, startBounds.width - dx);
    nextBounds.x = startBounds.x + (startBounds.width - width);
    nextBounds.width = width;
  }

  if (direction.includes("n")) {
    const height = Math.max(WINDOW_SIZE_LIMITS.minHeight, startBounds.height - dy);
    nextBounds.y = startBounds.y + (startBounds.height - height);
    nextBounds.height = height;
  }

  setClampedWindowBounds(nextBounds);
}

function saveCurrentWindowBounds(): void {
  if (!mainWindow) {
    return;
  }
  updateUiSettings({ windowBounds: mainWindow.getBounds() });
}

function setClampedWindowBounds(
  bounds: ResizeSession["bounds"],
  displaySourceBounds: ResizeSession["bounds"] = bounds,
): void {
  if (!mainWindow || mainWindow.isDestroyed()) {
    return;
  }

  isApplyingWindowBounds = true;
  mainWindow.setBounds(clampWindowBounds(bounds, displaySourceBounds));
  isApplyingWindowBounds = false;
}

function applyMove(startBounds: ResizeSession["bounds"], dx: number, dy: number) {
  setClampedWindowBounds(
    {
      ...startBounds,
      x: startBounds.x + dx,
      y: startBounds.y + dy,
    },
    startBounds,
  );
}

function createWindow(): void {
  const uiSettings = readUiSettings();
  mainWindow = new BrowserWindow(createMainWindowOptions(
    __dirname,
    uiSettings.windowBounds,
    screen.getPrimaryDisplay().workAreaSize,
  ));
  mainWindow.setResizable(uiSettings.resizeEnabled);
  mainWindow.setOpacity(uiSettings.opacity);

  mainWindow.on("close", (event) => {
    if (isQuitting) {
      return;
    }

    event.preventDefault();
    mainWindow?.hide();
  });

  mainWindow.on("resize", () => {
    saveCurrentWindowBounds();
  });

  mainWindow.on("move", () => {
    if (!isApplyingWindowBounds) {
      saveCurrentWindowBounds();
    }
  });

  mainWindow.on("ready-to-show", () => {
    // 다른 앱을 사용할 때 MileDay 위젯이 그 위를 덮지 않도록 비활성 상태로 표시한다.
    if (mainWindow) {
      setClampedWindowBounds(mainWindow.getBounds());
    }
    mainWindow?.showInactive();
  });

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
  }
}

function showMainWindow(): void {
  if (!mainWindow || mainWindow.isDestroyed()) {
    createWindow();
    return;
  }

  mainWindow.show();
  mainWindow.focus();
}

function createTray(): void {
  if (tray) {
    return;
  }

  tray = new Tray(getTrayIconPath());
  tray.setToolTip("MileDay");
  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: "MileDay 열기",
        click: showMainWindow,
      },
      {
        label: "숨기기",
        click: () => mainWindow?.hide(),
      },
      { type: "separator" },
      {
        label: "종료",
        click: () => {
          isQuitting = true;
          app.quit();
        },
      },
    ]),
  );

  tray.on("double-click", showMainWindow);
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
  ipcMain.handle("ui-settings:set-font-sizes", (_event, payload: LocalUiFontSizePayload) =>
    updateUiSettings({
      baseFontSize: payload.baseFontSize,
      goalFontSize: payload.goalFontSize,
    }),
  );
  ipcMain.handle("ui-settings:set-resize-enabled", (_event, resizeEnabled: boolean) => {
    mainWindow?.setResizable(resizeEnabled);
    return updateUiSettings({ resizeEnabled });
  });
  ipcMain.handle("ui-settings:set-opacity", (_event, opacity: number) => {
    const normalizedOpacity = normalizeOpacity(opacity);
    mainWindow?.setOpacity(normalizedOpacity);
    return updateUiSettings({ opacity: normalizedOpacity });
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

  ipcMain.handle("window-move:start", (_event, payload: { screenX: number; screenY: number }) => {
    if (!mainWindow) {
      moveSession = null;
      return false;
    }

    moveSession = {
      startX: payload.screenX,
      startY: payload.screenY,
      bounds: mainWindow.getBounds(),
    };
    return true;
  });

  ipcMain.handle("window-move:update", (_event, payload: { screenX: number; screenY: number }) => {
    if (!moveSession) {
      return false;
    }

    applyMove(
      moveSession.bounds,
      payload.screenX - moveSession.startX,
      payload.screenY - moveSession.startY,
    );
    return true;
  });

  ipcMain.handle("window-move:end", () => {
    moveSession = null;
    saveCurrentWindowBounds();
    return true;
  });
}

function registerWindowFocusHandlers(): void {
  ipcMain.handle("window-focus:set-keyboard-focus-required", (_event, required: boolean) => {
    mainWindow?.setFocusable(required);
    if (required) {
      mainWindow?.focus();
    }
    return required;
  });
}

app.whenReady().then(() => {
  app.setAppUserModelId("com.mileday.app");
  registerAutoLaunchHandlers();
  registerAuthTokenHandlers();
  registerUiSettingsHandlers();
  registerWindowFocusHandlers();

  createWindow();
  createTray();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    } else {
      showMainWindow();
    }
  });
});

app.on("before-quit", () => {
  isQuitting = true;
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    if (isQuitting) {
      app.quit();
    }
  }
});
