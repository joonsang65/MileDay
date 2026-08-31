import { CSSProperties, FormEvent, ReactNode, useEffect, useState } from "react";
import { CheckSquare, Pencil, Plus, Square, Trash2, X } from "lucide-react";

import type {
  CalendarDateData,
  Goal,
  GoalUpdatePayload,
  Language,
  Milestone,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
} from "@/api/types";

type DateDetailProps = {
  detail?: CalendarDateData | null;
  goals?: Goal[];
  isLoading: boolean;
  onToggleGoal: (goalId: string, isCompleted: boolean) => void | Promise<void>;
  onToggleMilestone: (milestoneId: string, isCompleted: boolean) => void | Promise<void>;
  onUpdateGoal: (goalId: string, payload: GoalUpdatePayload) => Promise<void>;
  onDeleteGoal: (goalId: string) => Promise<void>;
  onCreateMilestone: (goalId: string, payload: MilestoneCreatePayload) => Promise<void>;
  onUpdateMilestone: (milestoneId: string, payload: MilestoneUpdatePayload) => Promise<void>;
  onDeleteMilestone: (milestoneId: string) => Promise<void>;
  onEditingChange?: (isEditing: boolean) => void;
  onOpenQuickMenu?: () => void;
  quickMenuContent?: ReactNode;
  language?: Language;
  hideHeader?: boolean;
};

type EditingItem =
  | { type: "goal"; id: string }
  | { type: "new-milestone"; goalId: string }
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

const colorOptions = ["#7F9278", "#55A873", "#E59A45", "#8B6FD6", "#D96868", "#8A94A3"];

