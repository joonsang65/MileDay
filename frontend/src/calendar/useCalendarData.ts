import { type Dispatch, type SetStateAction, useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError, apiClient } from "@/api/client";
import type { CalendarDateData, Goal, Milestone, UserSettings } from "@/api/types";
import {
  type CalendarData,
  toCalendarMonthView,
  upsertGoalInCalendar,
  upsertGoalInDateDetail,
  upsertMilestoneInCalendar,
  upsertMilestoneInDateDetail,
  countCompletedMilestones,
  updateGoalCompletionInCalendar,
  updateGoalCompletionInDateDetail,
  updateGoalMilestonesCompletionInCalendar,
  updateGoalMilestonesCompletionInDateDetail,
} from "@/calendar/calendarUpdates";
import { DEFAULT_USER_SETTINGS } from "@/config/defaultUserSettings";
import { useCalendarStore, type CalendarMode } from "@/store/calendarStore";
import type { AuthLanguage } from "@/types/auth";
import { getTodayDateKey, getWeekStartDate, parseDateKey } from "@/utils/date";
import { getUserFacingErrorMessage } from "@/utils/errorMessages";

export type RequestState = {
  isLoading: boolean;
  message: string | null;
  notice: string | null;
};

const PREFETCH_MONTHS_BACK = 3;
const PREFETCH_MONTHS_FORWARD = 9;
const PREFETCH_CONCURRENCY = 2;

function getCalendarCacheKey(mode: CalendarMode, visibleDate: string, weekStartsOn: 0 | 1) {
  const visible = parseDateKey(visibleDate);
  if (mode === "month") {
    return `month:${visible.getFullYear()}-${String(visible.getMonth() + 1).padStart(2, "0")}`;
  }
  return `week:${getWeekStartDate(visibleDate, weekStartsOn)}`;
}

function getMonthCacheKey(year: number, month: number) {
  return `month:${year}-${String(month).padStart(2, "0")}`;
}

function addMonthsFromMonthStart(value: Date, offset: number) {
  return new Date(value.getFullYear(), value.getMonth() + offset, 1);
}

function getCalendarPrefetchTargets(baseDateKey: string) {
  const baseDate = parseDateKey(baseDateKey);
  const offsets = [0];
  for (let distance = 1; distance <= PREFETCH_MONTHS_FORWARD; distance += 1) {
    if (distance <= PREFETCH_MONTHS_BACK) {
      offsets.push(-distance);
    }
    offsets.push(distance);
  }

  return offsets.map((offset) => {
    const targetDate = addMonthsFromMonthStart(baseDate, offset);
    return {
      year: targetDate.getFullYear(),
      month: targetDate.getMonth() + 1,
    };
  });
}

function buildDateDetailFromCalendar(date: string, calendar: CalendarData | null): CalendarDateData | null {
  const day = calendar?.days.find((item) => item.date === date);
  if (!day) {
    return null;
  }
  return {
    date: day.date,
    is_today: day.is_today,
    goal_count: day.goal_count,
    milestone_count: day.milestone_count,
    completed_milestone_count: day.completed_milestone_count,
    goals: day.goals,
    milestones: day.milestones,
  };
}

function cacheCalendarMonth(
  calendarCache: Map<string, CalendarData>,
  dateDetailCache: Map<string, CalendarDateData>,
  calendar: Extract<CalendarData, { month: number }>,
) {
  calendarCache.set(getMonthCacheKey(calendar.year, calendar.month), calendar);
  for (const day of calendar.days) {
    dateDetailCache.set(day.date, {
      date: day.date,
      is_today: day.is_today,
      goal_count: day.goal_count,
      milestone_count: day.milestone_count,
      completed_milestone_count: day.completed_milestone_count,
      goals: day.goals,
      milestones: day.milestones,
    });
  }
}

