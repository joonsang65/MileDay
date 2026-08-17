import { describe, expect, it } from "vitest";

import { createMainWindowOptions } from "./windowOptions";

describe("createMainWindowOptions", () => {
  it("데스크톱 위젯처럼 프레임 없는 비상단 창 옵션을 만든다", () => {
    const options = createMainWindowOptions("C:/app/out/main");

    expect(options).toMatchObject({
      width: 612,
      height: 422,
      minWidth: 520,
      minHeight: 380,
      maxWidth: 980,
      maxHeight: 760,
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
      width: 520,
      height: 380,
    });

    expect(options).toMatchObject({
      x: 120,
      y: 80,
      width: 520,
      height: 380,
    });
  });

  it("clamps saved window size to the widget limits", () => {
    const options = createMainWindowOptions(
      "C:/app/out/main",
      {
        x: 120,
        y: 80,
        width: 1800,
        height: 1200,
      },
      { width: 1920, height: 1080 },
    );

    expect(options).toMatchObject({
      width: 980,
      height: 760,
      maxWidth: 980,
      maxHeight: 760,
    });
  });

  it("sizes the default widget window from the display work area", () => {
    const options = createMainWindowOptions(
      "C:/app/out/main",
      undefined,
      { width: 1920, height: 1080 },
    );

    expect(options).toMatchObject({
      width: 691,
      height: 518,
    });
  });
});
