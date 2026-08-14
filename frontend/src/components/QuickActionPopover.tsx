import { CalendarPlus, Sparkles } from "lucide-react";

import type { Language } from "@/api/types";

type QuickActionPopoverProps = {
  onManualCreate: () => void;
  onAiCreate: () => void;
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
  },
  en: {
    menu: "Create schedule",
    title: "Quick Add",
    manual: "Add Schedule",
    manualHint: "Create manually",
    ai: "Schedule Suggestion",
    aiHint: "Get an AI suggestion",
  },
};

export function QuickActionPopover({ onManualCreate, onAiCreate, language }: QuickActionPopoverProps) {
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
    </div>
  );
}
