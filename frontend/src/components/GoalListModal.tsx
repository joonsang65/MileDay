import { useState, useEffect, useMemo } from "react";
import { ChevronDown, ChevronUp, Square, CheckSquare, Plus, Pencil } from "lucide-react";

import type { Goal, Milestone, Language, GoalUpdatePayload, MilestoneCreatePayload, MilestoneUpdatePayload } from "@/api/types";
import { apiClient } from "@/api/client";
import { FloatingPanel } from "./FloatingPanel";
import { GoalEditor, MilestoneCreateEditor, MilestoneEditor } from "./DateDetail";

type GoalListModalProps = {
  language: Language;
  initialGoals?: Goal[];
  onClose: () => void;
  onUpdateGoal: (goalId: string, payload: GoalUpdatePayload) => Promise<void>;
  onDeleteGoal: (goalId: string) => Promise<void>;
  onCreateMilestone: (goalId: string, payload: MilestoneCreatePayload) => Promise<void>;
  onUpdateMilestone: (milestoneId: string, payload: MilestoneUpdatePayload) => Promise<void>;
  onDeleteMilestone: (milestoneId: string) => Promise<void>;
};

type TabType = "ongoing" | "completed" | "all";
type EditingItem = { type: "goal"; id: string; goal: Goal } | { type: "new-milestone"; goalId: string; color: string } | { type: "milestone"; id: string; milestone: Milestone } | null;

const labels = {
  ko: {
    title: "전체 목표",
    ongoing: "진행중",
    completed: "완료",
    all: "전체",
    delete: "삭제",
    cancel: "취소",
    goalCount: "목표",
    milestoneCount: "마일스톤",
    addMilestone: "마일스톤",
    editGoal: "목표 편집",
    loading: "불러오는 중...",
    empty: "표시할 목표가 없습니다.",
    until: "까지",
  },
  en: {
    title: "All Goals",
    ongoing: "Ongoing",
    completed: "Completed",
    all: "All",
    delete: "Delete",
    cancel: "Cancel",
    goalCount: "Goals",
    milestoneCount: "Milestones",
    addMilestone: "Milestone",
    editGoal: "Edit Goal",
    loading: "Loading...",
    empty: "No goals to display.",
    until: "Until",
  }
};

// DateDetailLabels is needed by the editors
const dateDetailLabels = {
  ko: {
    loading: "불러오는 중...",
    empty: "일정이 없습니다.",
    goals: "목표",
    task: "일정",
    noGoal: "목표 없음",
    save: "저장",
    close: "닫기",
    cancel: "취소",
    delete: "삭제",
    deleteConfirm: "삭제하시겠습니까?",
    recurringNote: "반복 목표입니다.",
    milestoneTitleLabel: "일정 내용",
    milestoneDateLabel: "예정일",
  },
  en: {
    loading: "Loading...",
    empty: "No schedules.",
    goals: "Goals",
    task: "Task",
    noGoal: "No Goal",
    save: "Save",
    close: "Close",
    cancel: "Cancel",
    delete: "Delete",
    deleteConfirm: "Are you sure to delete?",
    recurringNote: "Recurring goal.",
    milestoneTitleLabel: "Task content",
    milestoneDateLabel: "Scheduled Date",
  },
};