export const dateDetailLabels = {
  ko: {
    title: "하루 보기",
    loading: "불러오는 중입니다.",
    goals: "목표",
    task: "작업",
    empty: "오늘은 일정이 없습니다.",
    noGoal: "목표 없음",
    milestone: "마일스톤",
    markIncomplete: "미완료로 변경",
    markComplete: "완료로 변경",
    formTitle: "제목",
    goalTitleLabel: "목표 제목",
    milestoneTitleLabel: "마일스톤 제목",
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
    goalTitleLabel: "Goal title",
    milestoneTitleLabel: "Milestone title",
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

function getDateGoalGroups(
  detail: CalendarDateData | null | undefined,
  noGoalLabel: string,
  allGoals?: Goal[],
): DateGoalGroup[] {
  if (!detail) {
    return [];
  }

  const goalMap = new Map<string, Goal>();
  if (allGoals) {
    for (const goal of allGoals) {
      goalMap.set(goal.id, goal);
    }
  }
  for (const goal of detail.goals) {
    goalMap.set(goal.id, goal);
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
    const matchedGoal = goalMap.get(milestone.goal_id);
    const fallbackGoal: Goal | undefined = milestone.goal_id
      ? {
          id: milestone.goal_id,
          title: milestone.goal_title ?? noGoalLabel,
          deadline: detail.date,
          is_completed: false,
          color: milestone.color,
          is_recurring: false,
          recurrence_type: null,
          created_at: "",
          updated_at: "",
        }
      : undefined;

    const resolvedGoal = matchedGoal ?? fallbackGoal;
    const group = groups.get(milestone.goal_id) ?? {
      id: milestone.goal_id,
      title: resolvedGoal?.title ?? milestone.goal_title ?? noGoalLabel,
      color: resolvedGoal?.color ?? milestone.color,
      goal: resolvedGoal,
      milestones: [],
      completed: 0,
    };
    if (!group.goal && resolvedGoal) {
      group.goal = resolvedGoal;
      group.title = resolvedGoal.title;
      group.color = resolvedGoal.color;
    }
    group.milestones.push(milestone);
    if (milestone.is_completed) {
      group.completed += 1;
    }
    groups.set(milestone.goal_id, group);
  }

  return Array.from(groups.values());
}

function isSameEditingItem(current: EditingItem, next: EditingItem): boolean {
  if (!current || !next || current.type !== next.type) {
    return false;
  }
  if (current.type === "new-milestone" && next.type === "new-milestone") {
    return current.goalId === next.goalId;
  }
  if (current.type !== "new-milestone" && next.type !== "new-milestone") {
    return current.id === next.id;
  }
  return false;
}

export function DateDetail({
  detail,
  goals,
  isLoading,
  onToggleGoal,
  onToggleMilestone,
  onUpdateGoal,
  onDeleteGoal,
  onCreateMilestone,
  onUpdateMilestone,
  onDeleteMilestone,
  onEditingChange,
  onOpenQuickMenu,
  quickMenuContent,
  language = "ko",
  hideHeader = false,
}: DateDetailProps) {
  const [editingItem, setEditingItem] = useState<EditingItem>(null);
  const text = dateDetailLabels[language];
  const addLabel = language === "en" ? "Add schedule" : "일정 만들기";
  const goalGroups = getDateGoalGroups(detail, text.noGoal, goals);

  useEffect(() => {
    onEditingChange?.(editingItem !== null);
    return () => {
      onEditingChange?.(false);
    };
  }, [editingItem, onEditingChange]);

  function toggleEditing(item: EditingItem) {
    setEditingItem((current) => (
      isSameEditingItem(current, item) ? null : item
    ));
  }

  const quickAddControl = onOpenQuickMenu ? (
    <div className="day-view-add-control">
      <button
        type="button"
        className="add-button day-view-add-button"
        data-testid="quick-add-button"
        onClick={onOpenQuickMenu}
        title={addLabel}
      >
        <Plus size={19} aria-hidden="true" />
      </button>
      {quickMenuContent ? <div className="day-view-quick-menu">{quickMenuContent}</div> : null}
    </div>
  ) : null;

  return (
    <section className="detail-panel day-view-panel" data-testid="date-detail-panel" aria-label={text.title}>
      {hideHeader ? (
        <div className="day-view-toolbar">
          <h3 className="day-view-section-title">{text.goals}</h3>
          <div className="day-view-heading-meta">
            {detail ? (
              <span className="day-view-summary">
                <span>{text.goals} {goalGroups.length}</span>
                <span className="summary-divider" aria-hidden="true" />
                <span>{text.task} {detail.completed_milestone_count}/{detail.milestone_count}</span>
              </span>
            ) : null}
          </div>
          {quickAddControl}
        </div>
      ) : (
        <div className="panel-heading day-view-heading">
          <h2 className="day-view-title">
            {text.title}
            <span className="day-view-date">{detail?.date ?? "-"}</span>
          </h2>
          <div className="day-view-heading-meta">
            {detail ? (
              <span className="day-view-summary">
                <span>{text.goals} {goalGroups.length}</span>
                <span className="summary-divider" aria-hidden="true" />
                <span>{text.task} {detail.completed_milestone_count}/{detail.milestone_count}</span>
              </span>
            ) : null}
          </div>
          {quickAddControl}
        </div>
      )}
      {isLoading ? <p className="muted-text">{text.loading}</p> : null}
      {detail ? (
        <div className="section-block">
          {hideHeader ? null : <h3 className="day-view-section-title">{text.goals}</h3>}
          {goalGroups.length === 0 ? (
            <p className="empty-text day-view-empty-text">{text.empty}</p>
          ) : (
            <ul className="plain-list day-view-list">
              {goalGroups.map((group) => (
                <li key={group.id} className="goal-group">
                  {group.goal ? (
                    <div className={`editable-row goal-row split-goal-row ${group.milestones.length === 0 ? "single-goal-row" : ""}`}>
                      {group.milestones.length === 0 ? (
                        <button
                          type="button"
                          className="check-button goal-check-button"
                          data-testid="goal-toggle"
                          data-goal-id={group.id}
                          aria-pressed={group.goal.is_completed}
                          onClick={() => {
                            void Promise.resolve(onToggleGoal(group.id, !group.goal!.is_completed)).catch(() => undefined);
                          }}
                          title={group.goal.is_completed ? text.markIncomplete : text.markComplete}
                          disabled={isLoading}
                        >
                          {group.goal.is_completed ? (
                            <CheckSquare size={18} aria-hidden="true" />
                          ) : (
                            <Square size={18} aria-hidden="true" />
                          )}
                        </button>
                      ) : null}
                      <button
                        type="button"
                        className="goal-edit-target"
                        onClick={() => toggleEditing({ type: "goal", id: group.id })}
                      >
                        <span className="goal-color-bar" style={{ background: group.color }} />
                        <span className="day-view-row-content">
                          <strong style={{
                            opacity: group.goal.is_completed ? 0.6 : 1,
                            textDecoration: group.goal.is_completed ? "line-through" : "none",
                          }}>
                            {group.title}
                          </strong>
                          <small>{text.task} {group.completed}/{group.milestones.length}</small>
                        </span>
                      </button>
                      <div className="goal-row-actions">
                        <button
                          type="button"
                          className="row-icon-button"
                          onClick={() => toggleEditing({ type: "goal", id: group.id })}
                          title={language === "en" ? "Edit goal" : "목표 수정"}
                          aria-label={language === "en" ? "Edit goal" : "목표 수정"}
                        >
                          <Pencil size={14} aria-hidden="true" />
                        </button>
                      </div>
                    </div>
                  ) : (
                    <div className="editable-row goal-row readonly-row">
                      <span className="goal-color-bar" style={{ background: group.color }} />
                      <span className="day-view-row-content">
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
                  {group.goal && editingItem?.type === "new-milestone" && editingItem.goalId === group.id ? (
                    <MilestoneCreateEditor
                      goal={group.goal}
                      scheduledDate={detail.date}
                      heading={language === "en" ? "Add milestone" : "마일스톤 추가"}
                      isLoading={isLoading}
                      text={text}
                      onCancel={() => setEditingItem(null)}
                      onSave={async (payload) => {
                        await onCreateMilestone(group.id, payload);
                        setEditingItem(null);
                      }}
                      onUpdateGoal={async (payload) => {
                        await onUpdateGoal(group.id, payload);
                      }}
                    />
                  ) : null}
                  {group.milestones.length > 0 ? (
                    <ul className="nested-task-list">
                      {group.milestones.map((milestone) => (
                        <li key={milestone.id} className="editable-item">
                          <div className="milestone-row">
                            <div className="editable-row split-goal-row milestone-card-row">
                              <button
                                type="button"
                                className="check-button"
                                data-testid="milestone-toggle"
                                data-milestone-id={milestone.id}
                                aria-pressed={milestone.is_completed}
                                onClick={() => {
                                  void Promise.resolve(onToggleMilestone(milestone.id, !milestone.is_completed)).catch(() => undefined);
                                }}
                                title={milestone.is_completed ? text.markIncomplete : text.markComplete}
                                disabled={isLoading}
                              >
                              {milestone.is_completed ? (
                                <CheckSquare size={18} aria-hidden="true" />
                              ) : (
                                <Square size={18} aria-hidden="true" />
                              )}
                              </button>
                              <button
                                type="button"
                                className="goal-edit-target"
                                onClick={() => toggleEditing({ type: "milestone", id: milestone.id })}
                              >
                                <span className="day-view-row-content">
                                  <strong>{milestone.title}</strong>
                                  <small>{text.milestone}</small>
                                </span>
                              </button>
                              <button
                                type="button"
                                className="row-icon-button"
                                onClick={() => toggleEditing({ type: "milestone", id: milestone.id })}
                              >
                                <Pencil size={14} aria-hidden="true" />
                              </button>
                            </div>
                          </div>
                          {editingItem?.type === "milestone" && editingItem.id === milestone.id ? (
                            <MilestoneEditor
                              goal={group.goal}
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
                              onUpdateGoal={async (payload) => {
                                await onUpdateGoal(group.id, payload);
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
      ) : null}
    </section>
  );
}

export function GoalEditor({
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
      <div className="inline-goal-editor-layout">
        <div className="inline-editor-fields">
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
        </div>
        <label className="inline-goal-color-field">
          {text.color}
          <ColorPicker value={color} disabled={isLoading} label={text.color} onChange={setColor} />
        </label>
      </div>
      {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      <EditorActions isLoading={isLoading} text={text} onCancel={onCancel} onDelete={onDelete} />
    </form>
  );
}

export function MilestoneEditor({
  milestone,
  isLoading,
  text,
  onCancel,
  onSave,
  onDelete,
}: {
  goal?: Goal;
  milestone: Milestone;
  isLoading: boolean;
  text: (typeof dateDetailLabels)[Language];
  onCancel: () => void;
  onSave: (payload: MilestoneUpdatePayload) => Promise<void>;
  onDelete: () => Promise<void>;
  onUpdateGoal?: (payload: GoalUpdatePayload) => Promise<void>;
}) {
  const [title, setTitle] = useState(milestone.title);
  const [scheduledDate, setScheduledDate] = useState(milestone.scheduled_date);
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
    });
  }

  return (
    <form className="inline-editor" onSubmit={handleSubmit} noValidate>
      <label>
        {text.milestoneTitleLabel || text.formTitle}
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

      {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      <EditorActions isLoading={isLoading} text={text} onCancel={onCancel} onDelete={onDelete} />
    </form>
  );
}

export function MilestoneCreateEditor({
  goal,
  scheduledDate,
  heading,
  isLoading,
  text,
  onCancel,
  onSave,
  onUpdateGoal,
}: {
  goal: Goal;
  scheduledDate: string;
  heading: string;
  isLoading: boolean;
  text: (typeof dateDetailLabels)[Language];
  onCancel: () => void;
  onSave: (payload: MilestoneCreatePayload) => Promise<void>;
  onUpdateGoal: (payload: GoalUpdatePayload) => Promise<void>;
}) {
  const [goalTitle, setGoalTitle] = useState(goal.title);
  const [title, setTitle] = useState("");
  const [date, setDate] = useState(scheduledDate);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);
    if (!goalTitle.trim()) {
      setValidationMessage(text.goalTitleRequired);
      return;
    }
    if (!title.trim()) {
      setValidationMessage(text.milestoneTitleRequired);
      return;
    }
    if (!date) {
      setValidationMessage(text.scheduledDateRequired);
      return;
    }
    
    if (goalTitle.trim() !== goal.title) {
      await onUpdateGoal({ title: goalTitle.trim() });
    }
    
    await onSave({
      title: title.trim(),
      scheduled_date: date,
      color: goal.color,
    });
  }

  return (
    <form className="inline-editor" onSubmit={handleSubmit} noValidate>
      <strong className="inline-editor-title">{heading}</strong>
      <label className="secondary-field">
        {text.goalTitleLabel}
        <input value={goalTitle} onChange={(event) => setGoalTitle(event.target.value)} disabled={isLoading} required />
      </label>
      <label>
        {text.milestoneTitleLabel}
        <input value={title} onChange={(event) => setTitle(event.target.value)} disabled={isLoading} required />
      </label>
      <label>
        {text.scheduledDate}
        <input
          type="date"
          value={date}
          onChange={(event) => setDate(event.target.value)}
          disabled={isLoading}
          required
        />
      </label>

      {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
      <div className="editor-actions">
        <button type="submit" className="primary-button compact" disabled={isLoading}>
          {isLoading ? text.saving : text.save}
        </button>
        <button type="button" className="ghost-button compact" onClick={onCancel} disabled={isLoading}>
          {text.close}
        </button>
      </div>
    </form>
  );
}

function ColorPicker({
  value,
  disabled,
  label,
  onChange,
}: {
  value: string;
  disabled: boolean;
  label: string;
  onChange: (value: string) => void;
}) {
  return (
    <div className="color-options inline-color-options">
      {colorOptions.map((color) => (
        <button
          key={color}
          type="button"
          className={value === color ? "selected" : ""}
          style={{ "--swatch-color": color } as CSSProperties}
          onClick={() => onChange(color)}
          disabled={disabled}
          title={color}
          aria-label={`${label} ${color}`}
        />
      ))}
    </div>
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
