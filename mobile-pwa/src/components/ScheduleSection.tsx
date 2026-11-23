import { displayDate } from "../date";
import type { CalendarDateData, Goal, Milestone } from "../types";

export function WeekScheduleSection({ days }: { days: CalendarDateData[] }) {
  return (
    <section className="schedule-section compact">
      <h2>이번 7일 일정</h2>
      <div className="week-list">
        {days.map((day) => {
          const items = buildScheduleItems(day.goals, day.milestones);
          return (
            <article className="week-day" key={day.date}>
              <div className="week-day-header">
                <strong>{displayDate(day.date)}</strong>
                <span>{items.length}개</span>
              </div>
              {items.length === 0 ? <p className="empty-state">일정이 없습니다.</p> : null}
              {items.length > 0 ? (
                <div className="schedule-list">
                  {items.map((item) => (
                    <div className="schedule-item" key={item.id}>
                      <span className="color-dot" style={{ background: item.color }} />
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.meta}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

export function ScheduleSection({ title, data, compact = false }: { title: string; data: CalendarDateData | null; compact?: boolean }) {
  const items = data ? buildScheduleItems(data.goals, data.milestones) : [];
  return (
    <section className={compact ? "schedule-section compact" : "schedule-section"}>
      <h2>{title}</h2>
      {items.length === 0 ? <p className="empty-state">일정이 없습니다.</p> : null}
      <div className="schedule-list">
        {items.map((item) => (
          <article className="schedule-item" key={item.id}>
            <span className="color-dot" style={{ background: item.color }} />
            <div>
              <strong>{item.title}</strong>
              <p>{item.meta}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function buildScheduleItems(goals: Goal[], milestones: Milestone[]) {
  return [
    ...goals.map((goal) => ({
      id: `goal-${goal.id}`,
      title: goal.title,
      color: goal.color,
      meta: goal.is_completed ? "목표 완료" : "목표 마감",
    })),
    ...milestones.map((milestone) => ({
      id: `milestone-${milestone.id}`,
      title: milestone.title,
      color: milestone.color,
      meta: milestone.goal_title || "마일스톤",
    })),
  ].sort((a, b) => a.title.localeCompare(b.title, "ko"));
}
