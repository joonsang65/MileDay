import { CheckCircle2, Circle } from "lucide-react";

import type { Milestone } from "@/api/types";

type TodayListProps = {
  milestones: Milestone[];
  isLoading: boolean;
  onToggleMilestone: (milestoneId: string, isCompleted: boolean) => void;
};

export function TodayList({ milestones, isLoading, onToggleMilestone }: TodayListProps) {
  return (
    <section className="today-panel" aria-label="오늘 할 일">
      <div className="panel-heading">
        <h2>오늘</h2>
        <span>{milestones.length}</span>
      </div>
      {isLoading ? <p className="muted-text">불러오는 중입니다.</p> : null}
      {!isLoading && milestones.length === 0 ? (
        <p className="empty-text">오늘 예정된 마일스톤이 없습니다.</p>
      ) : null}
      <ul className="today-list">
        {milestones.map((milestone) => (
          <li key={milestone.id} className={milestone.is_completed ? "done" : ""}>
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
            <span className="color-swatch" style={{ background: milestone.color }} />
            <span>
              <strong>{milestone.title}</strong>
              <small>{milestone.goal_title ?? "목표 없음"}</small>
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
