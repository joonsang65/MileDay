import { Menu, Tray, app, nativeImage } from 'electron';
import { markQuitting } from './lifecycle';
import { hideMainWindow, showMainWindow } from './window';

let tray: Tray | null = null;

const trayIconSvg = `
<svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 32 32">
  <rect width="32" height="32" rx="8" fill="#0f172a"/>
  <path d="M9 9h14v14H9z" fill="#38bdf8" opacity=".2"/>
  <path d="M11 12h10M11 16h10M11 20h6" stroke="#e0f2fe" stroke-width="2" stroke-linecap="round"/>
</svg>`;

const createTrayImage = () =>
  nativeImage.createFromDataURL(
    `data:image/svg+xml;base64,${Buffer.from(trayIconSvg).toString('base64')}`,
  );

export const createAppTray = (): Tray => {
  if (tray) {
    return tray;
  }

  tray = new Tray(createTrayImage());
  tray.setToolTip('MileDay');
  tray.setContextMenu(
    Menu.buildFromTemplate([
      {
        label: 'Show',
        click: () => showMainWindow(),
      },
      {
        label: 'Hide',
        click: () => hideMainWindow(),
      },
      { type: 'separator' },
      {
        label: 'Quit',
        click: () => {
          markQuitting();
          app.quit();
        },
      },
    ]),
  );
  tray.on('double-click', () => showMainWindow());

  return tray;
};
