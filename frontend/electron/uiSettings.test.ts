import { beforeEach, describe, expect, it, vi } from "vitest";

const state = vi.hoisted(() => ({
  file: "" as string | null,
  failWrite: false,
  handlers: new Map<string, (...args: unknown[]) => unknown>(),
}));

vi.mock("node:fs", () => {
  const fs = {
  existsSync: () => state.file !== null,
  readFileSync: () => state.file,
  writeFileSync: (_path: string, value: string) => {
    if (state.failWrite) throw new Error("disk full");
    state.file = value;
  },
  unlinkSync: vi.fn(),
  };
  return { ...fs, default: fs };
});
vi.mock("electron", () => {
  const electron = {
  app: { getPath: () => "C:/fake-mileday", whenReady: () => Promise.resolve(), on: vi.fn(), setAppUserModelId: vi.fn() },
  ipcMain: { handle: (name: string, handler: (...args: unknown[]) => unknown) => state.handlers.set(name, handler) },
  BrowserWindow: class {
    setResizable() {} setOpacity() {} on() {} loadFile() {} loadURL() {}
  },
  Tray: class { setToolTip() {} setContextMenu() {} on() {} },
  Menu: { buildFromTemplate: vi.fn() },
  safeStorage: {},
  screen: { getPrimaryDisplay: () => ({ workAreaSize: { width: 1920, height: 1080 } }) },
  };
  return { ...electron, default: electron };
});

beforeEach(() => {
  state.file = null;
  state.failWrite = false;
  state.handlers.clear();
  vi.resetModules();
  vi.stubGlobal("__dirname", "C:/fake-mileday/out/main");
});

async function startMain() {
  await import("./main");
  await Promise.resolve();
}
function invoke(name: string, value?: unknown) {
  return state.handlers.get(name)!(null, value) as Record<string, unknown>;
}

describe("Electron local side panel settings", () => {
  it("defaults missing fields to false and preserves existing settings and window bounds", async () => {
    state.file = JSON.stringify({ baseFontSize: 18, opacity: 0.8, resizeEnabled: true, windowBounds: { x: 20, y: 30, width: 640, height: 480 } });
    await startMain();
    expect(invoke("ui-settings:get").todaySidePanelEnabled).toBe(false);
    invoke("ui-settings:set-today-side-panel-enabled", true);
    const saved = JSON.parse(state.file!);
    expect(saved).toMatchObject({ todaySidePanelEnabled: true, baseFontSize: 18, opacity: 0.8, resizeEnabled: true, windowBounds: { x: 20, y: 30, width: 640, height: 480 } });
    vi.resetModules();
    await startMain();
    expect(invoke("ui-settings:get").todaySidePanelEnabled).toBe(true);
    invoke("ui-settings:set-today-side-panel-enabled", false);
    expect(invoke("ui-settings:get").todaySidePanelEnabled).toBe(false);
  });

  it("propagates write failures without changing the persisted setting", async () => {
    await startMain();
    invoke("ui-settings:set-today-side-panel-enabled", true);
    state.failWrite = true;
    expect(() => invoke("ui-settings:set-today-side-panel-enabled", false)).toThrow("disk full");
    expect(invoke("ui-settings:get").todaySidePanelEnabled).toBe(true);
  });
});
