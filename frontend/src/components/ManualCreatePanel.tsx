import { FormEvent, useEffect, useState } from "react";
import { CalendarPlus, Plus, Trash2 } from "lucide-react";

import type { Goal, GoalCreatePayload, Language, MilestoneCreatePayload } from "@/api/types";
import { FloatingPanel } from "@/components/FloatingPanel";

type ManualCreatePanelProps = {
  selectedDate: string;
  isLoading: boolean;
  goals: Goal[];
  onCreateSchedule: (goalPayloadOrId: string | GoalCreatePayload, milestones: MilestoneCreatePayload[]) => Promise<void>;
  onClose: () => void;
  language: Language;
};

type ManualMilestoneDraft = {
  id: string;
  title: string;
  scheduledDate: string;
};

type CreationMode = "new" | "existing";

const colorOptions = ["#7F9278", "#55A873", "#E59A45", "#8B6FD6", "#D96868", "#8A94A3"];
const labels = {
  ko: {
    title: "일정 추가",
    modeNew: "새 목표 추가",
    modeExisting: "기존 목표에 추가",
    goalTitle: "목표 제목",
    selectGoal: "목표 선택",
    selectGoalRequired: "목표를 선택해 주세요.",
    goalPlaceholder: "예: 데이터 분석 과제 마무리",
    deadline: "마감일",
    color: "색상",
    colorLabel: "색상",
    milestones: "세부 마일스톤",
    name: "이름",
    date: "날짜",
    milestonePlaceholder: "예: 세부 작업",
    deleteMilestone: "마일스톤 삭제",
    addMilestone: "세부 마일스톤 추가",
    cancel: "취소",
    adding: "추가 중",
    add: "일정 추가",
    close: "닫기",
    validation: {
      titleRequired: "목표 제목을 입력해 주세요.",
      deadlineRequired: "마감일을 선택해 주세요.",
      milestoneRequired: "세부 마일스톤을 최소 1개 입력해 주세요.",
      milestoneTitleRequired: "세부 마일스톤 이름을 입력해 주세요.",
      milestoneDateRequired: "세부 마일스톤 날짜를 선택해 주세요.",
      milestoneAfterDeadline: "세부 마일스톤 날짜는 목표 마감일을 넘을 수 없습니다.",
    },
  },
  en: {
    title: "Add Schedule",
    modeNew: "New Goal",
    modeExisting: "Existing Goal",
    goalTitle: "Goal title",
    selectGoal: "Select goal",
    selectGoalRequired: "Please select a goal.",
    goalPlaceholder: "e.g. Finish data analysis assignment",
    deadline: "Deadline",
    color: "Color",
    colorLabel: "Color",
    milestones: "Milestones",
    name: "Name",
    date: "Date",
    milestonePlaceholder: "e.g. Task",
    deleteMilestone: "Delete milestone",
    addMilestone: "Add milestone",
    cancel: "Cancel",
    adding: "Adding",
    add: "Add Schedule",
    close: "Close",
    validation: {
      titleRequired: "Please enter a goal title.",
      deadlineRequired: "Please select a deadline.",
      milestoneRequired: "Please enter at least one milestone.",
      milestoneTitleRequired: "Please enter a milestone name.",
      milestoneDateRequired: "Please select a milestone date.",
      milestoneAfterDeadline: "Milestone dates cannot be after the goal deadline.",
    },
  },
};

