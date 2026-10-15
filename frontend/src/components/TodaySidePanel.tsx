import { CheckCircle2, Circle } from "lucide-react";
import type { CalendarDateData, Goal, Language, Milestone } from "@/api/types";

type Props = {
  today: string;
  detail: CalendarDateData | null;
  goals: Goal[];
  language: Language;
  isLoading: boolean;
  error: string | null;
  pendingIds: ReadonlySet<string>;
  onRetry: () => void;
  onToggleMilestone: (id: string, completed: boolean) => Promise<void>;
};

export function TodaySidePanel({ today, detail, goals, language, isLoading, error, pendingIds, onRetry, onToggleMilestone }: Props) {
  const en = language === "en";
  const knownGoals = new Map(goals.map((goal) => [goal.id, goal]));
  const groups = new Map<string, { title: string; color: string; milestones: Milestone[] }>();
  for (const goal of detail?.goals ?? []) {
    groups.set(goal.id, { title: goal.title, color: goal.color, milestones: [] });
  }
  for (const milestone of detail?.milestones ?? []) {
    const goal = knownGoals.get(milestone.goal_id);
    const group = groups.get(milestone.goal_id) ?? {
      title: goal?.title ?? milestone.goal_title ?? (en ? "No goal" : "목표 없음"),
      color: goal?.color ?? milestone.color, milestones: [],
    };
    group.milestones.push(milestone);
    groups.set(milestone.goal_id, group);
  }
  const milestones = detail?.milestones ?? [];
  return (
    <aside className="today-side-panel" aria-label={en ? "Today's schedule" : "오늘의 일정"} aria-busy={isLoading}>
      <div className="panel-heading"><h2>{en ? "Today's schedule" : "오늘의 일정"}</h2></div>
      <time dateTime={today}>{today}</time>
      {detail ? <p className="muted-text">{en ? "Milestones completed" : "완료한 마일스톤"} {milestones.filter((m) => m.is_completed).length} / {milestones.length}</p> : null}
      <div className="today-side-panel-scroll">
        {isLoading ? <p role="status" className="muted-text">{en ? "Loading…" : "불러오는 중입니다."}</p> : null}
        {error ? <div role="alert"><p className="error-text">{error}</p><button type="button" className="ghost-button" onClick={onRetry}>{en ? "Retry" : "다시 시도"}</button></div> : null}
        {!isLoading && !error && detail && groups.size === 0 ? <p className="empty-text">{en ? "No schedule today." : "오늘 예정된 일정이 없습니다."}</p> : null}
        {Array.from(groups, ([id, group]) => (
          <section key={id} className="today-goal-group">
            <h3><span className="color-swatch" style={{ background: group.color }} />{group.title}</h3>
            {group.milestones.length === 0 ? <p className="muted-text">{en ? "Due today" : "오늘 마감"}</p> : null}
            <ul className="today-list">
              {group.milestones.map((m) => (
                <li key={m.id} className={m.is_completed ? "done" : ""}>
                  <button type="button" className="check-button" aria-label={m.title} aria-pressed={m.is_completed}
                    title={m.is_completed ? (en ? "Mark incomplete" : "미완료로 변경") : (en ? "Mark complete" : "완료로 변경")}
                    disabled={pendingIds.has(m.id)} onClick={() => { void onToggleMilestone(m.id, !m.is_completed).catch(() => undefined); }}>
                    {m.is_completed ? <CheckCircle2 size={18} aria-hidden="true" /> : <Circle size={18} aria-hidden="true" />}
                  </button>
                  <span className="color-swatch" style={{ background: m.color }} />
                  <strong title={m.title}>{m.title}</strong>
                </li>
              ))}
            </ul>
          </section>
        ))}
      </div>
    </aside>
  );
}
