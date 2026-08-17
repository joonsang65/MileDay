import { useState, useEffect, useMemo } from "react";
import { ChevronDown, ChevronUp, Square, CheckSquare, Plus, Pencil } from "lucide-react";

import type { Goal, Milestone, Language, GoalUpdatePayload, MilestoneCreatePayload, MilestoneUpdatePayload } from "@/api/types";
import { apiClient } from "@/api/client";
import { FloatingPanel } from "./FloatingPanel";
import { GoalEditor, MilestoneCreateEditor, MilestoneEditor } from "./DateDetail";

type GoalListModalProps = {
  language: Language;
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
    selected: "개 선택됨",
    selectDelete: "선택 삭제",
    confirmDeleteTitle: "선택한 항목을 삭제할까요?",
    confirmDeleteDesc: "목표 삭제 시 하위 마일스톤도 삭제됩니다.",
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
    selected: "selected",
    selectDelete: "Delete Selected",
    confirmDeleteTitle: "Delete selected items?",
    confirmDeleteDesc: "Deleting a goal will also delete its milestones.",
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
  onClose,
  onUpdateGoal,
  onDeleteGoal,
  onCreateMilestone,
  onUpdateMilestone,
  onDeleteMilestone,
}: GoalListModalProps) {
  const t = labels[language];
  const dt = dateDetailLabels[language];

  const [isLoading, setIsLoading] = useState(true);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [milestonesMap, setMilestonesMap] = useState<Record<string, Milestone[]>>({});
  
  const [activeTab, setActiveTab] = useState<TabType>("ongoing");
  const [expandedGoalId, setExpandedGoalId] = useState<string | null>(null);
  const [editingItem, setEditingItem] = useState<EditingItem>(null);
  
  const [selectedGoals, setSelectedGoals] = useState<Set<string>>(new Set());
  const [selectedMilestones, setSelectedMilestones] = useState<Set<string>>(new Set());
  const [isDeleting, setIsDeleting] = useState(false);

  useEffect(() => {
    async function loadData() {
      setIsLoading(true);
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
        completedCount,
        totalCount: ms.length,
      };
    });
  }, [goals, milestonesMap]);

  const filteredGoals = useMemo(() => {
    return goalData.filter(g => {
      if (activeTab === "ongoing") return !g.isCompleted;
      if (activeTab === "completed") return g.isCompleted;
      return true;
    });
  }, [goalData, activeTab]);

  const handleToggleGoalSelect = (goalId: string) => {
    const next = new Set(selectedGoals);
    if (next.has(goalId)) {
      next.delete(goalId);
    } else {
      next.add(goalId);
    }
    setSelectedGoals(next);
  };

  const handleToggleMilestoneSelect = (milestoneId: string) => {
    const next = new Set(selectedMilestones);
    if (next.has(milestoneId)) {
      next.delete(milestoneId);
    } else {
      next.add(milestoneId);
    }
    setSelectedMilestones(next);
  };

  const handleDeleteConfirm = async () => {
    // Delete in parallel
    const p1 = Array.from(selectedGoals).map(id => onDeleteGoal(id));
    const p2 = Array.from(selectedMilestones).map(id => onDeleteMilestone(id));
    await Promise.all([...p1, ...p2]);
    
    // Refresh list locally
    setGoals(prev => prev.filter(g => !selectedGoals.has(g.id)));
    
    const newMap = { ...milestonesMap };
    for (const gid in newMap) {
      newMap[gid] = newMap[gid].filter(m => !selectedMilestones.has(m.id));
      if (selectedGoals.has(gid)) {
        delete newMap[gid];
      }
    }
    setMilestonesMap(newMap);
    
    setSelectedGoals(new Set());
    setSelectedMilestones(new Set());
    setIsDeleting(false);
  };

  // Re-fetch milestones for a specific goal after CUD operations
  const refreshGoalMilestones = async (goalId: string) => {
    const ms = await apiClient.getGoalMilestones(goalId);
    setMilestonesMap(prev => ({ ...prev, [goalId]: ms }));
  };

  const selectedTotal = selectedGoals.size + selectedMilestones.size;

  const selectionFooter = selectedTotal > 0 && !isDeleting ? (
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", width: "100%" }}>
      <span style={{ fontSize: "13px", fontWeight: 500, color: "var(--text-primary)" }}>
        {selectedTotal}{t.selected}
      </span>
      <button
        type="button"
        className="button-primary"
        style={{ backgroundColor: "var(--text-danger)", borderColor: "var(--text-danger)", fontSize: "12px", padding: "6px 16px" }}
        onClick={() => setIsDeleting(true)}
      >
        {t.selectDelete}
      </button>
    </div>
  ) : undefined;

  return (
    <>
      <FloatingPanel 
        title={t.title} 
        onClose={onClose} 
        placement="center" 
        closeLabel={t.cancel}
        className="goal-list-modal-panel"
        footer={selectionFooter}
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

        {isLoading ? (
          <p className="muted-text" style={{ padding: "20px", textAlign: "center" }}>{t.loading}</p>
        ) : filteredGoals.length === 0 ? (
          <p className="muted-text" style={{ padding: "20px", textAlign: "center" }}>{t.empty}</p>
        ) : (
          <ul className="plain-list day-view-list" style={{ maxHeight: "50vh", overflowY: "auto", overflowX: "hidden" }}>
            {filteredGoals.map(group => {
              const isExpanded = expandedGoalId === group.id;
              const isGoalSelected = selectedGoals.has(group.id);
              const isGoalEditing = editingItem?.type === "goal" && editingItem.id === group.id;
              
              if (isGoalEditing && editingItem.type === "goal") {
                return (
                  <li key={group.id} className="goal-group">
                    <GoalEditor
                      goal={editingItem.goal}
                      isLoading={false}
                      text={dt}
                      onUpdate={async (gid, p) => {
                        await onUpdateGoal(gid, p);
                        setGoals(prev => prev.map(g => g.id === gid ? { ...g, ...p } as Goal : g));
                        setEditingItem(null);
                      }}
                      onDelete={async (gid) => {
                        await onDeleteGoal(gid);
                        setGoals(prev => prev.filter(g => g.id !== gid));
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
                    <button
                      type="button"
                      className="icon-button compact-icon"
                      onClick={() => handleToggleGoalSelect(group.id)}
                      style={{ color: isGoalSelected ? "var(--primary)" : "var(--text-tertiary)", flexShrink: 0 }}
                    >
                      {isGoalSelected ? <CheckSquare size={16} /> : <Square size={16} />}
                    </button>
                    
                    <div 
                      onClick={() => setExpandedGoalId(isExpanded ? null : group.id)}
                      style={{ flex: 1, display: "flex", flexDirection: "column", cursor: "pointer", gap: "2px", minWidth: 0 }}
                    >
                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                        <span className="color-swatch" style={{ background: group.color, flexShrink: 0 }} aria-hidden="true" />
                        <strong style={{ fontSize: "13px", color: "var(--text-primary)", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{group.title}</strong>
                      </div>
                      <div style={{ display: "flex", gap: "10px", fontSize: "11px", color: "var(--text-tertiary)", paddingLeft: "14px" }}>
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
                      onClick={() => setExpandedGoalId(isExpanded ? null : group.id)}
                      style={{ flexShrink: 0 }}
                    >
                      {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                    </button>
                  </div>

                  {isExpanded && (
                    <div style={{ paddingLeft: "24px", paddingTop: "8px" }}>
                      <ul className="plain-list">
                        {group.milestones.map(m => {
                          const isMilestoneSelected = selectedMilestones.has(m.id);
                          const isMilestoneEditing = editingItem?.type === "milestone" && editingItem.id === m.id;
                          
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
                                  onClick={() => handleToggleMilestoneSelect(m.id)}
                                  style={{ color: isMilestoneSelected ? "var(--primary)" : "var(--text-tertiary)", flexShrink: 0 }}
                                >
                                  {isMilestoneSelected ? <CheckSquare size={16} /> : <Square size={16} />}
                                </button>
                                <div style={{ flex: 1, display: "flex", justifyContent: "space-between", alignItems: "center", minWidth: 0 }}>
                                  <strong className={m.is_completed ? "completed-text" : ""} style={{ fontSize: "12px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                                    {m.title}
                                  </strong>
                                  <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "11px", color: "var(--text-tertiary)", flexShrink: 0, paddingLeft: "8px" }}>
                                    <span>{m.scheduled_date}</span>
                                    {m.is_completed && <strong style={{ color: "var(--primary)" }}>{t.completed}</strong>}
                                  </div>
                                </div>
                                <button 
                                  type="button" 
                                  className="icon-button compact-icon"
                                  onClick={() => setEditingItem({ type: "milestone", id: m.id, milestone: m })}
                                  style={{ flexShrink: 0 }}
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
                            scheduledDate=""
                            heading={t.addMilestone}
                            isLoading={false}
                            text={dt}
                            onCreate={async (gid, p) => {
                              await onCreateMilestone(gid, p);
                              await refreshGoalMilestones(group.id);
                              setEditingItem(null);
                            }}
                            onCancel={() => setEditingItem(null)}
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
                          <button
                            type="button"
                            className="button-secondary"
                            onClick={() => setEditingItem({ type: "goal", id: group.id, goal: group })}
                            style={{ flex: 1, padding: "6px", fontSize: "12px", display: "flex", justifyContent: "center", alignItems: "center", gap: "4px" }}
                          >
                            <Pencil size={14} /> {t.editGoal}
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



      {/* Delete Confirmation Modal */}
      {isDeleting && (
        <FloatingPanel title={t.confirmDeleteTitle} onClose={() => setIsDeleting(false)} placement="center" closeLabel={t.cancel}>
          <div style={{ padding: "0 4px 16px" }}>
            <ul style={{ margin: "0 0 12px 16px", padding: 0, fontSize: "14px", lineHeight: "1.6" }}>
              {selectedGoals.size > 0 && (
                <li>{t.goalCount} {selectedGoals.size}개</li>
              )}
              {selectedMilestones.size > 0 && (
                <li>{t.milestoneCount} {selectedMilestones.size}개</li>
              )}
            </ul>
            <p style={{ color: "var(--text-danger)", fontSize: "13px", margin: 0 }}>
              {t.confirmDeleteDesc}
            </p>
          </div>
          <div style={{ display: "flex", gap: "8px" }}>
            <button type="button" className="button-secondary" style={{ flex: 1 }} onClick={() => setIsDeleting(false)}>
              {t.cancel}
            </button>
            <button type="button" className="button-primary" style={{ flex: 1, backgroundColor: "var(--text-danger)", borderColor: "var(--text-danger)" }} onClick={handleDeleteConfirm}>
              {t.delete}
            </button>
          </div>
        </FloatingPanel>
      )}
    </>
  );
}
