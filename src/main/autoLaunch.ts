import { app } from 'electron';

export const setAutoLaunchEnabled = (enabled: boolean): void => {
  app.setLoginItemSettings({
    openAtLogin: enabled,
    openAsHidden: true,
  });
};

export const getAutoLaunchEnabled = (): boolean =>
  app.getLoginItemSettings().openAtLogin;