export function GoalListModal({
  language,
  initialGoals = [],
  onClose,
  onUpdateGoal,
  onDeleteGoal,
  onCreateMilestone,
  onUpdateMilestone,
  onDeleteMilestone,
}: GoalListModalProps) {
  const t = labels[language];
  const dt = dateDetailLabels[language];

  const [isLoading, setIsLoading] = useState(initialGoals.length === 0);
  const [goals, setGoals] = useState<Goal[]>(initialGoals);
  const [milestonesMap, setMilestonesMap] = useState<Record<string, Milestone[]>>({});
  
  const [activeTab, setActiveTab] = useState<TabType>("ongoing");
  const [expandedGoalId, setExpandedGoalId] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<EditingItem>(null);
  const [isMilestoneToggling, setIsMilestoneToggling] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (initialGoals.length === 0) {
        setIsLoading(true);
      }
      try {
        const fetchedGoals = await apiClient.listGoals();
        setGoals(fetchedGoals);
        
        // Fetch milestones for all goals
        const mData: Record<string, Milestone[]> = {};
        await Promise.all(
          fetchedGoals.map(async (goal) => {
            const milestones = await apiClient.getGoalMilestones(goal.id);
            mData[goal.id] = milestones;
          })
        );
        setMilestonesMap(mData);
      } catch (err) {
        console.error("Failed to load goals/milestones", err);
      } finally {
        setIsLoading(false);
      }
    }
    void loadData();
  }, []);

  const goalData = useMemo(() => {
    return goals.map(goal => {
      const ms = milestonesMap[goal.id] || [];
      const isCompleted = ms.length > 0 && ms.every(m => m.is_completed);
      const completedCount = ms.filter(m => m.is_completed).length;
      return {
        ...goal,
        milestones: ms,
        isCompleted,
        totalCount: ms.length,
        completedCount,
      };
    });
  }, [goals, milestonesMap]);

  const filteredGoals = useMemo(() => {
    switch (activeTab) {
      case "ongoing":
        return goalData.filter(g => !g.isCompleted);
      case "completed":
        return goalData.filter(g => g.isCompleted);
      case "all":
      default:
        return goalData;
    }
  }, [goalData, activeTab]);

  const handleToggleMilestone = async (milestone: Milestone, goalId: string) => {
    if (isMilestoneToggling === milestone.id) return;
    setIsMilestoneToggling(milestone.id);
    try {
      await onUpdateMilestone(milestone.id, { is_completed: !milestone.is_completed });
      setMilestonesMap(prev => {
        const ms = prev[goalId] || [];
        return {
          ...prev,
          [goalId]: ms.map(m => m.id === milestone.id ? { ...m, is_completed: !m.is_completed } : m)
        };
      });
    } catch (err) {
      console.error("Failed to toggle milestone", err);
    } finally {
      setIsMilestoneToggling(null);
    }
  };

  const refreshGoalMilestones = async (goalId: string) => {
    const ms = await apiClient.getGoalMilestones(goalId);
    setMilestonesMap(prev => ({ ...prev, [goalId]: ms }));
  };

  return (
    <>
      <FloatingPanel 
        title={t.title} 
        onClose={onClose} 
        placement="center" 
        closeLabel={t.cancel}
        className="goal-list-modal-panel"
      >
        <div style={{ display: 'flex', gap: '8px', marginBottom: '12px' }}>
          {(["ongoing", "completed", "all"] as TabType[]).map(tab => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={activeTab === tab ? "button-primary" : "button-secondary"}
              style={{ flex: 1, padding: "6px 0", fontSize: "12px", borderRadius: "20px" }}
            >
              {t[tab]}
            </button>
          ))}
        </div>

        {isLoading && goals.length === 0 ? (
          <p className="muted-text" style={{ padding: "20px", textAlign: "center" }}>{t.loading}</p>
        ) : filteredGoals.length === 0 ? (
          <p className="muted-text" style={{ padding: "20px", textAlign: "center" }}>{t.empty}</p>
        ) : (
          <ul className="plain-list day-view-list" style={{ maxHeight: "60vh", overflowY: "auto", overflowX: "hidden" }}>
            {filteredGoals.map(group => {
              const isExpanded = expandedGoalId === group.id;
              const isGoalEditing = editingItem?.type === "goal" && editingItem.id === group.id;
              
              if (isGoalEditing && editingItem.type === "goal") {
                return (
                  <li key={group.id} className="goal-group">
                    <GoalEditor
                      goal={editingItem.goal}
                      isLoading={false}
                      text={dt}
                      onSave={async (p) => {
                        await onUpdateGoal(group.id, p);
                        setGoals(prev => prev.map(g => g.id === group.id ? { ...g, ...p } as Goal : g));
                        setEditingItem(null);
                      }}
                      onDelete={async () => {
                        await onDeleteGoal(group.id);
                        setGoals(prev => prev.filter(g => g.id !== group.id));
                        setEditingItem(null);
                      }}
                      onCancel={() => setEditingItem(null)}
                    />
                  </li>
                );
              }

              return (
                <li key={group.id} style={{ marginBottom: "6px" }}>
                  <div className="editable-row" style={{ display: "flex", alignItems: "center", padding: "8px", gap: "8px", width: "100%", boxSizing: "border-box" }}>
                    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", width: "24px" }}>
                      <span className="color-swatch" style={{ background: group.color, flexShrink: 0 }} aria-hidden="true" />
                    </div>
                    
                    <div 
                      onClick={() => setExpandedGoalId(isExpanded ? null : group.id)}
                      style={{ flex: 1, display: "flex", flexDirection: "column", cursor: "pointer", gap: "2px", minWidth: 0 }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <strong style={{ fontSize: "13px", color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", opacity: group.isCompleted ? 0.6 : 1, textDecoration: group.isCompleted ? "line-through" : "none" }}>{group.title}</strong>
                      </div>
                      <div style={{ display: "flex", gap: "10px", fontSize: "11px", color: "var(--text-tertiary)" }}>
                        <span>{group.deadline} {t.until}</span>
                        <span>
                          {group.isCompleted ? (
                            <strong style={{ color: "var(--primary)" }}>{t.completed}</strong>
                          ) : (
                            `${group.totalCount > 0 ? Math.round((group.completedCount / group.totalCount) * 100) : 0}%`
                          )}
                        </span>
                      </div>
                    </div>
                    
                    <button
                      type="button"
                      className="icon-button compact-icon"
                      onClick={() => setEditingItem({ type: "goal", id: group.id, goal: group })}
                      style={{ flexShrink: 0, opacity: 0.7 }}
                    >
                      <Pencil size={14} />
                    </button>
                    <button
                      type="button"
                      className="icon-button compact-icon"
                      onClick={() => setExpandedGoalId(isExpanded ? null : group.id)}
                      style={{ flexShrink: 0 }}
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>

                  {isExpanded && (
                    <div style={{ paddingLeft: "32px", paddingTop: "8px" }}>
                      <ul className="plain-list">
                        {group.milestones.map(m => {
                          const isMilestoneEditing = editingItem?.type === "milestone" && editingItem.id === m.id;
                          const isToggling = isMilestoneToggling === m.id;
                          
                          if (isMilestoneEditing && editingItem.type === "milestone") {
                            return (
                              <li key={m.id} className="milestone-row" style={{ marginLeft: "-24px" }}>
                                <MilestoneEditor
                                  goal={group}
                                  milestone={editingItem.milestone}
                                  isLoading={false}
                                  text={dt}
                                  onUpdate={async (mid, p) => {
                                    await onUpdateMilestone(mid, p);
                                    await refreshGoalMilestones(group.id);
                                    setEditingItem(null);
                                  }}
                                  onDelete={async (mid) => {
                                    await onDeleteMilestone(mid);
                                    await refreshGoalMilestones(group.id);
                                    setEditingItem(null);
                                  }}
                                  onCancel={() => setEditingItem(null)}
                                />
                              </li>
                            );
                          }

                          return (
                            <li key={m.id} style={{ marginBottom: "6px" }}>
                              <div className="editable-row" style={{ display: "flex", alignItems: "center", padding: "6px 8px", gap: "8px", width: "100%", boxSizing: "border-box" }}>
                                <button
                                  type="button"
                                  className="icon-button compact-icon"
                                  onClick={() => handleToggleMilestone(m, group.id)}
                                  disabled={isToggling}
                                  style={{ color: m.is_completed ? "var(--primary)" : "var(--text-tertiary)", flexShrink: 0, opacity: isToggling ? 0.5 : 1 }}
                                >
                                  {m.is_completed ? <CheckSquare size={16} /> : <Square size={16} />}
                                </button>
                                <div style={{ flex: 1, display: "flex", justifyContent: "space-between", alignItems: "center", minWidth: 0, gap: "6px" }}>
                                  <strong style={{ fontSize: "12px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis", opacity: m.is_completed ? 0.6 : 1, textDecoration: m.is_completed ? "line-through" : "none" }}>
                                    {m.title}
                                  </strong>
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "var(--text-tertiary)", flexShrink: 0 }}>
                                    <span>{m.scheduled_date}</span>
                                    {m.is_completed && <strong style={{ color: "var(--primary)" }}>{t.completed}</strong>}
                                  </div>
                                </div>
                                <button 
                                  type="button" 
                                  className="icon-button compact-icon"
                                  onClick={() => setEditingItem({ type: "milestone", id: m.id, milestone: m })}
                                  style={{ flexShrink: 0, opacity: 0.7 }}
                                >
                                  <Pencil size={14} />
                                </button>
                              </div>
                            </li>
                          );
                        })}
                      </ul>
                      
                      {editingItem?.type === "new-milestone" && editingItem.goalId === group.id ? (
                        <div style={{ marginLeft: "-24px", marginTop: "8px" }}>
                          <MilestoneCreateEditor
                            goal={group}
                            scheduledDate={new Date().toISOString().split("T")[0]}
                            heading={t.addMilestone}
                            isLoading={false}
                            text={dt}
                            onCancel={() => setEditingItem(null)}
                            onSave={async (payload) => {
                              await onCreateMilestone(group.id, payload);
                              await refreshGoalMilestones(group.id);
                              setEditingItem(null);
                            }}
                            onUpdateGoal={async (p) => {
                              await onUpdateGoal(group.id, p);
                              setGoals(prev => prev.map(g => g.id === group.id ? { ...g, ...p } as Goal : g));
                            }}
                          />
                        </div>
                      ) : (
                        <div style={{ display: "flex", gap: "8px", marginTop: "12px", marginBottom: "8px" }}>
                          <button
                            type="button"
                            className="button-secondary"
                            onClick={() => setEditingItem({ type: "new-milestone", goalId: group.id, color: group.color })}
                            style={{ flex: 1, padding: "6px", fontSize: "12px", display: "flex", justifyContent: "center", alignItems: "center", gap: "4px" }}
                          >
                            <Plus size={14} /> {t.addMilestone}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </li>
              );
            })}
          </ul>
        )}
      </FloatingPanel>
    </>
  );
}
