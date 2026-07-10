import { contextBridge } from "electron";

contextBridge.exposeInMainWorld("mileday", {
  platform: process.platform,
});
