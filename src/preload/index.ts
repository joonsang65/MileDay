import { contextBridge, ipcRenderer } from 'electron';
import type { AppSettings, WidgetSettings, WindowState } from '../main/store';

contextBridge.exposeInMainWorld('mileDayWidget', {
  getSettings: (): Promise<AppSettings> => ipcRenderer.invoke('widget:get-settings'),
  getWidgetSettings: (): Promise<WidgetSettings> =>
    ipcRenderer.invoke('widget:get-widget-settings'),
  updateWidgetSettings: (
    settings: Partial<WidgetSettings>,
  ): Promise<AppSettings> =>
    ipcRenderer.invoke('widget:update-widget-settings', settings),
  setAlwaysOnTop: (alwaysOnTop: boolean): Promise<AppSettings> =>
    ipcRenderer.invoke('widget:set-always-on-top', alwaysOnTop),
  getWindowBounds: (): Promise<WindowState> =>
    ipcRenderer.invoke('widget:get-window-bounds'),
  resizeWindow: (width: number, height: number): Promise<AppSettings> =>
    ipcRenderer.invoke('widget:resize-window', width, height),
  show: (): Promise<void> => ipcRenderer.invoke('widget:show'),
  hide: (): Promise<void> => ipcRenderer.invoke('widget:hide'),
});
