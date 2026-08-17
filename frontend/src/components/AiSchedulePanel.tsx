import { FormEvent, useState } from "react";
import { Bot, GripVertical, ListPlus, Plus, RefreshCw, Trash2 } from "lucide-react";

import type {
  AiScheduleDraft,
  AiScheduleDraftMilestone,
  AiScheduleDraftRequest,
  GoalCreatePayload,
  Language,
  MilestoneCreatePayload,
} from "@/api/types";
import { FloatingPanel } from "@/components/FloatingPanel";

type AiPanelStep = "input" | "loading" | "draft" | "error";

type AiSchedulePanelProps = {
  selectedDate: string;
  today: string;
  timezone: string;
  availability: AiScheduleDraftRequest["availability"];
  isSaving: boolean;
  onCreateDraft: (payload: AiScheduleDraftRequest) => Promise<AiScheduleDraft>;
  onSaveDraft: (goal: GoalCreatePayload, milestones: MilestoneCreatePayload[]) => Promise<void>;
  onClose: () => void;
  language: Language;
};

const labels = {
  ko: {
    title: "일정 추천",
    description: "목표를 바탕으로 일정 초안을 준비해 드립니다.",
    defaultPrompt: "9월 말까지 데이터 분석 과제를 끝내고 싶어. 가능한 날짜 안에서 너무 빡빡하지 않게 초안을 잡아줘.",
    promptRequired: "목표를 자연어로 입력해 주세요.",
    draftFailedFallback: "일정 제안에 실패했습니다.",
    draftFailed: "일정 제안에 실패했습니다. 입력한 내용은 그대로 유지됩니다.",
    retryFailed: "다시 제안에 실패했습니다. 기존 초안은 유지됩니다.",
    creating: "제안 만드는 중",
    create: "제안 만들기",
    goalTitle: "목표 제목",
    deadline: "마감일",
    selectedCount: "개 선택",
    select: "선택",
    milestoneTitle: "마일스톤 제목",
    milestoneDate: "마일스톤 날짜",
    delete: "삭제",
    addMilestone: "마일스톤 추가",
    extraMilestone: "추가 작업",
    retry: "다시 제안",
    cancel: "취소",
    adding: "추가 중",
    addToSchedule: "일정에 추가",
    close: "닫기",
    validation: {
      goalTitleRequired: "목표 제목을 입력해 주세요.",
      deadlineRequired: "마감일을 선택해 주세요.",
      selectedRequired: "선택한 마일스톤이 최소 1개 필요합니다.",
      emptyMilestoneTitle: "비어 있는 마일스톤 제목이 있습니다.",
      milestoneDateRequired: "마일스톤 날짜를 모두 선택해 주세요.",
      milestoneAfterDeadline: "마일스톤 날짜는 마감일을 넘을 수 없습니다.",
    },
  },
  en: {
    title: "Schedule Suggestion",
    description: "MileDay prepares a schedule draft from your goal.",
    defaultPrompt: "I want to finish a data analysis assignment by the end of September. Make a balanced draft within my available dates.",
    promptRequired: "Please describe your goal in natural language.",
    draftFailedFallback: "Could not create a schedule suggestion.",
    draftFailed: "Could not create a suggestion. Your input is still here.",
    retryFailed: "Could not regenerate the suggestion. The current draft is kept.",
    creating: "Creating suggestion",
    create: "Create suggestion",
    goalTitle: "Goal title",
    deadline: "Deadline",
    selectedCount: "selected",
    select: "Select",
    milestoneTitle: "Milestone title",
    milestoneDate: "Milestone date",
    delete: "Delete",
    addMilestone: "Add milestone",
    extraMilestone: "Extra task",
    retry: "Regenerate",
    cancel: "Cancel",
    adding: "Adding",
    addToSchedule: "Add to schedule",
    close: "Close",
    validation: {
      goalTitleRequired: "Please enter a goal title.",
      deadlineRequired: "Please select a deadline.",
      selectedRequired: "Select at least one milestone.",
      emptyMilestoneTitle: "There is an empty milestone title.",
      milestoneDateRequired: "Please select all milestone dates.",
      milestoneAfterDeadline: "Milestone dates cannot be after the deadline.",
    },
  },
};

