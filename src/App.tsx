import { addMonths, startOfMonth } from 'date-fns';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { Calendar } from './components/calendar/Calendar';
import { WidgetShell } from './components/layout/WidgetShell';
import { TodayList } from './components/today/TodayList';
import { getTodayDateString } from './lib/date';
import { getGoals } from './services/goalService';
import {
  getMilestones,
  toggleMilestoneComplete,
} from './services/milestoneService';
import type { Goal } from './types/goal';
import type { Milestone } from './types/milestone';

export default function App() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [milestones, setMilestones] = useState<Milestone[]>([]);
  const [currentMonth, setCurrentMonth] = useState(() =>
    startOfMonth(new Date()),
  );
  const [selectedDate, setSelectedDate] = useState(getTodayDateString);
  const [isLoading, setIsLoading] = useState(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [updatingMilestoneId, setUpdatingMilestoneId] = useState<string | null>(
    null,
  );
  const [isAlwaysOnTop, setIsAlwaysOnTop] = useState(false);

  useEffect(() => {
    void window.mileDayWidget?.getSettings().then((settings) => {
      setIsAlwaysOnTop(settings.widget.alwaysOnTop);
    });
  }, []);

  const loadWidgetData = useCallback(async () => {
    setIsLoading(true);
    setErrorMessage(null);

    try {
      const [loadedGoals, loadedMilestones] = await Promise.all([
        getGoals(),
        getMilestones(),
      ]);

      setGoals(loadedGoals);
      setMilestones(loadedMilestones);
    } catch (error) {
      console.error(error);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Failed to load MileDay data.',
      );
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadWidgetData();
  }, [loadWidgetData]);

  const todayMilestones = useMemo(() => {
    const today = getTodayDateString();

    return milestones.filter(
      (milestone) => milestone.scheduled_date === today,
    );
  }, [milestones]);

  const handleToggleComplete = async (milestone: Milestone) => {
    setUpdatingMilestoneId(milestone.id);
    setErrorMessage(null);

    try {
      const updatedMilestone = await toggleMilestoneComplete(
        milestone.id,
        !milestone.is_completed,
      );

      setMilestones((currentMilestones) =>
        currentMilestones.map((currentMilestone) =>
          currentMilestone.id === updatedMilestone.id
            ? updatedMilestone
            : currentMilestone,
        ),
      );
    } catch (error) {
      console.error(error);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Failed to update milestone.',
      );
    } finally {
      setUpdatingMilestoneId(null);
    }
  };

  const handleToggleAlwaysOnTop = async () => {
    const nextAlwaysOnTop = !isAlwaysOnTop;
    setIsAlwaysOnTop(nextAlwaysOnTop);

    try {
      const settings = await window.mileDayWidget?.setAlwaysOnTop(
        nextAlwaysOnTop,
      );

      if (settings) {
        setIsAlwaysOnTop(settings.widget.alwaysOnTop);
      }
    } catch (error) {
      console.error(error);
      setIsAlwaysOnTop(!nextAlwaysOnTop);
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'Failed to update widget settings.',
      );
    }
  };

  return (
    <WidgetShell>
      <div className="flex h-full min-h-0 flex-col gap-2 p-3">
        <header className="app-drag flex shrink-0 items-center justify-between gap-2">
          <div className="min-w-0">
            <h1 className="text-base font-semibold tracking-normal text-zinc-50">
              MileDay
            </h1>
            <p className="text-[11px] text-zinc-500">{selectedDate}</p>
          </div>
          <div className="app-no-drag flex items-center gap-1">
            <button
              className={[
                'app-no-drag rounded border px-2 py-1 text-[11px] hover:bg-zinc-800',
                isAlwaysOnTop
                  ? 'border-sky-500 text-sky-200'
                  : 'border-zinc-700 text-zinc-300',
              ].join(' ')}
              type="button"
              onClick={() => void handleToggleAlwaysOnTop()}
            >
              Pin
            </button>
            <button
              className="app-no-drag rounded border border-zinc-700 px-2 py-1 text-[11px] text-zinc-300 hover:bg-zinc-800"
              type="button"
              onClick={() => void loadWidgetData()}
            >
              Refresh
            </button>
          </div>
        </header>

        {errorMessage ? (
          <div className="shrink-0 truncate rounded border border-rose-900 bg-rose-950/40 px-3 py-2 text-xs text-rose-200">
            {errorMessage}
          </div>
        ) : null}

        {isLoading ? (
          <div className="flex min-h-0 flex-1 items-center justify-center text-xs text-zinc-500">
            Loading MileDay...
          </div>
        ) : (
          <div className="grid min-h-0 flex-1 grid-rows-[auto_minmax(0,1fr)] gap-2 overflow-hidden">
            <Calendar
              currentMonth={currentMonth}
              goals={goals}
              milestones={milestones}
              selectedDate={selectedDate}
              onNextMonth={() =>
                setCurrentMonth((month) => addMonths(month, 1))
              }
              onPreviousMonth={() =>
                setCurrentMonth((month) => addMonths(month, -1))
              }
              onSelectDate={setSelectedDate}
            />
            <TodayList
              goals={goals}
              milestones={todayMilestones}
              updatingMilestoneId={updatingMilestoneId}
              onToggleComplete={handleToggleComplete}
            />
          </div>
        )}
      </div>
    </WidgetShell>
  );
}
