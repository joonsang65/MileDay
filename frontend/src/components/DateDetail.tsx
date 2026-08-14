import { FormEvent, useState } from "react";
import { CheckCircle2, Circle, Pencil, Trash2, X } from "lucide-react";

import type { CalendarDateData, Goal, GoalUpdatePayload, Language, Milestone, MilestoneUpdatePayload } from "@/api/types";

type DateDetailProps = {
  detail?: CalendarDateData | null;
  isLoading: boolean;
  onToggleMilestone: (milestoneId: string, isCompleted: boolean) => void;
  onUpdateGoal: (goalId: string, payload: GoalUpdatePayload) => Promise<void>;
  onDeleteGoal: (goalId: string) => Promise<void>;
  onUpdateMilestone: (milestoneId: string, payload: MilestoneUpdatePayload) => Promise<void>;
  onDeleteMilestone: (milestoneId: string) => Promise<void>;
  language?: Language;
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

const dateDetailLabels = {
  ko: {
    title: "하루 보기",
    loading: "불러오는 중입니다.",
    goals: "목표",
    task: "작업",
    empty: "연결된 일정이 없습니다.",
    noGoal: "목표 없음",
    milestone: "마일스톤",
    markIncomplete: "미완료로 변경",
    markComplete: "완료로 변경",
    formTitle: "제목",
    deadline: "마감일",
    scheduledDate: "일정일",
    color: "색상",
    goalTitleRequired: "목표 제목을 입력해 주세요.",
    milestoneTitleRequired: "마일스톤 제목을 입력해 주세요.",
    deadlineRequired: "마감일을 선택해 주세요.",
    scheduledDateRequired: "일정일을 선택해 주세요.",
    saving: "저장 중",
    save: "저장",
    close: "닫기",
    deleting: "삭제 중",
    delete: "삭제",
  },
  en: {
    title: "Day View",
    loading: "Loading.",
    goals: "Goals",
    task: "Tasks",
    empty: "No schedules are linked.",
    noGoal: "No goal",
    milestone: "Milestone",
    markIncomplete: "Mark incomplete",
    markComplete: "Mark complete",
    formTitle: "Title",
    deadline: "Deadline",
    scheduledDate: "Schedule date",
    color: "Color",
    goalTitleRequired: "Please enter a goal title.",
    milestoneTitleRequired: "Please enter a milestone title.",
    deadlineRequired: "Please select a deadline.",
    scheduledDateRequired: "Please select a schedule date.",
    saving: "Saving",
    save: "Save",
    close: "Close",
    deleting: "Deleting",
    delete: "Delete",
  },
};

function getDateGoalGroups(detail: CalendarDateData | null | undefined, noGoalLabel: string): DateGoalGroup[] {
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
      title: milestone.goal_title ?? noGoalLabel,
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
  language = "ko",
}: DateDetailProps) {
  const [editingItem, setEditingItem] = useState<EditingItem>(null);
  const text = dateDetailLabels[language];
  const goalGroups = getDateGoalGroups(detail, text.noGoal);

  function toggleEditing(item: EditingItem) {
    setEditingItem((current) => (
      current?.type === item?.type && current?.id === item?.id ? null : item
    ));
  }

  return (
    <section className="detail-panel day-view-panel" data-testid="date-detail-panel" aria-label={text.title}>
      <div className="panel-heading day-view-heading">
        <div>
          <h2>{text.title}</h2>
          <span>{detail?.date ?? "-"}</span>
        </div>
      </div>
      {isLoading ? <p className="muted-text">{text.loading}</p> : null}
      {detail ? (
        <>
          <div className="summary-row">
            <span>{text.goals} {goalGroups.length}</span>
            <span>
              {text.task} {detail.completed_milestone_count}/{detail.milestone_count}
            </span>
          </div>
          <div className="section-block">
            <h3>{text.goals}</h3>
            {goalGroups.length === 0 ? (
              <p className="empty-text">{text.empty}</p>
            ) : (
              <ul className="plain-list day-view-list">
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
                          <small>{text.task} {group.completed}/{group.milestones.length}</small>
                        </span>
                        <Pencil size={14} aria-hidden="true" />
                      </button>
                    ) : (
                      <div className="editable-row goal-row readonly-row">
                        <span className="color-swatch" style={{ background: group.color }} />
                        <span>
                          <strong>{group.title}</strong>
                          <small>{text.task} {group.completed}/{group.milestones.length}</small>
                        </span>
                        <span aria-hidden="true" />
                      </div>
                    )}
                    {group.goal && editingItem?.type === "goal" && editingItem.id === group.id ? (
                      <GoalEditor
                        goal={group.goal}
                        isLoading={isLoading}
                        text={text}
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
                                data-testid="milestone-toggle"
                                data-milestone-id={milestone.id}
                                aria-pressed={milestone.is_completed}
                                onClick={() => onToggleMilestone(milestone.id, !milestone.is_completed)}
                                title={milestone.is_completed ? text.markIncomplete : text.markComplete}
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
                                  <small>{text.milestone}</small>
                                </span>
                                <Pencil size={14} aria-hidden="true" />
                              </button>
                            </div>
                            {editingItem?.type === "milestone" && editingItem.id === milestone.id ? (
                              <MilestoneEditor
                                milestone={milestone}
                                isLoading={isLoading}
                                text={text}
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
  text,
  onCancel,
  onSave,
  onDelete,
}: {
  goal: Goal;
  isLoading: boolean;
  text: (typeof dateDetailLabels)[Language];
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
      setValidationMessage(text.goalTitleRequired);
      return;
    }
    if (!deadline) {
      setValidationMessage(text.deadlineRequired);
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
        {text.formTitle}
        <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={isLoading} required />
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
      <label>
        {text.color}
        <input value={color} onChange={(event) => setColor(event.target.value)} disabled={isLoading} required />
      </label>
      {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      <EditorActions isLoading={isLoading} text={text} onCancel={onCancel} onDelete={onDelete} />
    </form>
  );
}

function MilestoneEditor({
  milestone,
  isLoading,
  text,
  onCancel,
  onSave,
  onDelete,
}: {
  milestone: Milestone;
  isLoading: boolean;
  text: (typeof dateDetailLabels)[Language];
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
      setValidationMessage(text.milestoneTitleRequired);
      return;
    }
    if (!scheduledDate) {
      setValidationMessage(text.scheduledDateRequired);
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
        {text.formTitle}
        <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={isLoading} required />
      </label>
      <label>
        {text.scheduledDate}
        <input
          type="date"
          value={scheduledDate}
          onChange={(event) => setScheduledDate(event.target.value)}
          disabled={isLoading}
          required
        />
      </label>
      <label>
        {text.color}
        <input value={color} onChange={(event) => setColor(event.target.value)} disabled={isLoading} required />
      </label>
      {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      <EditorActions isLoading={isLoading} text={text} onCancel={onCancel} onDelete={onDelete} />
    </form>
  );
}

function EditorActions({
  isLoading,
  text,
  onCancel,
  onDelete,
}: {
  isLoading: boolean;
  text: (typeof dateDetailLabels)[Language];
  onCancel: () => void;
  onDelete: () => Promise<void>;
}) {
  return (
    <div className="editor-actions">
      <button type="submit" className="primary-button compact" disabled={isLoading}>
        {isLoading ? text.saving : text.save}
      </button>
      <button type="button" className="ghost-button compact" onClick={onCancel} disabled={isLoading}>
        <X size={14} aria-hidden="true" />
        {text.close}
      </button>
      <button type="button" className="danger-button compact" onClick={() => void onDelete()} disabled={isLoading}>
        <Trash2 size={14} aria-hidden="true" />
        {isLoading ? text.deleting : text.delete}
      </button>
    </div>
  );
}
