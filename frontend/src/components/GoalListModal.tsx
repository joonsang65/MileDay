import { useEffect, useMemo, useState } from "react";
import { CheckSquare, ChevronDown, ChevronUp, Square } from "lucide-react";

import { apiClient } from "@/api/client";
import type { Goal, GoalUpdatePayload, Language, Milestone, MilestoneCreatePayload, MilestoneUpdatePayload } from "@/api/types";

import { FloatingPanel } from "./FloatingPanel";

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

const labels = {
  ko: {
    title: "전체 목표",
    ongoing: "진행중",
    completed: "완료",
    all: "전체",
    cancel: "취소",
    loading: "불러오는 중...",
    empty: "표시할 목표가 없습니다.",
    noMilestones: "마일스톤이 없습니다.",
    until: "까지",
  },
  en: {
    title: "All Goals",
    ongoing: "Ongoing",
    completed: "Completed",
    all: "All",
    cancel: "Cancel",
    loading: "Loading...",
    empty: "No goals to display.",
    noMilestones: "No milestones.",
    until: "Until",
  },
};

export function GoalListModal({
  language,
  initialGoals = [],
  onClose,
  onUpdateMilestone,
}: GoalListModalProps) {
  const t = labels[language];

  const [isLoading, setIsLoading] = useState(initialGoals.length === 0);
  const [goals, setGoals] = useState<Goal[]>(initialGoals);
  const [milestonesMap, setMilestonesMap] = useState<Record<string, Milestone[]>>({});
  const [activeTab, setActiveTab] = useState<TabType>("ongoing");
  const [expandedGoalId, setExpandedGoalId] = useState<string | null>(null);
  const [isMilestoneToggling, setIsMilestoneToggling] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      if (initialGoals.length === 0) {
        setIsLoading(true);
      }
      try {
        const fetchedGoals = await apiClient.listGoals();
        setGoals(fetchedGoals);

        const milestonesByGoal: Record<string, Milestone[]> = {};
        await Promise.all(
          fetchedGoals.map(async (goal) => {
            milestonesByGoal[goal.id] = await apiClient.getGoalMilestones(goal.id);
          }),
        );
        setMilestonesMap(milestonesByGoal);
      } catch (error) {
        console.error("Failed to load goals/milestones", error);
      } finally {
        setIsLoading(false);
      }
    }
    void loadData();
  }, [initialGoals.length]);

  const goalData = useMemo(() => {
    return goals.map((goal) => {
      const milestones = milestonesMap[goal.id] ?? [];
      const isCompleted = milestones.length > 0 && milestones.every((milestone) => milestone.is_completed);
      const completedCount = milestones.filter((milestone) => milestone.is_completed).length;
      return {
        ...goal,
        milestones,
        isCompleted,
        totalCount: milestones.length,
        completedCount,
      };
    });
  }, [goals, milestonesMap]);

  const filteredGoals = useMemo(() => {
    switch (activeTab) {
      case "ongoing":
        return goalData.filter((goal) => !goal.isCompleted);
      case "completed":
        return goalData.filter((goal) => goal.isCompleted);
      case "all":
      default:
        return goalData;
    }
  }, [activeTab, goalData]);

  async function handleToggleMilestone(milestone: Milestone, goalId: string) {
    if (isMilestoneToggling === milestone.id) {
      return;
    }

    setIsMilestoneToggling(milestone.id);
    try {
      await onUpdateMilestone(milestone.id, { is_completed: !milestone.is_completed });
      setMilestonesMap((current) => {
        const milestones = current[goalId] ?? [];
        return {
          ...current,
          [goalId]: milestones.map((item) => (
            item.id === milestone.id ? { ...item, is_completed: !item.is_completed } : item
          )),
        };
      });
    } catch (error) {
      console.error("Failed to toggle milestone", error);
    } finally {
      setIsMilestoneToggling(null);
    }
  }

  return (
    <FloatingPanel
      title={t.title}
      onClose={onClose}
      placement="center"
      closeLabel={t.cancel}
      className="goal-list-modal-panel"
    >
      <div className="goal-list-tabs">
        {(["ongoing", "completed", "all"] as TabType[]).map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={`goal-list-tab ${activeTab === tab ? "button-primary" : "button-secondary"}`}
          >
            {t[tab]}
          </button>
        ))}
      </div>

      {isLoading && goals.length === 0 ? (
        <p className="muted-text goal-list-empty">{t.loading}</p>
      ) : filteredGoals.length === 0 ? (
        <p className="muted-text goal-list-empty">{t.empty}</p>
      ) : (
        <ul className="plain-list day-view-list goal-list-scroll">
          {filteredGoals.map((goal) => {
            const isExpanded = expandedGoalId === goal.id;
            const progress = goal.totalCount > 0
              ? Math.round((goal.completedCount / goal.totalCount) * 100)
              : 0;

            return (
              <li key={goal.id} className="goal-list-item">
                <div className="editable-row goal-list-row">
                  <div className="goal-list-color-cell">
                    <span className="color-swatch goal-list-color-swatch" style={{ background: goal.color }} aria-hidden="true" />
                  </div>

                  <div
                    onClick={() => setExpandedGoalId(isExpanded ? null : goal.id)}
                    className="goal-list-content"
                  >
                    <div className="goal-list-title-row">
                      <strong
                        className="goal-list-title"
                        style={{ opacity: goal.isCompleted ? 0.6 : 1, textDecoration: goal.isCompleted ? "line-through" : "none" }}
                      >
                        {goal.title}
                      </strong>
                    </div>
                    <div className="goal-list-meta">
                      <span>{goal.deadline} {t.until}</span>
                      <span>
                        {goal.isCompleted ? (
                          <strong className="goal-list-completed-label">{t.completed}</strong>
                        ) : (
                          `${progress}%`
                        )}
                      </span>
                    </div>
                  </div>

                  <button
                    type="button"
                    className="icon-button compact-icon goal-list-icon-button"
                    onClick={() => setExpandedGoalId(isExpanded ? null : goal.id)}
                  >
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                  </button>
                </div>

                {isExpanded ? (
                  <div className="goal-list-nested">
                    <ul className="plain-list">
                      {goal.milestones.length === 0 ? (
                        <li className="goal-list-item">
                          <div className="editable-row goal-list-row goal-list-milestone-row goal-list-empty-milestone-row">
                            <span>{t.noMilestones}</span>
                          </div>
                        </li>
                      ) : goal.milestones.map((milestone) => {
                        const isToggling = isMilestoneToggling === milestone.id;
                        return (
                          <li key={milestone.id} className="goal-list-item">
                            <div className="editable-row goal-list-row goal-list-milestone-row">
                              <button
                                type="button"
                                className="icon-button compact-icon goal-list-icon-button"
                                onClick={() => void handleToggleMilestone(milestone, goal.id)}
                                disabled={isToggling}
                                style={{ color: milestone.is_completed ? "var(--primary)" : "var(--text-tertiary)", opacity: isToggling ? 0.5 : 1 }}
                              >
                                {milestone.is_completed ? <CheckSquare size={16} /> : <Square size={16} />}
                              </button>
                              <div className="goal-list-milestone-content">
                                <strong
                                  className="goal-list-milestone-title"
                                  style={{ opacity: milestone.is_completed ? 0.6 : 1, textDecoration: milestone.is_completed ? "line-through" : "none" }}
                                >
                                  {milestone.title}
                                </strong>
                                <div className="goal-list-milestone-meta">
                                  <span>{milestone.scheduled_date}</span>
                                  {milestone.is_completed ? <strong className="goal-list-completed-label">{t.completed}</strong> : null}
                                </div>
                              </div>
                            </div>
                          </li>
                        );
                      })}
                    </ul>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </FloatingPanel>
  );
}