type CalendarDataOptions = {
  mode: CalendarMode;
  selectedDate: string;
  visibleDate: string;
  weekStartsOn: 0 | 1;
  authLanguage: AuthLanguage;
  isAuthenticated: boolean;
  setIsAuthenticated: Dispatch<SetStateAction<boolean>>;
  setRequestState: Dispatch<SetStateAction<RequestState>>;
  todaySidePanelEnabled: boolean;
  isManualCreateOpen: boolean;
  onTodayViewReset: () => void;
};

export function useCalendarData({
  mode, selectedDate, visibleDate, weekStartsOn, authLanguage, isAuthenticated,
  setIsAuthenticated, setRequestState, todaySidePanelEnabled, isManualCreateOpen, onTodayViewReset,
}: CalendarDataOptions) {
  const { setMode, setVisibleDate, setWeekStartsOn } = useCalendarStore.getState();
  const [calendarData, setCalendarData] = useState<CalendarData | null>(null);
  const [dateDetail, setDateDetail] = useState<CalendarDateData | null>(null);
  const [todayDetail, setTodayDetail] = useState<CalendarDateData | null>(null);
  const [todayRequest, setTodayRequest] = useState({ isLoading: false, error: null as string | null });
  const [pendingMilestoneIds, setPendingMilestoneIds] = useState<ReadonlySet<string>>(new Set());
  const [milestoneCompletions, setMilestoneCompletions] = useState<Record<string, boolean>>({});
  const pendingMilestonesRef = useRef(new Map<string, string | null>());
  const pendingGoalMutationsRef = useRef(0);
  const mutationRevisionRef = useRef(0);
  const milestoneGoalIdsRef = useRef(new Map<string, string>());
  const reloadCurrentViewRef = useRef<() => void>(() => undefined);
  const sessionRevisionRef = useRef(0);
  const todaySequenceRef = useRef(0);
  const dateRevisionRef = useRef(0);
  const dateRefreshPendingRef = useRef(false);
  const [dateRefreshRevision, setDateRefreshRevision] = useState(0);
  const [allGoals, setAllGoals] = useState<Goal[]>([]);
  const [userSettings, setUserSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [hasAppliedInitialSettings, setHasAppliedInitialSettings] = useState(false);
  const calendarCacheRef = useRef(new Map<string, CalendarData>());
  const dateDetailCacheRef = useRef(new Map<string, CalendarDateData>());
  const settingsCacheRef = useRef<UserSettings | null>(null);
  const requestSequenceRef = useRef(0);
  const prefetchRunRef = useRef(0);
  const hasStartedLoginPrefetchRef = useRef(false);
  const currentViewRef = useRef({ mode, selectedDate, visibleDate, weekStartsOn });

  currentViewRef.current = { mode, selectedDate, visibleDate, weekStartsOn };

  const resetCalendarCache = useCallback(() => {
    prefetchRunRef.current += 1;
    hasStartedLoginPrefetchRef.current = false;
    calendarCacheRef.current.clear();
    dateDetailCacheRef.current.clear();
    settingsCacheRef.current = null;
  }, []);

  function storeUserSettings(settings: UserSettings) {
    setUserSettings(settings);
    settingsCacheRef.current = settings;
  }

  function findCachedMilestone(id: string) {
    return Array.from(dateDetailCacheRef.current.values()).flatMap((day) => day.milestones).find((milestone) => milestone.id === id);
  }

  const [todayKey, setTodayKey] = useState(() => getTodayDateKey(userSettings.timezone));
  const todayKeyRef = useRef(todayKey);
  useEffect(() => {
    const updateToday = (refresh = false) => {
      const nextToday = getTodayDateKey(userSettings.timezone);
      const previousToday = todayKeyRef.current;
      if (nextToday === previousToday && !refresh) return;

      // Invalidate reads, not mutations: a sleeping window may resume with old responses pending.
      dateRevisionRef.current += 1;
      requestSequenceRef.current += 1;
      todaySequenceRef.current += 1;
      prefetchRunRef.current += 1;
      hasStartedLoginPrefetchRef.current = false;
      calendarCacheRef.current.clear();
      dateDetailCacheRef.current.clear();
      dateRefreshPendingRef.current = true;
      if (nextToday !== previousToday) {
        todayKeyRef.current = nextToday;
        const view = useCalendarStore.getState();
        if (view.selectedDate === previousToday) {
          view.selectDate(nextToday);
          if (getCalendarCacheKey(view.mode, view.visibleDate, view.weekStartsOn)
            === getCalendarCacheKey(view.mode, previousToday, view.weekStartsOn)) {
            view.setVisibleDate(view.mode === "week" ? getWeekStartDate(nextToday, view.weekStartsOn) : nextToday);
          }
        }
        setTodayKey(nextToday);
      }
      setDateRefreshRevision((revision) => revision + 1);
    };
    const handleResume = () => updateToday(true);
    const handleVisibility = () => {
      if (document.visibilityState === "visible") handleResume();
    };
    updateToday();
    const timer = window.setInterval(() => updateToday(), 1000);
    window.addEventListener("focus", handleResume);
    window.addEventListener("online", handleResume);
    document.addEventListener("visibilitychange", handleVisibility);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", handleResume);
      window.removeEventListener("online", handleResume);
      document.removeEventListener("visibilitychange", handleVisibility);
    };
  }, [userSettings.timezone]);

  useEffect(() => {
    if (isAuthenticated) return;
    sessionRevisionRef.current += 1;
    requestSequenceRef.current += 1;
    todaySequenceRef.current += 1;
    resetCalendarCache();
    pendingMilestonesRef.current.clear();
    pendingGoalMutationsRef.current = 0;
    setPendingMilestoneIds(new Set());
    setMilestoneCompletions({});
    milestoneGoalIdsRef.current.clear();
    setTodayDetail(null);
    setCalendarData(null);
    setDateDetail(null);
    setAllGoals([]);
    setTodayRequest({ isLoading: false, error: null });
  }, [isAuthenticated, resetCalendarCache]);
  const applySettingsToCalendar = useCallback(
    (settings: UserSettings) => {
      setWeekStartsOn(settings.week_starts_on);
      setMode(settings.calendar_view);
      setVisibleDate(
        settings.calendar_view === "week"
          ? getWeekStartDate(selectedDate, settings.week_starts_on)
          : selectedDate,
      );
    },
    [selectedDate, setMode, setVisibleDate, setWeekStartsOn],
  );

  const updateCachedCalendars = useCallback((updater: (calendar: CalendarData) => CalendarData) => {
    calendarCacheRef.current = new Map(
      Array.from(calendarCacheRef.current.entries()).map(([key, value]) => [key, updater(value)]),
    );
    setCalendarData((current) => (current ? updater(current) : current));
  }, []);

  const updateCachedDateDetails = useCallback((updater: (detail: CalendarDateData) => CalendarDateData) => {
    dateDetailCacheRef.current = new Map(
      Array.from(dateDetailCacheRef.current.entries()).map(([key, value]) => [key, updater(value)]),
    );
    setDateDetail((current) => (current ? updater(current) : current));
    setTodayDetail((current) => (current ? updater(current) : current));
  }, []);

  const prefetchCalendarMonths = useCallback((baseDateKey: string) => {
    const runId = ++prefetchRunRef.current;
    const targets = getCalendarPrefetchTargets(baseDateKey).filter(
      (target) => !calendarCacheRef.current.has(getMonthCacheKey(target.year, target.month)),
    );
    let nextTargetIndex = 0;

    async function worker() {
      while (nextTargetIndex < targets.length && prefetchRunRef.current === runId) {
        const target = targets[nextTargetIndex];
        nextTargetIndex += 1;

        if (calendarCacheRef.current.has(getMonthCacheKey(target.year, target.month))) {
          continue;
        }

        try {
          const revision = mutationRevisionRef.current;
          const month = await apiClient.getMonthCalendar(target.year, target.month);
          if (prefetchRunRef.current !== runId || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0) {
            return;
          }
          cacheCalendarMonth(calendarCacheRef.current, dateDetailCacheRef.current, toCalendarMonthView(month));
        } catch {
          // Prefetch is opportunistic; visible calendar requests still surface errors.
        }
      }
    }

    window.setTimeout(() => {
      void Promise.all(
        Array.from({ length: Math.min(PREFETCH_CONCURRENCY, targets.length) }, () => worker()),
      );
    }, 0);
  }, []);

  const loadCalendar = useCallback(async (options: { force?: boolean; quiet?: boolean } = {}) => {
    if (!isAuthenticated) {
      return;
    }
    const { force = false, quiet = false } = options;
    const revision = mutationRevisionRef.current;
    const session = sessionRevisionRef.current;
    const dateRevision = dateRevisionRef.current;
    const requestSequence = requestSequenceRef.current + 1;
    requestSequenceRef.current = requestSequence;
    const calendarCacheKey = getCalendarCacheKey(mode, visibleDate, weekStartsOn);
    const cachedCalendar = calendarCacheRef.current.get(calendarCacheKey) ?? null;
    const cachedDetail = dateDetailCacheRef.current.get(selectedDate) ?? buildDateDetailFromCalendar(selectedDate, cachedCalendar);

    if (!force) {
      if (cachedCalendar) {
        setCalendarData(cachedCalendar);
      }
      if (cachedDetail) {
        setDateDetail(cachedDetail);
      }
    }
    if (!quiet) {
      setRequestState({
        isLoading: !cachedCalendar || !cachedDetail,
        message: null,
        notice: null,
      });
    }
    try {
      const visible = parseDateKey(visibleDate);
      const settingsPromise = settingsCacheRef.current
        ? Promise.resolve(settingsCacheRef.current)
        : apiClient.getSettings();
      const calendarPromise =
        !force && cachedCalendar
          ? Promise.resolve(cachedCalendar)
          : mode === "month"
            ? apiClient.getMonthCalendar(visible.getFullYear(), visible.getMonth() + 1).then(toCalendarMonthView)
            : apiClient.getWeekCalendar(getWeekStartDate(visibleDate, weekStartsOn));

      const [settings, calendar] = await Promise.all([settingsPromise, calendarPromise]);
      const isCurrentView =
        currentViewRef.current.mode === mode &&
        currentViewRef.current.selectedDate === selectedDate &&
        currentViewRef.current.visibleDate === visibleDate &&
        currentViewRef.current.weekStartsOn === weekStartsOn;
      if (session !== sessionRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0 || requestSequence !== requestSequenceRef.current || !isCurrentView) {
        return;
      }
      settingsCacheRef.current = settings;
      if ("month" in calendar) {
        cacheCalendarMonth(calendarCacheRef.current, dateDetailCacheRef.current, calendar);
      } else {
        calendarCacheRef.current.set(calendarCacheKey, calendar);
      }
      setCalendarData(calendar);
      setMilestoneCompletions((current) => {
        const next = { ...current };
        for (const milestone of calendar.milestones) {
          milestoneGoalIdsRef.current.set(milestone.id, milestone.goal_id);
          if (milestone.id in next) next[milestone.id] = milestone.is_completed;
        }
        return next;
      });

      let detail =
        !force && cachedDetail
          ? cachedDetail
          : buildDateDetailFromCalendar(selectedDate, calendar);
      if (!detail) {
        detail = await apiClient.getDateCalendar(selectedDate);
        const isStillCurrentView =
          currentViewRef.current.mode === mode &&
          currentViewRef.current.selectedDate === selectedDate &&
          currentViewRef.current.visibleDate === visibleDate &&
          currentViewRef.current.weekStartsOn === weekStartsOn;
        if (session !== sessionRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0 || requestSequence !== requestSequenceRef.current || !isStillCurrentView) {
          return;
        }
      }
      dateDetailCacheRef.current.set(selectedDate, detail);
      setDateDetail(detail);

      setUserSettings(settings);
      if (!hasAppliedInitialSettings) {
        applySettingsToCalendar(settings);
        setHasAppliedInitialSettings(true);
      }
      void apiClient.listGoals().then((goals) => {
        if (session !== sessionRevisionRef.current || dateRevision !== dateRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0) return;
        setAllGoals(goals);
        for (const goal of goals) {
          updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
          updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
        }
      }).catch((error) => {
        if (session === sessionRevisionRef.current && dateRevision === dateRevisionRef.current && revision === mutationRevisionRef.current) {
          setRequestState((current) => ({ ...current, message: getUserFacingErrorMessage(error, userSettings.language) }));
        }
      });
      if (!quiet) {
        setRequestState({ isLoading: false, message: null, notice: null });
      }
      if (!quiet && !hasStartedLoginPrefetchRef.current) {
        hasStartedLoginPrefetchRef.current = true;
        prefetchCalendarMonths(todayKey);
      }
    } catch (error) {
      const isCurrentView =
        currentViewRef.current.mode === mode &&
        currentViewRef.current.selectedDate === selectedDate &&
        currentViewRef.current.visibleDate === visibleDate &&
        currentViewRef.current.weekStartsOn === weekStartsOn;
      if (session !== sessionRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0 || requestSequence !== requestSequenceRef.current || !isCurrentView) {
        return;
      }
      if (error instanceof ApiClientError && error.status === 401) {
        apiClient.setAccessToken(null);
        void apiClient.persistAccessToken(null);
        setIsAuthenticated(false);
        prefetchRunRef.current += 1;
        hasStartedLoginPrefetchRef.current = false;
      }
      if (!quiet) {
        setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, authLanguage), notice: null });
      }
    }
  }, [
    applySettingsToCalendar,
    authLanguage,
    hasAppliedInitialSettings,
    isAuthenticated,
    mode,
    prefetchCalendarMonths,
    selectedDate,
    todayKey,
    visibleDate,
    weekStartsOn,
    updateCachedCalendars,
    updateCachedDateDetails,
    userSettings.language,
    setIsAuthenticated,
    setRequestState,
  ]);

  const loadToday = useCallback(async (force = false) => {
    if (!isAuthenticated || !hasAppliedInitialSettings || !todaySidePanelEnabled) return;
    const sequence = ++todaySequenceRef.current;
    const session = sessionRevisionRef.current;
    const revision = mutationRevisionRef.current;
    const cached = dateDetailCacheRef.current.get(todayKey);
    if (cached && !force) {
      setTodayDetail(cached);
      setTodayRequest({ isLoading: false, error: null });
      return;
    }
    setTodayRequest({ isLoading: true, error: null });
    try {
      const detail = await apiClient.getDateCalendar(todayKey);
      if (sequence !== todaySequenceRef.current || session !== sessionRevisionRef.current) return;
      if (revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0) {
        setTodayDetail(dateDetailCacheRef.current.get(todayKey) ?? null);
        setTodayRequest({ isLoading: false, error: null });
        return;
      }
      dateDetailCacheRef.current.set(todayKey, detail);
      setMilestoneCompletions((current) => {
        const next = { ...current };
        for (const milestone of detail.milestones) {
          milestoneGoalIdsRef.current.set(milestone.id, milestone.goal_id);
          if (milestone.id in next) next[milestone.id] = milestone.is_completed;
        }
        return next;
      });
      setTodayDetail(detail);
      setTodayRequest({ isLoading: false, error: null });
    } catch (error) {
      if (sequence === todaySequenceRef.current && session === sessionRevisionRef.current) {
        setTodayRequest({ isLoading: false, error: getUserFacingErrorMessage(error, userSettings.language) });
      }
    }
  }, [isAuthenticated, hasAppliedInitialSettings, todaySidePanelEnabled, todayKey, userSettings.language]);

  useEffect(() => {
    setTodayDetail(null);
    onTodayViewReset();
    return () => { todaySequenceRef.current += 1; };
  }, [loadToday, onTodayViewReset]);

  reloadCurrentViewRef.current = () => {
    if (pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0) return;
    if (dateRefreshPendingRef.current) {
      setDateRefreshRevision((revision) => revision + 1);
      return;
    }
    void loadCalendar({ quiet: true });
    void loadToday();
  };

  const refreshCalendarInBackground = useCallback(() => {
    setTimeout(() => {
      void loadCalendar({ force: true, quiet: true });
      void loadToday(true);
    }, 0);
  }, [loadCalendar, loadToday]);

  useEffect(() => {
    if (pendingMilestonesRef.current.size > 0 || pendingGoalMutationsRef.current > 0) return;
    const force = dateRefreshPendingRef.current;
    dateRefreshPendingRef.current = false;
    void loadCalendar({ force });
    void loadToday(force);
  }, [loadCalendar, loadToday, dateRefreshRevision]);

  useEffect(() => {
    if (isManualCreateOpen) {
      const session = sessionRevisionRef.current;
      const revision = mutationRevisionRef.current;
      const dateRevision = dateRevisionRef.current;
      void apiClient.listGoals().then((goals) => {
        if (session === sessionRevisionRef.current && dateRevision === dateRevisionRef.current && revision === mutationRevisionRef.current) setAllGoals(goals);
      }).catch(() => undefined);
    }
  }, [isManualCreateOpen]);

  function trackCalendarMutation() {
    const session = sessionRevisionRef.current;
    return {
      isCurrent: () => session === sessionRevisionRef.current,
      recordChange: () => { mutationRevisionRef.current += 1; },
    };
  }

  function prepareCalendarLogin() {
    setHasAppliedInitialSettings(false);
    resetCalendarCache();
  }

  function clearCalendarView() {
    setCalendarData(null);
    setDateDetail(null);
    setUserSettings(DEFAULT_USER_SETTINGS);
    resetCalendarCache();
    setHasAppliedInitialSettings(false);
  }

  function invalidateCalendarSession() {
    sessionRevisionRef.current += 1;
  }

  function findMilestoneGoalId(milestoneId: string): string | null {
    const dateDetailMilestone = dateDetail?.milestones.find((milestone) => milestone.id === milestoneId);
    if (dateDetailMilestone) {
      return dateDetailMilestone.goal_id;
    }
    const calendarMilestone = calendarData?.milestones.find((milestone) => milestone.id === milestoneId)
      ?? calendarData?.days.flatMap((day) => day.milestones).find((milestone) => milestone.id === milestoneId);
    return calendarMilestone?.goal_id ?? todayDetail?.milestones.find((milestone) => milestone.id === milestoneId)?.goal_id ?? null;
  }

  function applyGoalCompletion(goalId: string, isCompleted: boolean) {
    setAllGoals((current) => current.map((goal) => (
      goal.id === goalId ? { ...goal, is_completed: isCompleted } : goal
    )));
    updateCachedCalendars((calendar) => updateGoalCompletionInCalendar(calendar, goalId, isCompleted));
    updateCachedDateDetails((detail) => updateGoalCompletionInDateDetail(detail, goalId, isCompleted));
  }

  function applyGoalAndMilestonesCompletion(goalId: string, isCompleted: boolean) {
    applyGoalCompletion(goalId, isCompleted);
    updateCachedCalendars((calendar) => updateGoalMilestonesCompletionInCalendar(calendar, goalId, isCompleted));
    updateCachedDateDetails((detail) => updateGoalMilestonesCompletionInDateDetail(detail, goalId, isCompleted));
  }

  async function handleToggleGoal(goalId: string, isCompleted: boolean) {
    const session = sessionRevisionRef.current;
    if (Array.from(pendingMilestonesRef.current.values()).includes(goalId)) throw new Error("Milestones are being saved.");
    pendingGoalMutationsRef.current += 1;
    mutationRevisionRef.current += 1;
    setMilestoneCompletions((current) => Object.fromEntries(Object.entries(current).filter(([id]) => milestoneGoalIdsRef.current.get(id) !== goalId)));
    applyGoalAndMilestonesCompletion(goalId, isCompleted);
    setRequestState({ isLoading: false, message: null, notice: null });
    try {
      const goal = await apiClient.completeGoal(goalId, isCompleted);
      if (session !== sessionRevisionRef.current) return;
      mutationRevisionRef.current += 1;
      setAllGoals((current) => current.map((item) => (item.id === goal.id ? { ...item, ...goal } : item)));
      updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
      updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      applyGoalAndMilestonesCompletion(goalId, !isCompleted);
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
      throw error;
    } finally {
      if (session === sessionRevisionRef.current) {
        pendingGoalMutationsRef.current -= 1;
        mutationRevisionRef.current += 1;
        reloadCurrentViewRef.current();
      }
    }
  }

  async function handleToggleMilestone(milestoneId: string, isCompleted: boolean, source?: Milestone) {
    if (pendingMilestonesRef.current.has(milestoneId)) throw new Error("Milestone is being saved.");
    const session = sessionRevisionRef.current;
    const goalId = source?.goal_id ?? findMilestoneGoalId(milestoneId);
    if (goalId) milestoneGoalIdsRef.current.set(milestoneId, goalId);
    const previous = source ?? todayDetail?.milestones.find((m) => m.id === milestoneId)
      ?? dateDetail?.milestones.find((m) => m.id === milestoneId)
      ?? calendarData?.milestones.find((m) => m.id === milestoneId)
      ?? findCachedMilestone(milestoneId);
    const previousCompleted = previous?.is_completed ?? !isCompleted;
    pendingMilestonesRef.current.set(milestoneId, goalId);
    setPendingMilestoneIds(new Set(pendingMilestonesRef.current.keys()));
    mutationRevisionRef.current += 1;
    const applyCompletion = (completed: boolean) => {
      setMilestoneCompletions((current) => ({ ...current, [milestoneId]: completed }));
      const update = <T extends { id: string; is_completed: boolean },>(item: T): T =>
        item.id === milestoneId ? { ...item, is_completed: completed } : item;
      updateCachedCalendars((calendar) => ({
        ...calendar, milestones: calendar.milestones.map(update),
        days: calendar.days.map((day) => {
          const milestones = day.milestones.map(update);
          return { ...day, milestones, completed_milestone_count: countCompletedMilestones(milestones) };
        }),
      }));
      updateCachedDateDetails((detail) => {
        const milestones = detail.milestones.map(update);
        return { ...detail, milestones, completed_milestone_count: countCompletedMilestones(milestones) };
      });
    };
    // Goal completion is authoritative on the server; today's subset cannot prove it.
    applyCompletion(isCompleted);
    setRequestState({ isLoading: false, message: null, notice: null });
    try {
      const milestone = await apiClient.completeMilestone(milestoneId, isCompleted);
      if (session !== sessionRevisionRef.current) return;
      applyCompletion(milestone.is_completed);
      updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
      updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      applyCompletion(previousCompleted);
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
      throw error;
    } finally {
      if (session === sessionRevisionRef.current) {
        pendingMilestonesRef.current.delete(milestoneId);
        setPendingMilestoneIds(new Set(pendingMilestonesRef.current.keys()));
        mutationRevisionRef.current += 1;
        if (pendingMilestonesRef.current.size === 0) reloadCurrentViewRef.current();
      }
    }
  }

  return {
    allGoals,
    applySettingsToCalendar,
    calendarData,
    clearCalendarView,
    dateDetail,
    handleToggleGoal,
    handleToggleMilestone,
    hasAppliedInitialSettings,
    invalidateCalendarSession,
    loadToday,
    milestoneCompletions,
    pendingMilestoneIds,
    prepareCalendarLogin,
    refreshCalendarInBackground,
    setAllGoals,
    storeUserSettings,
    todayDetail,
    todayKey,
    todayRequest,
    trackCalendarMutation,
    updateCachedCalendars,
    updateCachedDateDetails,
    userSettings,
  };
}
