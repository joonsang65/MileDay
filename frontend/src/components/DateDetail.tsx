import { FormEvent, useState } from "react";
import { CheckCircle2, Circle, Pencil, Trash2, X } from "lucide-react";

import type { CalendarDateData, Goal, GoalUpdatePayload, Milestone, MilestoneUpdatePayload } from "@/api/types";

type DateDetailProps = {
  detail?: CalendarDateData | null;
  isLoading: boolean;
  onToggleMilestone: (milestoneId: string, isCompleted: boolean) => void;
  onUpdateGoal: (goalId: string, payload: GoalUpdatePayload) => Promise<void>;
  onDeleteGoal: (goalId: string) => Promise<void>;
  onUpdateMilestone: (milestoneId: string, payload: MilestoneUpdatePayload) => Promise<void>;
  onDeleteMilestone: (milestoneId: string) => Promise<void>;
};

type EditingItem =
  | { type: "goal"; id: string }
  | { type: "milestone"; id: string }
  | null;

type DateGoalGroup = {
  id: string;
  title: string;
  color: string;
  goal?: Goal;
  milestones: Milestone[];
  completed: number;
};

function getDateGoalGroups(detail?: CalendarDateData | null): DateGoalGroup[] {
  if (!detail) {
    return [];
  }

  const groups = new Map<string, DateGoalGroup>();
  for (const goal of detail.goals) {
    groups.set(goal.id, {
      id: goal.id,
      title: goal.title,
      color: goal.color,
      goal,
      milestones: [],
      completed: 0,
    });
  }

  for (const milestone of detail.milestones) {
    const group = groups.get(milestone.goal_id) ?? {
      id: milestone.goal_id,
      title: milestone.goal_title ?? "목표 없음",
      color: milestone.color,
      milestones: [],
      completed: 0,
    };
    group.milestones.push(milestone);
    if (milestone.is_completed) {
      group.completed += 1;
    }
    groups.set(milestone.goal_id, group);
  }

  return Array.from(groups.values());
}

