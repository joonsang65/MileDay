import { CalendarDays, ChevronLeft, ChevronRight, Plus, RefreshCw, Settings } from "lucide-react";

import type { Language } from "@/api/types";
import type { CalendarMode } from "@/store/calendarStore";

type CalendarHeaderProps = {
  label: string;
  mode: CalendarMode;
  isLoading: boolean;
  onModeChange: (mode: CalendarMode) => void;
  onPrevious: () => void;
  onNext: () => void;
  onToday: () => void;
  onRefresh: () => void;
  onOpenSettings: () => void;
  onOpenQuickMenu: () => void;
  language: Language;
};

export function CalendarHeader({
  label,
  mode,
  isLoading,
  onModeChange,
  onPrevious,
  onNext,
  onToday,
  onRefresh,
  onOpenSettings,
  onOpenQuickMenu,
  language,
}: CalendarHeaderProps) {
  const text = language === "en"
    ? {
        modeLabel: "Calendar view",
        month: "Month",
        week: "Week",
        today: "Today",
        previous: "Previous",
        next: "Next",
        refresh: "Refresh",
        settings: "Settings",
        add: "Add schedule",
      }
    : {
        modeLabel: "캘린더 표시 방식",
        month: "월",
        week: "주",
        today: "오늘",
        previous: "이전",
        next: "다음",
        refresh: "새로고침",
        settings: "설정",
        add: "일정 만들기",
      };

  return (
    <header className="app-header">
      <div className="header-title">
        <p className="eyebrow">MILEDAY</p>
        <h1>{label}</h1>
      </div>
      <div className="header-actions">
        <div className="segmented" role="group" aria-label={text.modeLabel}>
          <button
            type="button"
            className={mode === "month" ? "active" : ""}
            onClick={() => onModeChange("month")}
          >
            {text.month}
          </button>
          <button
            type="button"
            className={mode === "week" ? "active" : ""}
            onClick={() => onModeChange("week")}
          >
            {text.week}
          </button>
        </div>
        <button type="button" className="icon-button" onClick={onPrevious} title={text.previous}>
          <ChevronLeft size={18} aria-hidden="true" />
        </button>
        <button type="button" className="ghost-button" onClick={onToday}>
          <CalendarDays size={17} aria-hidden="true" />
          {text.today}
        </button>
        <button type="button" className="icon-button" onClick={onNext} title={text.next}>
          <ChevronRight size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="icon-button"
          onClick={onRefresh}
          disabled={isLoading}
          title={text.refresh}
        >
          <RefreshCw size={17} aria-hidden="true" />
        </button>
        <button type="button" className="icon-button" onClick={onOpenSettings} title={text.settings}>
          <Settings size={17} aria-hidden="true" />
        </button>
        <button type="button" className="add-button" onClick={onOpenQuickMenu} title={text.add}>
          <Plus size={19} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
