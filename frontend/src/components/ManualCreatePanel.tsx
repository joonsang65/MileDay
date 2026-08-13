import { FormEvent, useEffect, useState } from "react";
import { CalendarPlus } from "lucide-react";

import type { GoalCreatePayload } from "@/api/types";
import { FloatingPanel } from "@/components/FloatingPanel";

type ManualCreatePanelProps = {
  selectedDate: string;
  isLoading: boolean;
  onCreateGoal: (payload: GoalCreatePayload) => Promise<void>;
  onClose: () => void;
};

const colorOptions = ["#7F9278", "#55A873", "#E59A45", "#8B6FD6", "#D96868", "#8A94A3"];

export function ManualCreatePanel({
  selectedDate,
  isLoading,
  onCreateGoal,
  onClose,
}: ManualCreatePanelProps) {
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState(selectedDate);
  const [color, setColor] = useState(colorOptions[0]);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  useEffect(() => {
    setDeadline(selectedDate);
  }, [selectedDate]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);
    if (!title.trim()) {
      setValidationMessage("목표 제목을 입력해 주세요.");
      return;
    }
    if (!deadline) {
      setValidationMessage("마감일을 선택해 주세요.");
      return;
    }

    await onCreateGoal({
      title: title.trim(),
      deadline,
      is_recurring: false,
      recurrence_type: null,
      color,
    });
    onClose();
  }

  return (
    <FloatingPanel
      title="일정 추가"
      onClose={onClose}
      footer={
        <>
          <button type="button" className="ghost-button panel-button" onClick={onClose} disabled={isLoading}>
            취소
          </button>
          <button type="submit" form="manual-create-form" className="primary-button panel-primary" disabled={isLoading}>
            <CalendarPlus size={16} aria-hidden="true" />
            {isLoading ? "추가 중" : "목표 추가"}
          </button>
        </>
      }
    >
      <form id="manual-create-form" className="panel-form" onSubmit={handleSubmit} noValidate>
        <label>
          목표 제목
          <input
            type="text"
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="예: 데이터 분석 과제 마무리"
            disabled={isLoading}
          />
        </label>
        <label>
          마감일
          <input
            type="date"
            value={deadline}
            onChange={(event) => setDeadline(event.target.value)}
            disabled={isLoading}
            required
          />
        </label>
        <fieldset className="color-field">
          <legend>색상</legend>
          <div className="color-options">
            {colorOptions.map((option) => (
              <button
                key={option}
                type="button"
                className={option === color ? "selected" : ""}
                style={{ background: option }}
                onClick={() => setColor(option)}
                disabled={isLoading}
                title={option}
                aria-label={`색상 ${option}`}
              />
            ))}
          </div>
        </fieldset>
        {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      </form>
    </FloatingPanel>
  );
}