export function DateDetail({
  detail,
  isLoading,
  onToggleMilestone,
  onUpdateGoal,
  onDeleteGoal,
  onUpdateMilestone,
  onDeleteMilestone,
}: DateDetailProps) {
  const [editingItem, setEditingItem] = useState<EditingItem>(null);
  const goalGroups = getDateGoalGroups(detail);

  function toggleEditing(item: EditingItem) {
    setEditingItem((current) => (
      current?.type === item?.type && current?.id === item?.id ? null : item
    ));
  }

  return (
    <section className="detail-panel" aria-label="날짜 상세">
      <div className="panel-heading">
        <h2>날짜 상세</h2>
        <span>{detail?.date ?? "-"}</span>
      </div>
      {isLoading ? <p className="muted-text">불러오는 중입니다.</p> : null}
      {detail ? (
        <>
          <div className="summary-row">
            <span>목표 {goalGroups.length}</span>
            <span>
              작업 {detail.completed_milestone_count}/{detail.milestone_count}
            </span>
          </div>
          <div className="section-block">
            <h3>목표</h3>
            {goalGroups.length === 0 ? (
              <p className="empty-text">연결된 목표가 없습니다.</p>
            ) : (
              <ul className="plain-list">
                {goalGroups.map((group) => (
                  <li key={group.id} className="goal-group">
                    {group.goal ? (
                      <button
                        type="button"
                        className="editable-row goal-row"
                        onClick={() => toggleEditing({ type: "goal", id: group.id })}
                      >
                        <span className="color-swatch" style={{ background: group.color }} />
                        <span>
                          <strong>{group.title}</strong>
                          <small>작업 {group.completed}/{group.milestones.length}</small>
                        </span>
                        <Pencil size={14} aria-hidden="true" />
                      </button>
                    ) : (
                      <div className="editable-row goal-row readonly-row">
                        <span className="color-swatch" style={{ background: group.color }} />
                        <span>
                          <strong>{group.title}</strong>
                          <small>작업 {group.completed}/{group.milestones.length}</small>
                        </span>
                        <span aria-hidden="true" />
                      </div>
                    )}
                    {group.goal && editingItem?.type === "goal" && editingItem.id === group.id ? (
                      <GoalEditor
                        goal={group.goal}
                        isLoading={isLoading}
                        onCancel={() => setEditingItem(null)}
                        onSave={async (payload) => {
                          await onUpdateGoal(group.id, payload);
                          setEditingItem(null);
                        }}
                        onDelete={async () => {
                          await onDeleteGoal(group.id);
                          setEditingItem(null);
                        }}
                      />
                    ) : null}
                    {group.milestones.length > 0 ? (
                      <ul className="nested-task-list">
                        {group.milestones.map((milestone) => (
                          <li key={milestone.id} className="editable-item">
                            <div className="milestone-row">
                              <button
                                type="button"
                                className="check-button"
                                onClick={() => onToggleMilestone(milestone.id, !milestone.is_completed)}
                                title={milestone.is_completed ? "미완료로 변경" : "완료로 변경"}
                                disabled={isLoading}
                              >
                                {milestone.is_completed ? (
                                  <CheckCircle2 size={18} aria-hidden="true" />
                                ) : (
                                  <Circle size={18} aria-hidden="true" />
                                )}
                              </button>
                              <button
                                type="button"
                                className="editable-row milestone-main"
                                onClick={() => toggleEditing({ type: "milestone", id: milestone.id })}
                              >
                                <span className="color-swatch" style={{ background: milestone.color }} />
                                <span>
                                  <strong>{milestone.title}</strong>
                                  <small>마일스톤</small>
                                </span>
                                <Pencil size={14} aria-hidden="true" />
                              </button>
                            </div>
                            {editingItem?.type === "milestone" && editingItem.id === milestone.id ? (
                              <MilestoneEditor
                                milestone={milestone}
                                isLoading={isLoading}
                                onCancel={() => setEditingItem(null)}
                                onSave={async (payload) => {
                                  await onUpdateMilestone(milestone.id, payload);
                                  setEditingItem(null);
                                }}
                                onDelete={async () => {
                                  await onDeleteMilestone(milestone.id);
                                  setEditingItem(null);
                                }}
                              />
                            ) : null}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </>
      ) : null}
    </section>
  );
}

function GoalEditor({
  goal,
  isLoading,
  onCancel,
  onSave,
  onDelete,
}: {
  goal: Goal;
  isLoading: boolean;
  onCancel: () => void;
  onSave: (payload: GoalUpdatePayload) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [title, setTitle] = useState(goal.title);
  const [deadline, setDeadline] = useState(goal.deadline);
  const [color, setColor] = useState(goal.color);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

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
    await onSave({
      title: title.trim(),
      deadline,
      color,
      is_recurring: false,
      recurrence_type: null,
    });
  }

  return (
    <form className="inline-editor" onSubmit={handleSubmit} noValidate>
      <label>
        제목
        <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={isLoading} required />
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
      <label>
        색상
        <input value={color} onChange={(event) => setColor(event.target.value)} disabled={isLoading} required />
      </label>
      {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      <EditorActions isLoading={isLoading} onCancel={onCancel} onDelete={onDelete} />
    </form>
  );
}

function MilestoneEditor({
  milestone,
  isLoading,
  onCancel,
  onSave,
  onDelete,
}: {
  milestone: Milestone;
  isLoading: boolean;
  onCancel: () => void;
  onSave: (payload: MilestoneUpdatePayload) => Promise<void>;
  onDelete: () => Promise<void>;
}) {
  const [title, setTitle] = useState(milestone.title);
  const [scheduledDate, setScheduledDate] = useState(milestone.scheduled_date);
  const [color, setColor] = useState(milestone.color);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);
    if (!title.trim()) {
      setValidationMessage("마일스톤 제목을 입력해 주세요.");
      return;
    }
    if (!scheduledDate) {
      setValidationMessage("예정일을 선택해 주세요.");
      return;
    }
    await onSave({
      title: title.trim(),
      scheduled_date: scheduledDate,
      color,
    });
  }

  return (
    <form className="inline-editor" onSubmit={handleSubmit} noValidate>
      <label>
        제목
        <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={isLoading} required />
      </label>
      <label>
        예정일
        <input
          type="date"
          value={scheduledDate}
          onChange={(event) => setScheduledDate(event.target.value)}
          disabled={isLoading}
          required
        />
      </label>
      <label>
        색상
        <input value={color} onChange={(event) => setColor(event.target.value)} disabled={isLoading} required />
      </label>
      {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      <EditorActions isLoading={isLoading} onCancel={onCancel} onDelete={onDelete} />
    </form>
  );
}

function EditorActions({
  isLoading,
  onCancel,
  onDelete,
}: {
  isLoading: boolean;
  onCancel: () => void;
  onDelete: () => Promise<void>;
}) {
  return (
    <div className="editor-actions">
      <button type="submit" className="primary-button compact" disabled={isLoading}>
        {isLoading ? "저장 중" : "저장"}
      </button>
      <button type="button" className="ghost-button compact" onClick={onCancel} disabled={isLoading}>
        <X size={14} aria-hidden="true" />
        닫기
      </button>
      <button type="button" className="danger-button compact" onClick={() => void onDelete()} disabled={isLoading}>
        <Trash2 size={14} aria-hidden="true" />
        {isLoading ? "삭제 중" : "삭제"}
      </button>
    </div>
  );
}
