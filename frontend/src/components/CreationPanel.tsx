import { FormEvent, useEffect, useMemo, useState } from "react";
import { ChevronDown, ChevronUp, Flag, ListPlus, Plus } from "lucide-react";

import type { Goal, GoalCreatePayload, MilestoneCreatePayload, RecurrenceType } from "@/api/types";

type CreationPanelProps = {
  goals: Goal[];
  selectedDate: string;
  isLoading: boolean;
  onCreateGoal: (payload: GoalCreatePayload) => Promise<void>;
  onCreateMilestones: (goalId: string, payloads: MilestoneCreatePayload[]) => Promise<void>;
};

const colorOptions = ["#0F766E", "#D97706", "#4F46E5", "#E11D48", "#16A34A"];

const recurrenceLabels: Record<RecurrenceType, string> = {
  daily: "매일",
  weekly: "매주",
  monthly: "매월",
};

export function CreationPanel({
  goals,
  selectedDate,
  isLoading,
  onCreateGoal,
  onCreateMilestones,
}: CreationPanelProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [goalTitle, setGoalTitle] = useState("");
  const [goalDeadline, setGoalDeadline] = useState(selectedDate);
  const [goalColor, setGoalColor] = useState(colorOptions[0]);
  const [showMilestoneForm, setShowMilestoneForm] = useState(false);
  const [milestoneGoalId, setMilestoneGoalId] = useState("");
  const [milestoneTitle, setMilestoneTitle] = useState("");
  const [milestoneDate, setMilestoneDate] = useState(selectedDate);
  const [milestoneColor, setMilestoneColor] = useState(colorOptions[1]);
  const [isMilestoneRecurring, setIsMilestoneRecurring] = useState(false);
  const [milestoneRecurrenceType, setMilestoneRecurrenceType] = useState<RecurrenceType>("weekly");
  const [milestoneRepeatUntil, setMilestoneRepeatUntil] = useState(selectedDate);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  const hasGoals = goals.length > 0;
  const selectedGoalId = useMemo(() => {
    if (milestoneGoalId) {
      return milestoneGoalId;
    }
    return goals[0]?.id ?? "";
  }, [goals, milestoneGoalId]);

  useEffect(() => {
    setGoalDeadline(selectedDate);
    setMilestoneDate(selectedDate);
    setMilestoneRepeatUntil(selectedDate);
  }, [selectedDate]);

  useEffect(() => {
    if (!milestoneGoalId && goals[0]?.id) {
      setMilestoneGoalId(goals[0].id);
    }
  }, [goals, milestoneGoalId]);

  async function handleGoalSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);
    if (!goalTitle.trim()) {
      setValidationMessage("목표 제목을 입력해 주세요.");
      return;
    }

    await onCreateGoal({
      title: goalTitle.trim(),
      deadline: goalDeadline,
      is_recurring: false,
      recurrence_type: null,
      color: goalColor,
    });
    setGoalTitle("");
    setShowMilestoneForm(true);
  }

  async function handleMilestoneSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);
    if (!hasGoals || !selectedGoalId) {
      setValidationMessage("마일스톤을 만들 목표가 필요합니다.");
      return;
    }
    if (!milestoneTitle.trim()) {
      setValidationMessage("마일스톤 제목을 입력해 주세요.");
      return;
    }

    const scheduledDates = isMilestoneRecurring
      ? buildRecurringDates({
          startDate: milestoneDate,
          endDate: milestoneRepeatUntil,
          recurrenceType: milestoneRecurrenceType,
        })
      : [milestoneDate];

    if (scheduledDates.length === 0) {
      setValidationMessage("반복 종료일은 시작일 이후여야 합니다.");
      return;
    }

    await onCreateMilestones(
      selectedGoalId,
      scheduledDates.map((scheduledDate) => ({
        title: milestoneTitle.trim(),
        scheduled_date: scheduledDate,
        color: milestoneColor,
      })),
    );
    setMilestoneTitle("");
    setIsMilestoneRecurring(false);
    setMilestoneRecurrenceType("weekly");
  }

  return (
    <section className="creation-panel bottom-panel" aria-label="빠른 추가">
      <button
        type="button"
        className="panel-toggle"
        onClick={() => setIsOpen((value) => !value)}
        aria-expanded={isOpen}
      >
        <span>
          <Plus size={16} aria-hidden="true" />
          빠른 추가
        </span>
        {isOpen ? <ChevronDown size={16} aria-hidden="true" /> : <ChevronUp size={16} aria-hidden="true" />}
      </button>

      {isOpen ? (
        <div className="creation-stack">
          <form className="creation-form" onSubmit={handleGoalSubmit}>
            <div className="panel-heading compact-heading">
              <h2>목표</h2>
            </div>
            <label>
              제목
              <input
                type="text"
                value={goalTitle}
                onChange={(event) => setGoalTitle(event.target.value)}
                placeholder="새 목표"
              />
            </label>
            <label>
              마감일
              <input
                type="date"
                value={goalDeadline}
                onChange={(event) => setGoalDeadline(event.target.value)}
                required
              />
            </label>
            <ColorPicker value={goalColor} onChange={setGoalColor} />
            <button type="submit" className="primary-button compact" disabled={isLoading}>
              <ListPlus size={16} aria-hidden="true" />
              목표 추가
            </button>
          </form>

          <div className="inline-divider" />
          <button
            type="button"
            className="secondary-toggle"
            onClick={() => setShowMilestoneForm((value) => !value)}
            disabled={!hasGoals}
          >
            <Flag size={15} aria-hidden="true" />
            {showMilestoneForm ? "마일스톤 닫기" : "마일스톤 추가"}
          </button>

          {showMilestoneForm ? (
            <form className="creation-form" onSubmit={handleMilestoneSubmit}>
              <label>
                목표
                <select
                  value={selectedGoalId}
                  onChange={(event) => setMilestoneGoalId(event.target.value)}
                  disabled={!hasGoals}
                >
                  {goals.map((goal) => (
                    <option key={goal.id} value={goal.id}>
                      {goal.title}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                제목
                <input
                  type="text"
                  value={milestoneTitle}
                  onChange={(event) => setMilestoneTitle(event.target.value)}
                  placeholder="새 마일스톤"
                  disabled={!hasGoals}
                />
              </label>
              <label>
                예정일
                <input
                  type="date"
                  value={milestoneDate}
                  onChange={(event) => {
                    setMilestoneDate(event.target.value);
                    setMilestoneRepeatUntil(event.target.value);
                  }}
                  required
                  disabled={!hasGoals}
                />
              </label>
              <ColorPicker value={milestoneColor} onChange={setMilestoneColor} />
              <label className="toggle-row">
                <input
                  type="checkbox"
                  checked={isMilestoneRecurring}
                  onChange={(event) => setIsMilestoneRecurring(event.target.checked)}
                  disabled={!hasGoals}
                />
                반복 마일스톤
              </label>
              {isMilestoneRecurring ? (
                <>
                  <label>
                    반복 주기
                    <select
                      value={milestoneRecurrenceType}
                      onChange={(event) => setMilestoneRecurrenceType(event.target.value as RecurrenceType)}
                    >
                      {(Object.keys(recurrenceLabels) as RecurrenceType[]).map((value) => (
                        <option key={value} value={value}>
                          {recurrenceLabels[value]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    반복 종료일
                    <input
                      type="date"
                      value={milestoneRepeatUntil}
                      min={milestoneDate}
                      onChange={(event) => setMilestoneRepeatUntil(event.target.value)}
                      required
                    />
                  </label>
                </>
              ) : null}
              {!hasGoals ? <p className="empty-text">목표를 먼저 만들어 주세요.</p> : null}
              {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
              <button type="submit" className="primary-button compact" disabled={isLoading || !hasGoals}>
                <ListPlus size={16} aria-hidden="true" />
                마일스톤 추가
              </button>
            </form>
          ) : null}
          {validationMessage && !showMilestoneForm ? <p className="error-text">{validationMessage}</p> : null}
        </div>
      ) : null}
    </section>
  );
}

function ColorPicker({
  value,
  onChange,
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  return (
    <fieldset className="color-field">
      <legend>색상</legend>
      <div className="color-options">
        {colorOptions.map((color) => (
          <button
            key={color}
            type="button"
            className={value === color ? "selected" : ""}
            style={{ background: color }}
            onClick={() => onChange(color)}
            title={color}
            aria-label={`색상 ${color}`}
          />
        ))}
      </div>
    </fieldset>
  );
}

function buildRecurringDates({
  startDate,
  endDate,
  recurrenceType,
}: {
  startDate: string;
  endDate: string;
  recurrenceType: RecurrenceType;
}) {
  const start = parseDate(startDate);
  const end = parseDate(endDate);
  if (start > end) {
    return [];
  }

  const dates: string[] = [];
  const preferredDay = start.getDate();
  let current = start;
  while (current <= end) {
    dates.push(formatDate(current));
    current = nextDate(current, recurrenceType, preferredDay);
  }
  return dates;
}

function parseDate(value: string) {
  return new Date(`${value}T00:00:00`);
}

function formatDate(value: Date) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function nextDate(current: Date, recurrenceType: RecurrenceType, preferredDay: number) {
  const next = new Date(current);
  if (recurrenceType === "daily") {
    next.setDate(next.getDate() + 1);
    return next;
  }
  if (recurrenceType === "weekly") {
    next.setDate(next.getDate() + 7);
    return next;
  }

  next.setMonth(next.getMonth() + 1, 1);
  const lastDay = new Date(next.getFullYear(), next.getMonth() + 1, 0).getDate();
  next.setDate(Math.min(preferredDay, lastDay));
  return next;
}