export function ManualCreatePanel({
  selectedDate,
  isLoading,
  goals,
  onCreateSchedule,
  onClose,
  language,
}: ManualCreatePanelProps) {
  const text = labels[language];
  const [mode, setMode] = useState<CreationMode>("new");
  const [selectedGoalId, setSelectedGoalId] = useState("");
  const [title, setTitle] = useState("");
  const [deadline, setDeadline] = useState(selectedDate);
  const [color, setColor] = useState(colorOptions[0]);
  const [milestones, setMilestones] = useState<ManualMilestoneDraft[]>([]);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  useEffect(() => {
    setDeadline(selectedDate);
    setMilestones((current) =>
      current.length === 1 && !current[0].title.trim()
        ? [{ ...current[0], scheduledDate: selectedDate }]
        : current,
    );
  }, [selectedDate]);

  function updateMilestone(id: string, patch: Partial<ManualMilestoneDraft>) {
    setMilestones((current) =>
      current.map((milestone) => milestone.id === id ? { ...milestone, ...patch } : milestone),
    );
  }

  function addMilestone() {
    setMilestones((current) => [...current, createMilestoneDraft(selectedDate)]);
  }

  function deleteMilestone(id: string) {
    setMilestones((current) =>
      current.filter((milestone) => milestone.id !== id),
    );
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);
    
    let targetDeadline = deadline;
    let targetColor = color;
    
    if (mode === "new") {
      if (!title.trim()) {
        setValidationMessage(text.validation.titleRequired);
        return;
      }
      if (!deadline) {
        setValidationMessage(text.validation.deadlineRequired);
        return;
      }
    } else {
      if (!selectedGoalId) {
        setValidationMessage(text.selectGoalRequired);
        return;
      }
      const selectedGoal = goals.find(g => g.id === selectedGoalId);
      if (selectedGoal) {
        targetDeadline = selectedGoal.deadline;
        targetColor = selectedGoal.color;
      }
    }
    
    const filledMilestones = milestones.filter((milestone) => milestone.title.trim());
    if (milestones.length === 0 && filledMilestones.length > 0) {
      setValidationMessage(text.validation.milestoneRequired);
      return;
    }
    for (const milestone of filledMilestones) {
      if (!milestone.title.trim()) {
        setValidationMessage(text.validation.milestoneTitleRequired);
        return;
      }
      if (!milestone.scheduledDate) {
        setValidationMessage(text.validation.milestoneDateRequired);
        return;
      }
      if (milestone.scheduledDate > targetDeadline && mode === "new") {
        setValidationMessage(text.validation.milestoneAfterDeadline);
        return;
      }
    }

    const payloadOrId = mode === "new" ? {
      title: title.trim(),
      deadline,
      is_recurring: false,
      recurrence_type: null,
      color,
    } : selectedGoalId;

    await onCreateSchedule(
      payloadOrId,
      filledMilestones.map((milestone) => ({
        title: milestone.title.trim(),
        scheduled_date: milestone.scheduledDate,
        color: targetColor,
      })),
    );
    onClose();
  }

  return (
    <FloatingPanel
      title={text.title}
      onClose={onClose}
      placement="center"
      chrome="plain"
      closeLabel={text.close}
      className="schedule-create-panel"
    >
      <form id="manual-create-form" className="panel-form" onSubmit={handleSubmit} noValidate>
        <div className="creation-tabs">
          <button type="button" className={mode === "new" ? "active" : ""} onClick={() => setMode("new")} disabled={isLoading}>
            {text.modeNew}
          </button>
          <button type="button" className={mode === "existing" ? "active" : ""} onClick={() => setMode("existing")} disabled={isLoading}>
            {text.modeExisting}
          </button>
        </div>

        {mode === "new" ? (
          <div className="manual-goal-row">
            <div className="manual-goal-fields">
              <label>
                {text.goalTitle}
                <input
                  type="text"
                  value={title}
                  onChange={(event) => setTitle(event.target.value)}
                  placeholder={text.goalPlaceholder}
                  disabled={isLoading}
                />
              </label>
              <label>
                {text.deadline}
                <input
                  type="date"
                  value={deadline}
                  onChange={(event) => setDeadline(event.target.value)}
                  disabled={isLoading}
                  required
                />
              </label>
            </div>
            <fieldset className="color-field">
              <legend>{text.color}</legend>
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
                    aria-label={`${text.colorLabel} ${option}`}
                  />
                ))}
              </div>
            </fieldset>
          </div>
        ) : (
          <label>
            {text.selectGoal}
            <select
              value={selectedGoalId}
              onChange={(e) => setSelectedGoalId(e.target.value)}
              disabled={isLoading}
            >
              <option value="">{text.selectGoal}</option>
              {goals.map(g => (
                <option key={g.id} value={g.id}>{g.title}</option>
              ))}
            </select>
          </label>
        )}
        
        <fieldset className="manual-milestone-field">
          <legend>{text.milestones}</legend>
          <ul className="manual-milestone-list">
            {milestones.map((milestone, index) => (
              <li key={milestone.id}>
                <label>
                  {text.name}
                  <input
                    type="text"
                    value={milestone.title}
                    onChange={(event) => updateMilestone(milestone.id, { title: event.target.value })}
                    placeholder={`${text.milestonePlaceholder} ${index + 1}`}
                    disabled={isLoading}
                  />
                </label>
                <label>
                  {text.date}
                  <input
                    type="date"
                    value={milestone.scheduledDate}
                    onChange={(event) => updateMilestone(milestone.id, { scheduledDate: event.target.value })}
                    disabled={isLoading}
                  />
                </label>
                <button
                  type="button"
                  className="icon-button compact-icon danger-icon"
                  onClick={() => deleteMilestone(milestone.id)}
                  disabled={isLoading}
                  title={text.deleteMilestone}
                  aria-label={text.deleteMilestone}
                >
                  <Trash2 size={16} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="secondary-toggle draft-add-button" onClick={addMilestone} disabled={isLoading}>
            <Plus size={16} aria-hidden="true" />
            {text.addMilestone}
          </button>
        </fieldset>
        {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
        <div className="panel-actions">
          <button type="button" className="ghost-button panel-button" onClick={onClose} disabled={isLoading}>
            {text.cancel}
          </button>
          <button type="submit" className="primary-button panel-primary" disabled={isLoading}>
            <CalendarPlus size={16} aria-hidden="true" />
            {isLoading ? text.adding : text.add}
          </button>
        </div>
      </form>
    </FloatingPanel>
  );
}

function createMilestoneDraft(selectedDate: string): ManualMilestoneDraft {
  return {
    id: `manual-milestone-${Date.now()}-${Math.random().toString(36).slice(2)}`,
    title: "",
    scheduledDate: selectedDate,
  };
}
