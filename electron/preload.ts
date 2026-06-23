import { contextBridge } from 'electron';

contextBridge.exposeInMainWorld('mileDay', {
  platform: process.platform,
});

