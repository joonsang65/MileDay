import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("mileday", {
  platform: process.platform,
  autoLaunch: {
    get: () => ipcRenderer.invoke("auto-launch:get"),
    set: (openAtLogin: boolean) => ipcRenderer.invoke("auto-launch:set", openAtLogin),
  },
});
