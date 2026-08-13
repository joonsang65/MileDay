import { FormEvent, useState } from "react";
import { Bot, GripVertical, ListPlus, Plus, RefreshCw, Trash2 } from "lucide-react";

import type {
  AiScheduleDraft,
  AiScheduleDraftMilestone,
  AiScheduleDraftRequest,
  GoalCreatePayload,
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
};

const defaultPrompt =
  "9월 말까지 데이터 분석 과제를 끝내고 싶어. 가능한 날짜 안에서 너무 빡빡하지 않게 초안을 잡아줘.";
const defaultMilestoneColor = "#55A873";

export function AiSchedulePanel({
  selectedDate,
  today,
  timezone,
  availability,
  isSaving,
  onCreateDraft,
  onSaveDraft,
  onClose,
}: AiSchedulePanelProps) {
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
      setValidationMessage("목표를 자연어로 입력해 주세요.");
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
      setErrorMessage(error instanceof Error ? error.message : "일정 제안에 실패했습니다.");
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
    const validation = validateEditableDraft(draft);
    if (validation) {
      setValidationMessage(validation);
      return;
    }
    await onSaveDraft(
      {
        title: draft.goal.title.trim(),
        deadline: draft.goal.deadline,
        is_recurring: false,
        recurrence_type: null,
        color: draft.create_goal_payload.goal.color,
      },
      draft.milestones
        .filter((milestone) => milestone.selected)
        .map((milestone) => ({
          title: milestone.title.trim(),
          scheduled_date: milestone.scheduled_date,
          color: defaultMilestoneColor,
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
            title: `추가 작업 ${nextIndex}`,
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
      title="일정 추천"
      onClose={onClose}
      footer={
        step === "draft" && draft ? (
          <>
            <button type="button" className="ghost-button panel-button" onClick={() => void requestDraft()} disabled={isBusy}>
              <RefreshCw size={15} aria-hidden="true" />
              다시 제안
            </button>
            <button type="button" className="ghost-button panel-button" onClick={onClose} disabled={isBusy}>
              취소
            </button>
            <button type="button" className="primary-button panel-primary" onClick={() => void handleSaveDraft()} disabled={isBusy}>
              <ListPlus size={16} aria-hidden="true" />
              {isSaving ? "추가 중" : "일정에 추가"}
            </button>
          </>
        ) : null
      }
    >
      {step === "input" || step === "loading" || step === "error" ? (
        <form className="ai-input-panel" onSubmit={handleInputSubmit} noValidate>
          <p className="muted-text">목표를 바탕으로 일정 초안을 준비해 드립니다.</p>
          <textarea
            value={prompt}
            onChange={(event) => setPrompt(event.target.value)}
            placeholder={defaultPrompt}
            disabled={isBusy}
            rows={7}
          />
          {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
          {errorMessage ? (
            <p className="error-text">일정 제안에 실패했습니다. 입력한 내용은 그대로 유지됩니다.</p>
          ) : null}
          <button type="submit" className="primary-button panel-primary" disabled={isBusy}>
            <Bot size={16} aria-hidden="true" />
            {step === "loading" ? "제안 만드는 중" : "제안 만들기"}
          </button>
        </form>
      ) : null}

      {step === "draft" && draft ? (
        <div className="ai-draft-panel">
          <div className="panel-form">
            <label>
              목표 제목
              <input value={draft.goal.title} onChange={(event) => updateGoal("title", event.target.value)} disabled={isBusy} />
            </label>
            <label>
              마감일
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
            <span>{draft.milestones.filter((milestone) => milestone.selected).length}개 선택</span>
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
                  aria-label={`${milestone.title} 선택`}
                />
                <input
                  className="draft-title-input"
                  value={milestone.title}
                  onChange={(event) => updateMilestone(milestone.client_id, { title: event.target.value })}
                  disabled={isBusy}
                  aria-label="마일스톤 제목"
                />
                <input
                  className="draft-date-input"
                  type="date"
                  value={milestone.scheduled_date}
                  onChange={(event) => updateMilestone(milestone.client_id, { scheduled_date: event.target.value })}
                  disabled={isBusy}
                  aria-label="마일스톤 날짜"
                />
                <button
                  type="button"
                  className="icon-button compact-icon danger-icon"
                  onClick={() => deleteMilestone(milestone.client_id)}
                  disabled={isBusy}
                  title="삭제"
                >
                  <Trash2 size={15} aria-hidden="true" />
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="secondary-toggle draft-add-button" onClick={addMilestone} disabled={isBusy}>
            <Plus size={15} aria-hidden="true" />
            마일스톤 추가
          </button>
          {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
          {errorMessage ? <p className="error-text">다시 제안에 실패했습니다. 기존 초안은 유지됩니다.</p> : null}
        </div>
      ) : null}
    </FloatingPanel>
  );
}

function validateEditableDraft(draft: AiScheduleDraft): string | null {
  if (!draft.goal.title.trim()) {
    return "목표 제목을 입력해 주세요.";
  }
  if (!isDateString(draft.goal.deadline)) {
    return "마감일을 선택해 주세요.";
  }
  const selected = draft.milestones.filter((milestone) => milestone.selected);
  if (selected.length === 0) {
    return "선택한 마일스톤이 최소 1개 필요합니다.";
  }
  for (const milestone of selected) {
    if (!milestone.title.trim()) {
      return "비어 있는 마일스톤 제목이 있습니다.";
    }
    if (!isDateString(milestone.scheduled_date)) {
      return "마일스톤 날짜를 모두 선택해 주세요.";
    }
    if (milestone.scheduled_date > draft.goal.deadline) {
      return "마일스톤 날짜는 마감일을 넘을 수 없습니다.";
    }
  }
  return null;
}

function isDateString(value: string) {
  return /^\d{4}-\d{2}-\d{2}$/.test(value);
}
