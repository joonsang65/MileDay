import { CalendarDays, ChevronLeft, ChevronRight, LogOut, RefreshCw } from "lucide-react";

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
  onLogout: () => void;
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
  onLogout,
}: CalendarHeaderProps) {
  return (
    <header className="app-header">
      <div className="header-title">
        <p className="eyebrow">MileDay</p>
        <h1>{label}</h1>
      </div>
      <div className="header-actions">
        <div className="segmented" role="group" aria-label="캘린더 표시 방식">
          <button
            type="button"
            className={mode === "month" ? "active" : ""}
            onClick={() => onModeChange("month")}
          >
            월
          </button>
          <button
            type="button"
            className={mode === "week" ? "active" : ""}
            onClick={() => onModeChange("week")}
          >
            주
          </button>
        </div>
        <button type="button" className="icon-button" onClick={onPrevious} title="이전">
          <ChevronLeft size={18} aria-hidden="true" />
        </button>
        <button type="button" className="ghost-button" onClick={onToday}>
          <CalendarDays size={17} aria-hidden="true" />
          오늘
        </button>
        <button type="button" className="icon-button" onClick={onNext} title="다음">
          <ChevronRight size={18} aria-hidden="true" />
        </button>
        <button
          type="button"
          className="icon-button"
          onClick={onRefresh}
          disabled={isLoading}
          title="새로고침"
        >
          <RefreshCw size={17} aria-hidden="true" />
        </button>
        <button type="button" className="icon-button" onClick={onLogout} title="로그아웃">
          <LogOut size={17} aria-hidden="true" />
        </button>
      </div>
    </header>
  );
}
