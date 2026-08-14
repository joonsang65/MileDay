import { describe, expect, it } from "vitest";

import { createMainWindowOptions } from "./windowOptions";

describe("createMainWindowOptions", () => {
  it("데스크톱 위젯처럼 프레임 없는 비상단 창 옵션을 만든다", () => {
    const options = createMainWindowOptions("C:/app/out/main");

    expect(options).toMatchObject({
      width: 900,
      height: 620,
      frame: false,
      resizable: false,
      minimizable: false,
      maximizable: false,
      fullscreenable: false,
      skipTaskbar: true,
      show: false,
    });
    expect(options).not.toHaveProperty("alwaysOnTop");
    expect(options.webPreferences).toMatchObject({
      sandbox: false,
      contextIsolation: true,
      nodeIntegration: false,
    });
  });

  it("uses saved window position and size when bounds are provided", () => {
    const options = createMainWindowOptions("C:/app/out/main", {
      x: 120,
      y: 80,
      width: 560,
      height: 440,
    });

    expect(options).toMatchObject({
      x: 120,
      y: 80,
      width: 560,
      height: 440,
    });
  });
});
