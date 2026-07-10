import { describe, expect, it, vi } from "vitest";

import { getAutoLaunchState, setAutoLaunchState } from "./autoLaunch";

describe("autoLaunch", () => {
  it("Electron login item 상태를 조회한다", () => {
    const app = {
      getLoginItemSettings: vi.fn(() => ({ openAtLogin: true })),
      setLoginItemSettings: vi.fn(),
    };

    expect(getAutoLaunchState(app)).toEqual({ openAtLogin: true });
  });

  it("자동 실행 상태를 변경하고 변경 후 상태를 반환한다", () => {
    let openAtLogin = false;
    const app = {
      getLoginItemSettings: vi.fn(() => ({ openAtLogin })),
      setLoginItemSettings: vi.fn((settings: { openAtLogin: boolean }) => {
        openAtLogin = settings.openAtLogin;
      }),
    };

    const result = setAutoLaunchState({
      app,
      openAtLogin: true,
      executablePath: "C:/MileDay/MileDay.exe",
    });

    expect(app.setLoginItemSettings).toHaveBeenCalledWith({
      openAtLogin: true,
      path: "C:/MileDay/MileDay.exe",
    });
    expect(result).toEqual({ openAtLogin: true });
  });
});
