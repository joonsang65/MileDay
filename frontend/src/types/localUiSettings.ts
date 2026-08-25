export type LocalUiSettings = {
  baseFontSize: number;
  goalFontSize: number;
  resizeEnabled: boolean;
  theme: "system";
  fontFamily: "system";
  opacity: number;
};

export type LocalUiSettingsPatch = Partial<LocalUiSettings>;

export type LocalUiFontSizePayload = Pick<LocalUiSettings, "baseFontSize" | "goalFontSize">;

export const DEFAULT_LOCAL_UI_SETTINGS: LocalUiSettings = {
  baseFontSize: 12,
  goalFontSize: 13,
  resizeEnabled: false,
  theme: "system",
  fontFamily: "system",
  opacity: 1,
};
