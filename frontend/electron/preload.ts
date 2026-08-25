import { contextBridge, ipcRenderer } from "electron";
import type { LocalUiFontSizePayload } from "../src/types/localUiSettings";

contextBridge.exposeInMainWorld("mileday", {
  platform: process.platform,
  autoLaunch: {
    get: () => ipcRenderer.invoke("auto-launch:get"),
    set: (openAtLogin: boolean) => ipcRenderer.invoke("auto-launch:set", openAtLogin),
  },
  authToken: {
    get: () => ipcRenderer.invoke("auth-token:get"),
    set: (accessToken: string) => ipcRenderer.invoke("auth-token:set", accessToken),
    clear: () => ipcRenderer.invoke("auth-token:clear"),
    isEncryptionAvailable: () => ipcRenderer.invoke("auth-token:is-encryption-available"),
  },
  uiSettings: {
    get: () => ipcRenderer.invoke("ui-settings:get"),
    setFontSizes: (payload: LocalUiFontSizePayload) =>
      ipcRenderer.invoke("ui-settings:set-font-sizes", payload),
    setResizeEnabled: (resizeEnabled: boolean) =>
      ipcRenderer.invoke("ui-settings:set-resize-enabled", resizeEnabled),
    setOpacity: (opacity: number) =>
      ipcRenderer.invoke("ui-settings:set-opacity", opacity),
  },
  windowResize: {
    start: (payload: { direction: string; screenX: number; screenY: number }) =>
      ipcRenderer.invoke("window-resize:start", payload),
    update: (payload: { screenX: number; screenY: number }) =>
      ipcRenderer.invoke("window-resize:update", payload),
    end: () => ipcRenderer.invoke("window-resize:end"),
  },
  windowMove: {
    start: (payload: { screenX: number; screenY: number }) =>
      ipcRenderer.invoke("window-move:start", payload),
    update: (payload: { screenX: number; screenY: number }) =>
      ipcRenderer.invoke("window-move:update", payload),
    end: () => ipcRenderer.invoke("window-move:end"),
  },
  windowFocus: {
    setKeyboardFocusRequired: (required: boolean) =>
      ipcRenderer.invoke("window-focus:set-keyboard-focus-required", required),
  },
});
