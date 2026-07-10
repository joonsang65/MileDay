import { app, BrowserWindow } from "electron";
import { join } from "node:path";

import { createMainWindowOptions } from "./windowOptions";

let mainWindow: BrowserWindow | null = null;

function createWindow(): void {
  mainWindow = new BrowserWindow(createMainWindowOptions(__dirname));

  mainWindow.on("ready-to-show", () => {
    // 다른 앱을 사용할 때 MileDay 위젯이 그 위를 덮지 않도록 비활성 상태로 표시한다.
    mainWindow?.showInactive();
  });

  if (process.env.ELECTRON_RENDERER_URL) {
    mainWindow.loadURL(process.env.ELECTRON_RENDERER_URL);
  } else {
    mainWindow.loadFile(join(__dirname, "../renderer/index.html"));
  }
}

app.whenReady().then(() => {
  app.setAppUserModelId("com.mileday.app");

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