export function AiSchedulePanel({
  selectedDate,
  today,
  timezone,
  availability,
  isSaving,
  onCreateDraft,
  onSaveDraft,
  onClose,
  language,
}: AiSchedulePanelProps) {
  const text = labels[language];
  const [step, setStep] = useState<AiPanelStep>("input");
  const [prompt, setPrompt] = useState("");
  const [draft, setDraft] = useState<AiScheduleDraft | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [draggingId, setDraggingId] = useState<string | null>(null);

  const isBusy = step === "loading" || isSaving;

  async function requestDraft() {
    setErrorMessage(null);
    setValidationMessage(null);
    if (!prompt.trim()) {
      setValidationMessage(text.promptRequired);
      return;
    }
    setStep("loading");
    try {
      const nextDraft = await onCreateDraft({
        prompt: prompt.trim(),
        today,
        timezone,
        availability,
      });
      setDraft(nextDraft);
      setStep("draft");
    } catch (error) {
      setErrorMessage(error instanceof Error ? error.message : text.draftFailedFallback);
      setStep(draft ? "draft" : "error");
    }
  }

  async function handleInputSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await requestDraft();
  }

  async function handleSaveDraft() {
    if (!draft) {
      return;
    }
    const validation = validateEditableDraft(draft, text.validation);
    if (validation) {
      setValidationMessage(validation);
      return;
    }
    const goalColor = draft.create_goal_payload.goal.color || "#7F9278";
    await onSaveDraft(
      {
        title: draft.goal.title.trim(),
        deadline: draft.goal.deadline,
        is_recurring: false,
        recurrence_type: null,
        color: goalColor,
      },
      draft.milestones
        .filter((milestone) => milestone.selected)
        .map((milestone) => ({
          title: milestone.title.trim(),
          scheduled_date: milestone.scheduled_date,
          color: goalColor,
        })),
    );
    onClose();
  }

  function updateGoal(field: "title" | "deadline", value: string) {
    setDraft((current) => current ? { ...current, goal: { ...current.goal, [field]: value } } : current);
  }

  function updateMilestone(clientId: string, patch: Partial<AiScheduleDraftMilestone>) {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        milestones: current.milestones.map((milestone) =>
          milestone.client_id === clientId ? { ...milestone, ...patch } : milestone,
        ),
      };
    });
  }

  function deleteMilestone(clientId: string) {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      return {
        ...current,
        milestones: current.milestones.filter((milestone) => milestone.client_id !== clientId),
      };
    });
  }

  function addMilestone() {
    setDraft((current) => {
      if (!current) {
        return current;
      }
      const nextIndex = current.milestones.length + 1;
      return {
        ...current,
        milestones: [
          ...current.milestones,
          {
            client_id: `draft-extra-${Date.now()}`,
            title: `${text.extraMilestone} ${nextIndex}`,
            scheduled_date: selectedDate,
            selected: true,
          },
        ],
      };
    });
  }

  function moveMilestone(sourceId: string, targetId: string) {
    setDraft((current) => {
      if (!current || sourceId === targetId) {
        return current;
      }
      const items = [...current.milestones];
      const sourceIndex = items.findIndex((item) => item.client_id === sourceId);
      const targetIndex = items.findIndex((item) => item.client_id === targetId);
      if (sourceIndex < 0 || targetIndex < 0) {
        return current;
      }
      const [moved] = items.splice(sourceIndex, 1);
      items.splice(targetIndex, 0, moved);
      return { ...current, milestones: items };
    });
  }

  return (
    <FloatingPanel
      title={text.title}
      onClose={onClose}
      placement="center"
      chrome="plain"
      closeLabel={text.close}
    >
      {step === "input" || step === "loading" || step === "error" ? (
        <form className="ai-input-panel" onSubmit={handleInputSubmit} noValidate>
          <p className="muted-text">{text.description}</p>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={text.defaultPrompt}
            disabled={isBusy}
            rows={7}
          />
          {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
          {errorMessage ? (
            <p className="error-text">{text.draftFailed}</p>
          ) : null}
          <div className="panel-actions">
            <button type="submit" className="primary-button panel-primary" disabled={isBusy}>
              <Bot size={16} aria-hidden="true" />
              {step === "loading" ? text.creating : text.create}
            </button>
          </div>
        </form>
      ) : null}

      {step === "draft" && draft ? (
        <div className="ai-draft-panel">
          <div className="panel-form">
            <label>
              {text.goalTitle}
              <input value={draft.goal.title} onChange={(event) => updateGoal("title", event.target.value)} disabled={isBusy} />
            </label>
            <label>
              {text.deadline}
              <input
                type="date"
                value={draft.goal.deadline}
                onChange={(event) => updateGoal("deadline", event.target.value)}
                disabled={isBusy}
              />
            </label>
          </div>
          <div className="draft-meta-row">
            <span>{draft.planning_preference.intensity}</span>
            <span>{draft.milestones.filter((milestone) => milestone.selected).length} {text.selectedCount}</span>
          </div>
          <ul className="draft-list">
            {draft.milestones.map((milestone) => (
              <li
                key={milestone.client_id}
                draggable={!isBusy}
                onDragStart={() => setDraggingId(milestone.client_id)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => {
                  if (draggingId) {
                    moveMilestone(draggingId, milestone.client_id);
                    setDraggingId(null);
                  }
                }}
              >
                <GripVertical className="drag-handle" size={16} aria-hidden="true" />
                <input
                  className="draft-checkbox"
                  type="checkbox"
                  checked={milestone.selected}
                  onChange={(event) => updateMilestone(milestone.client_id, { selected: event.target.checked })}
                  disabled={isBusy}
                  aria-label={`${text.select} ${milestone.title}`}
                />
                <input
                  className="draft-title-input"
                  value={milestone.title}
                  onChange={(event) => updateMilestone(milestone.client_id, { title: event.target.value })}
                  disabled={isBusy}
                  aria-label={text.milestoneTitle}
                />
                <input
                  className="draft-date-input"
                  type="date"
                  value={milestone.scheduled_date}
                  onChange={(event) => updateMilestone(milestone.client_id, { scheduled_date: event.target.value })}
                  disabled={isBusy}
                  aria-label={text.milestoneDate}
                />
                <button
                  type="button"
                  className="icon-button compact-icon danger-icon"
                  onClick={() => deleteMilestone(milestone.client_id)}
                  disabled={isBusy}
                  title={text.delete}
                >
                  <Trash2 size={15} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="secondary-toggle draft-add-button" onClick={addMilestone} disabled={isBusy}>
            <Plus size={15} aria-hidden="true" />
            {text.addMilestone}
          </button>
          {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
          {errorMessage ? <p className="error-text">{text.retryFailed}</p> : null}
          <div className="panel-actions ai-draft-actions">
            <button type="button" className="ghost-button panel-button" onClick={() => void requestDraft()} disabled={isBusy}>
              <RefreshCw size={15} aria-hidden="true" />
              {text.retry}
            </button>
            <button type="button" className="ghost-button panel-button" onClick={onClose} disabled={isBusy}>
              {text.cancel}
            </button>
            <button type="button" className="primary-button panel-primary" onClick={() => void handleSaveDraft()} disabled={isBusy}>
              <ListPlus size={16} aria-hidden="true" />
              {isSaving ? text.adding : text.addToSchedule}
            </button>
          </div>
        </div>
      ) : null}
    </FloatingPanel>
  );
}

function validateEditableDraft(
  draft: AiScheduleDraft,
  text: (typeof labels)[Language]["validation"],
): string | null {
  if (!draft.goal.title.trim()) {
    return text.goalTitleRequired;
  }
  if (!isDateString(draft.goal.deadline)) {
    return text.deadlineRequired;
  }
  const selected = draft.milestones.filter((milestone) => milestone.selected);
  if (selected.length === 0) {
    return text.selectedRequired;
  }
  for (const milestone of selected) {
    if (!milestone.title.trim()) {
      return text.emptyMilestoneTitle;
    }
    if (!isDateString(milestone.scheduled_date)) {
      return text.milestoneDateRequired;
    }
    if (milestone.scheduled_date > draft.goal.deadline) {
      return text.milestoneAfterDeadline;
    }
  }
  return null;
}

function isDateString(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}
