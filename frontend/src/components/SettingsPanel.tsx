import { FormEvent, useEffect, useState } from "react";
import { ExternalLink, LogOut, Monitor, Save, Settings2, SlidersHorizontal, Trash2 } from "lucide-react";

import type { CalendarView, HolidayDisplay, Language, UserSettings, UserSettingsUpdatePayload } from "@/api/types";
import type { LocalUiSettings, LocalUiSettingsPatch } from "@/types/localUiSettings";

type SettingsPanelProps = {
  settings: UserSettings;
  localUiSettings: LocalUiSettings;
  isLoading: boolean;
  autoLaunch?: {
    get: () => Promise<{ openAtLogin: boolean }>;
    set: (openAtLogin: boolean) => Promise<{ openAtLogin: boolean }>;
  };
  onSave: (payload: UserSettingsUpdatePayload) => Promise<void>;
  onLocalUiSettingsChange?: (payload: LocalUiSettingsPatch) => Promise<void>;
  onClose: () => void;
  onLogout: () => void;
  onDeleteAccount: () => void;
};

const labels = {
  ko: {
    title: "설정",
    calendarView: "기본 캘린더",
    month: "월간",
    week: "주간",
    holidayDisplay: "휴일 표현",
    normal: "이름 표시",
    weekendLike: "주말처럼",
    hidden: "숨김",
    weekStartsOn: "주 시작 요일",
    sunday: "일요일",
    monday: "월요일",
    language: "언어",
    korean: "한국어",
    english: "English",
    baseFontSize: "기본 글자 크기(px)",
    goalFontSize: "목표 글자 크기(px)",
    settingsPanelSize: "시스템 글자",
    settingsPanelSmall: "작게",
    settingsPanelLarge: "크게",
    opacity: "투명도",
    resizeEnabled: "창 크기 조정",
    resizeHint: "켜져 있을 때만 창 모서리를 마우스로 잡아 크기를 조정할 수 있습니다.",
    autoLaunch: "컴퓨터 시작 시 자동 실행",
    autoLaunchHint: "컴퓨터를 켜면 MileDay가 자동으로 시작됩니다.",
    autoLaunchUnavailable: "현재 실행 환경에서는 자동 실행 설정을 사용할 수 없습니다.",
    autoLaunchError: "자동 실행 설정을 변경하지 못했습니다.",
    save: "저장",
    saving: "저장 중",
    survey: "POC 설문 참여",
    close: "닫기",
    logout: "로그아웃",
    deleteAccount: "계정 삭제",
    deleteAccountConfirm: "계정을 삭제하면 목표, 마일스톤, 설정이 모두 삭제됩니다. 계속할까요?",
    basicSection: "기본 설정",
    fontSection: "글자 및 화면",
    advancedSection: "앱 고급 설정",
  },
  en: {
    title: "Settings",
    calendarView: "Default calendar",
    month: "Month",
    week: "Week",
    holidayDisplay: "Holidays",
    normal: "Show names",
    weekendLike: "Weekend style",
    hidden: "Hidden",
    weekStartsOn: "Week starts on",
    sunday: "Sunday",
    monday: "Monday",
    language: "Language",
    korean: "Korean",
    english: "English",
    baseFontSize: "Base font size (px)",
    goalFontSize: "Goal font size (px)",
    settingsPanelSize: "System text size",
    settingsPanelSmall: "Small",
    settingsPanelLarge: "Large",
    opacity: "Opacity",
    resizeEnabled: "Window resizing",
    resizeHint: "When enabled, drag a window edge or corner to resize the widget.",
    autoLaunch: "Open at Windows login",
    autoLaunchHint: "MileDay opens automatically after you turn on this computer and sign in.",
    autoLaunchUnavailable: "Auto launch is unavailable in this runtime.",
    autoLaunchError: "Could not update auto launch.",
    save: "Save",
    saving: "Saving",
    survey: "Open MVP survey",
    close: "Close",
    logout: "Log out",
    deleteAccount: "Delete account",
    deleteAccountConfirm: "Deleting your account removes goals, milestones, and settings. Continue?",
    basicSection: "Basic settings",
    fontSection: "Text and display",
    advancedSection: "Advanced app settings",
  },
};

const SURVEY_URL = "https://forms.gle/TKJzzzX1y39eFNDWA";

