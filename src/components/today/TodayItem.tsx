import type { Milestone } from '../../types/milestone';

interface TodayItemProps {
  milestone: Milestone;
  goalTitle?: string;
  isUpdating: boolean;
  onToggleComplete: (milestone: Milestone) => void;
}

export function TodayItem({
  milestone,
  goalTitle,
  isUpdating,
  onToggleComplete,
}: TodayItemProps) {
  return (
    <li className="flex items-start gap-2 rounded border border-zinc-800 bg-zinc-950/60 px-2 py-2">
      <input
        aria-label={`Toggle ${milestone.title}`}
        checked={milestone.is_completed}
        className="app-no-drag mt-0.5 h-4 w-4 shrink-0 accent-sky-500"
        disabled={isUpdating}
        type="checkbox"
        onChange={() => onToggleComplete(milestone)}
      />
      <div className="min-w-0 flex-1">
        <div
          className={[
            'todo-title text-xs font-medium',
            milestone.is_completed ? 'text-zinc-500 line-through' : 'text-zinc-100',
          ].join(' ')}
        >
          {milestone.title}
        </div>
        <div className="todo-goal truncate text-[11px] text-zinc-500">
          {goalTitle ?? 'Goal'}
        </div>
      </div>
    </li>
  );
}
