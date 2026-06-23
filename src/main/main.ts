import { app } from 'electron';
import { markQuitting } from './lifecycle';
import { createAppTray } from './tray';
import { createMainWindow, registerWindowIpc, showMainWindow } from './window';

const gotSingleInstanceLock = app.requestSingleInstanceLock();

if (!gotSingleInstanceLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    showMainWindow();
  });

  app.whenReady().then(() => {
    registerWindowIpc();
    createMainWindow();
    createAppTray();

    app.on('activate', () => {
      showMainWindow();
    });
  });

  app.on('before-quit', () => {
    markQuitting();
  });

  app.on('window-all-closed', () => {});
}
