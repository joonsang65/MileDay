import { FormEvent, useEffect, useState } from "react";
import { LogOut, Save, X } from "lucide-react";

import type { CalendarView, HolidayDisplay, Language, UserSettings, UserSettingsUpdatePayload } from "@/api/types";

type SettingsPanelProps = {
  settings: UserSettings;
  isLoading: boolean;
  onSave: (payload: UserSettingsUpdatePayload) => Promise<void>;
  onClose: () => void;
  onLogout: () => void;
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
    save: "저장",
    close: "닫기",
    logout: "로그아웃",
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
    korean: "한국어",
    english: "English",
    save: "Save",
    close: "Close",
    logout: "Log out",
  },
};

export function SettingsPanel({
  settings,
  isLoading,
  onSave,
  onClose,
  onLogout,
}: SettingsPanelProps) {
  const [calendarView, setCalendarView] = useState<CalendarView>(settings.calendar_view);
  const [holidayDisplay, setHolidayDisplay] = useState<HolidayDisplay>(settings.holiday_display);
  const [weekStartsOn, setWeekStartsOn] = useState<0 | 1>(settings.week_starts_on);
  const [language, setLanguage] = useState<Language>(settings.language);
  const text = labels[language];

  useEffect(() => {
    setCalendarView(settings.calendar_view);
    setHolidayDisplay(settings.holiday_display);
    setWeekStartsOn(settings.week_starts_on);
    setLanguage(settings.language);
  }, [settings]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await onSave({
      calendar_view: calendarView,
      holiday_display: holidayDisplay,
      week_starts_on: weekStartsOn,
      language,
    });
  }

  return (
    <section className="settings-panel" aria-label={text.title}>
      <div className="panel-heading">
        <h2>{text.title}</h2>
        <button type="button" className="icon-button compact-icon" onClick={onClose} title={text.close}>
          <X size={15} aria-hidden="true" />
        </button>
      </div>
      <form className="settings-form" onSubmit={handleSubmit}>
        <label>
          {text.calendarView}
          <select value={calendarView} onChange={(event) => setCalendarView(event.target.value as CalendarView)}>
            <option value="month">{text.month}</option>
            <option value="week">{text.week}</option>
          </select>
        </label>
        <label>
          {text.holidayDisplay}
          <select
            value={holidayDisplay}
            onChange={(event) => setHolidayDisplay(event.target.value as HolidayDisplay)}
          >
            <option value="normal">{text.normal}</option>
            <option value="weekend_like">{text.weekendLike}</option>
            <option value="hidden">{text.hidden}</option>
          </select>
        </label>
        <label>
          {text.weekStartsOn}
          <select value={weekStartsOn} onChange={(event) => setWeekStartsOn(Number(event.target.value) as 0 | 1)}>
            <option value={0}>{text.sunday}</option>
            <option value={1}>{text.monday}</option>
          </select>
        </label>
        <label>
          {text.language}
          <select value={language} onChange={(event) => setLanguage(event.target.value as Language)}>
            <option value="ko">{text.korean}</option>
            <option value="en">{text.english}</option>
          </select>
        </label>
        <button type="submit" className="primary-button compact" disabled={isLoading}>
          <Save size={15} aria-hidden="true" />
          {text.save}
        </button>
      </form>
      <button type="button" className="danger-button settings-logout" onClick={onLogout}>
        <LogOut size={15} aria-hidden="true" />
        {text.logout}
      </button>
    </section>
  );
}
