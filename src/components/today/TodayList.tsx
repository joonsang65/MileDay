import type { Goal } from '../../types/goal';
import type { Milestone } from '../../types/milestone';
import { TodayItem } from './TodayItem';
import { useEffect, useMemo, useState } from 'react';

interface TodayListProps {
  milestones: Milestone[];
  goals: Goal[];
  updatingMilestoneId: string | null;
  onToggleComplete: (milestone: Milestone) => void;
}

export function TodayList({
  milestones,
  goals,
  updatingMilestoneId,
  onToggleComplete,
}: TodayListProps) {
  const goalTitleById = new Map(goals.map((goal) => [goal.id, goal.title]));
  const [widgetHeight, setWidgetHeight] = useState(() => window.innerHeight);

  useEffect(() => {
    const handleResize = () => setWidgetHeight(window.innerHeight);

    window.addEventListener('resize', handleResize);
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const visibleCount = useMemo(() => {
    if (widgetHeight < 460) {
      return 2;
    }

    if (widgetHeight < 540) {
      return 3;
    }

    if (widgetHeight < 640) {
      return 4;
    }

    return 6;
  }, [widgetHeight]);
  const visibleMilestones = milestones.slice(0, visibleCount);
  const hiddenCount = Math.max(0, milestones.length - visibleMilestones.length);

  return (
    <section className="flex min-h-0 flex-1 flex-col overflow-hidden">
      <div className="mb-1.5 flex shrink-0 items-center justify-between">
        <h2 className="text-sm font-semibold text-zinc-100">Today</h2>
        <span className="text-[11px] text-zinc-500">{milestones.length}</span>
      </div>
      {milestones.length === 0 ? (
        <div className="flex min-h-0 flex-1 items-center justify-center rounded border border-dashed border-zinc-800 px-3 text-center text-xs text-zinc-500">
          No milestones scheduled for today.
        </div>
      ) : (
        <ul className="min-h-0 space-y-1.5 overflow-hidden">
          {visibleMilestones.map((milestone) => (
            <TodayItem
              key={milestone.id}
              goalTitle={goalTitleById.get(milestone.goal_id)}
              isUpdating={updatingMilestoneId === milestone.id}
              milestone={milestone}
              onToggleComplete={onToggleComplete}
            />
          ))}
          {hiddenCount > 0 ? (
            <li className="rounded border border-zinc-800 px-2 py-1 text-center text-[11px] text-zinc-500">
              +{hiddenCount} more
            </li>
          ) : null}
        </ul>
      )}
    </section>
  );
}
