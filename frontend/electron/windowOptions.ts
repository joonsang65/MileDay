import type { BrowserWindowConstructorOptions } from "electron";
import { join } from "node:path";

export const WINDOW_SIZE_LIMITS = {
  minWidth: 520,
  minHeight: 380,
  maxWidth: 980,
  maxHeight: 760,
} as const;

export function createMainWindowOptions(
  baseDir: string,
  windowBounds?: { x?: number; y?: number; width: number; height: number },
  workAreaSize?: { width: number; height: number },
): BrowserWindowConstructorOptions {
  const defaultBounds = getDefaultWindowBounds(workAreaSize);
  const maxBounds = getMaxWindowBounds(workAreaSize);
  return {
    ...(windowBounds?.x !== undefined ? { x: windowBounds.x } : {}),
    ...(windowBounds?.y !== undefined ? { y: windowBounds.y } : {}),
    width: clamp(windowBounds?.width ?? defaultBounds.width, WINDOW_SIZE_LIMITS.minWidth, maxBounds.width),
    height: clamp(windowBounds?.height ?? defaultBounds.height, WINDOW_SIZE_LIMITS.minHeight, maxBounds.height),
    minWidth: WINDOW_SIZE_LIMITS.minWidth,
    minHeight: WINDOW_SIZE_LIMITS.minHeight,
    maxWidth: maxBounds.width,
    maxHeight: maxBounds.height,
    frame: false,
    resizable: false,
    minimizable: false,
    maximizable: false,
    fullscreenable: false,
    skipTaskbar: true,
    show: false,
    title: "MileDay",
    backgroundColor: "#F7F8FA",
    webPreferences: {
      preload: join(baseDir, "../preload/preload.mjs"),
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
    },
  };
}

function getDefaultWindowBounds(workAreaSize?: { width: number; height: number }) {
  if (!workAreaSize) {
    return { width: 612, height: 422 };
  }

  return {
    width: clamp(Math.round(workAreaSize.width * 0.36), 560, 760),
    height: clamp(Math.round(workAreaSize.height * 0.48), 422, 640),
  };
}

export function getMaxWindowBounds(workAreaSize?: { width: number; height: number }) {
  if (!workAreaSize) {
    return {
      width: WINDOW_SIZE_LIMITS.maxWidth,
      height: WINDOW_SIZE_LIMITS.maxHeight,
    };
  }

  return {
    width: Math.max(WINDOW_SIZE_LIMITS.minWidth, Math.min(workAreaSize.width, WINDOW_SIZE_LIMITS.maxWidth)),
    height: Math.max(WINDOW_SIZE_LIMITS.minHeight, Math.min(workAreaSize.height, WINDOW_SIZE_LIMITS.maxHeight)),
  };
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}
