import type { BrowserWindowConstructorOptions } from "electron";
import { join } from "node:path";

export function createMainWindowOptions(baseDir: string): BrowserWindowConstructorOptions {
  return {
    width: 900,
    height: 620,
    minWidth: 760,
    minHeight: 540,
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
