export type AutoLaunchState = {
  openAtLogin: boolean;
};

type LoginItemSettings = {
  openAtLogin: boolean;
};

type LoginItemApp = {
  getLoginItemSettings: () => LoginItemSettings;
  setLoginItemSettings: (settings: { openAtLogin: boolean; path: string }) => void;
};

export function getAutoLaunchState(app: LoginItemApp): AutoLaunchState {
  return {
    openAtLogin: app.getLoginItemSettings().openAtLogin,
  };
}

export function setAutoLaunchState({
  app,
  openAtLogin,
  executablePath,
}: {
  app: LoginItemApp;
  openAtLogin: boolean;
  executablePath: string;
}): AutoLaunchState {
  app.setLoginItemSettings({
    openAtLogin,
    path: executablePath,
  });
  return getAutoLaunchState(app);
}
