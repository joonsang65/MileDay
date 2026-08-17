import type { PointerEvent as ReactPointerEvent } from "react";
import { CalendarDays, ChevronLeft, ChevronRight, Settings } from "lucide-react";

import type { Language } from "@/api/types";
import type { CalendarMode } from "@/store/calendarStore";

type CalendarHeaderProps = {
  label: string;
  mode: CalendarMode;
  onModeChange: (mode: CalendarMode) => void;
  onPrevious: () => void;
  onNext: () => void;
  onToday: () => void;
  onOpenSettings: () => void;
  onWindowMoveStart?: (event: ReactPointerEvent<HTMLElement>) => void;
  language: Language;
};

export function CalendarHeader({
  label,
  mode,
  onModeChange,
  onPrevious,
  onNext,
  onToday,
  onOpenSettings,
  onWindowMoveStart,
  language,
}: CalendarHeaderProps) {
  const text = language === "en"
    ? {
        modeLabel: "Calendar view",
        month: "MO",
        week: "WK",
        today: "Today",
        previous: "Previous",
        next: "Next",
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
        settings: "설정",
        add: "일정 만들기",
      };

  return (
    <header className="app-header" onPointerDown={onWindowMoveStart}>
      <div className="header-title">
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
        <button type="button" className="icon-button" data-testid="settings-button" onClick={onOpenSettings} title={text.settings}>
          <Settings size={17} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
