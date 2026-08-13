import { Bot, CalendarPlus } from "lucide-react";

type QuickActionPopoverProps = {
  onManualCreate: () => void;
  onAiCreate: () => void;
};

export function QuickActionPopover({ onManualCreate, onAiCreate }: QuickActionPopoverProps) {
  return (
    <div className="quick-action-popover" role="menu" aria-label="일정 만들기">
      <button type="button" role="menuitem" onClick={onManualCreate}>
        <CalendarPlus size={17} aria-hidden="true" />
        <span>
          <strong>일정 추가</strong>
          <small>직접 목표를 만들어요</small>
        </span>
      </button>
      <button type="button" role="menuitem" onClick={onAiCreate}>
        <Bot size={17} aria-hidden="true" />
        <span>
          <strong>일정 추천</strong>
          <small>AI 초안을 받아요</small>
        </span>
      </button>
    </div>
  );
}
