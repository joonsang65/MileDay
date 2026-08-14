import type { BrowserWindowConstructorOptions } from "electron";
import { join } from "node:path";

export function createMainWindowOptions(
  baseDir: string,
  windowBounds?: { x?: number; y?: number; width: number; height: number },
): BrowserWindowConstructorOptions {
  return {
    ...(windowBounds?.x !== undefined ? { x: windowBounds.x } : {}),
    ...(windowBounds?.y !== undefined ? { y: windowBounds.y } : {}),
    width: windowBounds?.width ?? 612,
    height: windowBounds?.height ?? 422,
    minWidth: 381,
    minHeight: 299,
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
