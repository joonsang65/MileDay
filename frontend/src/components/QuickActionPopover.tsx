import { CalendarPlus, Sparkles, ListTodo } from "lucide-react";

import type { Language } from "@/api/types";

type QuickActionPopoverProps = {
  onManualCreate: () => void;
  onAiCreate: () => void;
  onGoalList: () => void;
  language: Language;
};

const labels = {
  ko: {
    menu: "일정 만들기",
    title: "빠른 추가",
    manual: "일정 추가",
    manualHint: "직접 일정 만들기",
    ai: "일정 추천",
    aiHint: "AI에게 제안받기",
    goals: "전체 목표",
    goalsHint: "전체 목표 관리하기",
  },
  en: {
    menu: "Create schedule",
    title: "Quick Add",
    manual: "Add Schedule",
    manualHint: "Create manually",
    ai: "Schedule Suggestion",
    aiHint: "Get an AI suggestion",
    goals: "All Goals",
    goalsHint: "Manage all goals",
  },
};

export function QuickActionPopover({ onManualCreate, onAiCreate, onGoalList, language }: QuickActionPopoverProps) {
  const text = labels[language];
  return (
    <div className="quick-action-popover" role="menu" aria-label={text.menu}>
      <h2>{text.title}</h2>
      <button type="button" role="menuitem" onClick={onManualCreate}>
        <span className="quick-action-icon">
          <CalendarPlus size={31} aria-hidden="true" />
        </span>
        <span>
          <strong>{text.manual}</strong>
          <small>{text.manualHint}</small>
        </span>
      </button>
      <button type="button" role="menuitem" onClick={onAiCreate}>
        <span className="quick-action-icon">
          <Sparkles size={31} aria-hidden="true" />
        </span>
        <span>
          <strong>{text.ai}</strong>
          <small>{text.aiHint}</small>
        </span>
      </button>
      <button type="button" role="menuitem" onClick={onGoalList}>
        <span className="quick-action-icon">
          <ListTodo size={31} aria-hidden="true" />
        </span>
        <span>
          <strong>{text.goals}</strong>
          <small>{text.goalsHint}</small>
        </span>
      </button>
    </div>
  );
}