export function SettingsPanel({
  settings,
  localUiSettings,
  isLoading,
  autoLaunch = window.mileday?.autoLaunch,
  onSave,
  onLocalUiSettingsChange,
  onLogout,
  onDeleteAccount,
}: SettingsPanelProps) {
  const [calendarView, setCalendarView] = useState<CalendarView>(settings.calendar_view);
  const [holidayDisplay, setHolidayDisplay] = useState<HolidayDisplay>(settings.holiday_display);
  const [weekStartsOn, setWeekStartsOn] = useState<0 | 1>(settings.week_starts_on);
  const [language, setLanguage] = useState<Language>(settings.language);
  const [baseFontSize, setBaseFontSize] = useState(localUiSettings.baseFontSize);
  const [goalFontSize, setGoalFontSize] = useState(localUiSettings.goalFontSize);
  const [settingsPanelSize, setSettingsPanelSize] = useState(localUiSettings.settingsPanelSize);
  const [opacity, setOpacity] = useState(localUiSettings.opacity);
  const [resizeEnabled, setResizeEnabled] = useState(localUiSettings.resizeEnabled);
  const [openAtLogin, setOpenAtLogin] = useState(false);
  const [isAutoLaunchLoading, setIsAutoLaunchLoading] = useState(false);
  const [autoLaunchErrorType, setAutoLaunchErrorType] = useState<"unavailable" | "error" | null>(null);
  const text = labels[language];
  const autoLaunchMessage =
    autoLaunchErrorType === "unavailable"
      ? text.autoLaunchUnavailable
      : autoLaunchErrorType === "error"
        ? text.autoLaunchError
        : null;

  useEffect(() => {
    setCalendarView(settings.calendar_view);
    setHolidayDisplay(settings.holiday_display);
    setWeekStartsOn(settings.week_starts_on);
    setLanguage(settings.language);
  }, [settings]);

  useEffect(() => {
    setBaseFontSize(localUiSettings.baseFontSize);
    setGoalFontSize(localUiSettings.goalFontSize);
    setSettingsPanelSize(localUiSettings.settingsPanelSize);
    setOpacity(localUiSettings.opacity);
    setResizeEnabled(localUiSettings.resizeEnabled);
  }, [localUiSettings]);

  useEffect(() => {
    let isMounted = true;
    if (!autoLaunch) {
      setAutoLaunchErrorType("unavailable");
      return;
    }

    setIsAutoLaunchLoading(true);
    setAutoLaunchErrorType(null);
    void autoLaunch
      .get()
      .then((state) => {
        if (isMounted) {
          setOpenAtLogin(state.openAtLogin);
        }
      })
      .catch(() => {
        if (isMounted) {
          setAutoLaunchErrorType("error");
        }
      })
      .finally(() => {
        if (isMounted) {
          setIsAutoLaunchLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [autoLaunch]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSave({
      calendar_view: calendarView,
      holiday_display: holidayDisplay,
      week_starts_on: weekStartsOn,
      language,
    });
  }

  async function handleAutoLaunchChange(nextValue: boolean) {
    if (!autoLaunch) {
      setAutoLaunchErrorType("unavailable");
      return;
    }

    setIsAutoLaunchLoading(true);
    setAutoLaunchErrorType(null);
    try {
      const state = await autoLaunch.set(nextValue);
      setOpenAtLogin(state.openAtLogin);
    } catch {
      setAutoLaunchErrorType("error");
    } finally {
      setIsAutoLaunchLoading(false);
    }
  }

  async function handleBaseFontSizeChange(nextValue: string) {
    const value = Number(nextValue);
    setBaseFontSize(value);
    if (Number.isFinite(value)) {
      await onLocalUiSettingsChange?.({ baseFontSize: value });
    }
  }

  async function handleGoalFontSizeChange(nextValue: string) {
    const value = Number(nextValue);
    setGoalFontSize(value);
    if (Number.isFinite(value)) {
      await onLocalUiSettingsChange?.({ goalFontSize: value });
    }
  }

  async function handleOpacityChange(nextValue: string) {
    const value = Number(nextValue);
    setOpacity(value);
    if (Number.isFinite(value)) {
      await onLocalUiSettingsChange?.({ opacity: value });
    }
  }

  async function handleSettingsPanelSizeChange(nextValue: LocalUiSettings["settingsPanelSize"]) {
    setSettingsPanelSize(nextValue);
    await onLocalUiSettingsChange?.({ settingsPanelSize: nextValue });
  }

  async function handleResizeEnabledChange(nextValue: boolean) {
    setResizeEnabled(nextValue);
    await onLocalUiSettingsChange?.({ resizeEnabled: nextValue });
  }

  function handleDeleteAccount() {
    if (window.confirm(text.deleteAccountConfirm)) {
      onDeleteAccount();
    }
  }

  return (
    <section className="settings-panel" aria-label={text.title}>
      <form className="settings-form" onSubmit={handleSubmit}>
        <div className="settings-section">
          <div className="settings-section-title">
            <Monitor size={18} aria-hidden="true" />
            <h3>{text.basicSection}</h3>
          </div>
          <label className="settings-field">
            <span>{text.calendarView}</span>
            <select
              value={calendarView}
              onChange={(event) => setCalendarView(event.target.value as CalendarView)}
              disabled={isLoading}
            >
              <option value="month">{text.month}</option>
              <option value="week">{text.week}</option>
            </select>
          </label>
          <label className="settings-field">
            <span>{text.holidayDisplay}</span>
            <select
              value={holidayDisplay}
              onChange={(event) => setHolidayDisplay(event.target.value as HolidayDisplay)}
              disabled={isLoading}
            >
              <option value="normal">{text.normal}</option>
              <option value="weekend_like">{text.weekendLike}</option>
              <option value="hidden">{text.hidden}</option>
            </select>
          </label>
          <label className="settings-field">
            <span>{text.weekStartsOn}</span>
            <select
              value={weekStartsOn}
              onChange={(event) => setWeekStartsOn(Number(event.target.value) as 0 | 1)}
              disabled={isLoading}
            >
              <option value={0}>{text.sunday}</option>
              <option value={1}>{text.monday}</option>
            </select>
          </label>
          <label className="settings-field">
            <span>{text.language}</span>
            <select
              value={language}
              onChange={(event) => setLanguage(event.target.value as Language)}
              disabled={isLoading}
            >
              <option value="ko">{text.korean}</option>
              <option value="en">{text.english}</option>
            </select>
          </label>
        </div>

        <div className="settings-section">
          <div className="settings-section-title">
            <SlidersHorizontal size={18} aria-hidden="true" />
            <h3>{text.fontSection}</h3>
          </div>
          <label className="settings-field settings-field-range">
            <span>{text.baseFontSize}</span>
            <div className="settings-range-row">
              <input
                type="range"
                aria-label={text.baseFontSize}
                min={1}
                max={25}
                step={1}
                value={baseFontSize}
                disabled={isLoading}
                onChange={(event) => void handleBaseFontSizeChange(event.target.value)}
                className="settings-range-input"
              />
              <span className="settings-range-value">
                {baseFontSize}px
              </span>
            </div>
          </label>
          <label className="settings-field settings-field-range">
            <span>{text.goalFontSize}</span>
            <div className="settings-range-row">
              <input
                type="range"
                aria-label={text.goalFontSize}
                min={1}
                max={25}
                step={1}
                value={goalFontSize}
                disabled={isLoading}
                onChange={(event) => void handleGoalFontSizeChange(event.target.value)}
                className="settings-range-input"
              />
              <span className="settings-range-value">
                {goalFontSize}px
              </span>
            </div>
          </label>
          <label className="settings-field settings-field-range">
            <span>{text.opacity}</span>
            <div className="settings-range-row">
              <input
                type="range"
                aria-label={text.opacity}
                min={0.2}
                max={1}
                step={0.05}
                value={opacity}
                disabled={isLoading || !onLocalUiSettingsChange}
                onChange={(event) => void handleOpacityChange(event.target.value)}
                className="settings-range-input"
              />
              <span className="settings-range-value">
                {Math.round(opacity * 100)}%
              </span>
            </div>
          </label>
          <label className="settings-field">
            <span>{text.settingsPanelSize}</span>
            <select
              value={settingsPanelSize}
              onChange={(event) =>
                void handleSettingsPanelSizeChange(event.target.value as LocalUiSettings["settingsPanelSize"])
              }
              disabled={isLoading || !onLocalUiSettingsChange}
            >
              <option value="small">{text.settingsPanelSmall}</option>
              <option value="large">{text.settingsPanelLarge}</option>
            </select>
          </label>
        </div>

        <div className="settings-section settings-section-advanced">
          <div className="settings-section-title">
            <Settings2 size={18} aria-hidden="true" />
            <h3>{text.advancedSection}</h3>
          </div>
          <label className="toggle-row settings-toggle-row">
            <input
              type="checkbox"
              aria-label={text.resizeEnabled}
              checked={resizeEnabled}
              disabled={isLoading || !onLocalUiSettingsChange}
              onChange={(event) => void handleResizeEnabledChange(event.target.checked)}
            />
            <span>
              <strong>{text.resizeEnabled}</strong>
              <small>{text.resizeHint}</small>
            </span>
          </label>
          <label className="toggle-row settings-toggle-row">
            <input
              type="checkbox"
              aria-label={text.autoLaunch}
              checked={openAtLogin}
              disabled={isAutoLaunchLoading || !autoLaunch}
              onChange={(event) => void handleAutoLaunchChange(event.target.checked)}
            />
            <span>
              <strong>{text.autoLaunch}</strong>
              <small>{text.autoLaunchHint}</small>
            </span>
          </label>
          {autoLaunchMessage ? <p className="muted-text">{autoLaunchMessage}</p> : null}
        </div>

        <button type="submit" className="primary-button compact" disabled={isLoading}>
          <Save size={15} aria-hidden="true" />
          {isLoading ? text.saving : text.save}
        </button>
      </form>
      <a className="survey-button" href={SURVEY_URL} target="_blank" rel="noreferrer">
        <ExternalLink size={16} aria-hidden="true" />
        {text.survey}
      </a>
      <button type="button" className="danger-button settings-logout" onClick={onLogout} disabled={isLoading}>
        <LogOut size={15} aria-hidden="true" />
        {text.logout}
      </button>
      <button type="button" className="danger-button settings-delete-account" onClick={handleDeleteAccount} disabled={isLoading}>
        <Trash2 size={15} aria-hidden="true" />
        {text.deleteAccount}
      </button>
    </section>
  );
}
