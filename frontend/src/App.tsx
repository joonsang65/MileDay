import { type PointerEvent as ReactPointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ApiClientError, apiClient } from "@/api/client";
import type {
  CalendarDateData,
  CalendarMonthData,
  CalendarWeekData,
  Goal,
  GoalCreatePayload,
  AiScheduleDraft,
  AiScheduleDraftRequest,
  GoalUpdatePayload,
  Milestone,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  UserSettings,
  UserSettingsUpdatePayload,
} from "@/api/types";
import { AuthPanel } from "@/components/AuthPanel";
import { AiSchedulePanel } from "@/components/AiSchedulePanel";
import { CalendarBoard } from "@/components/CalendarBoard";
import { CalendarHeader } from "@/components/CalendarHeader";
import { DateDetail, dateDetailLabels } from "@/components/DateDetail";
import { FloatingPanel } from "@/components/FloatingPanel";
import { ManualCreatePanel } from "@/components/ManualCreatePanel";
import { QuickActionPopover } from "@/components/QuickActionPopover";
import { GoalListModal } from "@/components/GoalListModal";
import { TodaySidePanel } from "@/components/TodaySidePanel";
import { SettingsPanel } from "@/components/SettingsPanel";
import { DEFAULT_USER_SETTINGS } from "@/config/defaultUserSettings";
import { LAST_LOGIN_EMAIL_KEY } from "@/config/storageKeys";
import { useCalendarStore, type CalendarMode } from "@/store/calendarStore";
import { useUiStore } from "@/store/uiStore";
import type { AuthLanguage } from "@/types/auth";
import { DEFAULT_LOCAL_UI_SETTINGS, type LocalUiSettings, type LocalUiSettingsPatch } from "@/types/localUiSettings";
import { RESIZE_DIRECTIONS, type ResizeDirection } from "@/types/windowResize";
import { getInitialAuthLanguage } from "@/utils/authLanguage";
import {
  getTodayDateKey,
  getWeekStartDate,
  getMonthLabel,
  getWeekLabel,
  moveMonth,
  moveWeek,
  parseDateKey,
  toDateKey,
} from "@/utils/date";
import { getUserFacingErrorMessage } from "@/utils/errorMessages";

type RequestState = {
  isLoading: boolean;
  message: string | null;
  notice: string | null;
};

type CalendarData = CalendarMonthData | CalendarWeekData;

const PREFETCH_MONTHS_BACK = 3;
const PREFETCH_MONTHS_FORWARD = 9;
const PREFETCH_CONCURRENCY = 2;

const authMessages: Record<AuthLanguage, { checkingSession: string; signupComplete: string }> = {
  ko: {
    checkingSession: "로그인 상태를 확인하는 중입니다.",
    signupComplete: "회원가입이 완료되었습니다. 로그인해 주세요.",
  },
  en: {
    checkingSession: "Checking your login status.",
    signupComplete: "Sign up is complete. Please log in.",
  },
};

const appLabels = {
  ko: {
    closeMenu: "메뉴 닫기",
    settings: "설정",
    close: "닫기",
    credit: "앱 크레딧",
  },
  en: {
    closeMenu: "Close menu",
    settings: "Settings",
    close: "Close",
    credit: "App credit",
  },
};

function WindowResizeHandles({ enabled }: { enabled: boolean }) {
  const isDraggingRef = useRef(false);

  if (!enabled || !window.mileday?.windowResize) {
    return null;
  }

  function removeListeners() {
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", handlePointerUp);
    window.removeEventListener("pointercancel", handlePointerUp);
  }

  function handlePointerMove(event: PointerEvent) {
    if (!isDraggingRef.current) {
      return;
    }
    void window.mileday?.windowResize?.update({
      screenX: event.screenX,
      screenY: event.screenY,
    });
  }

  function handlePointerUp() {
    if (!isDraggingRef.current) {
      return;
    }
    isDraggingRef.current = false;
    removeListeners();
    void window.mileday?.windowResize?.end();
  }

  function handlePointerDown(direction: ResizeDirection, event: ReactPointerEvent<HTMLDivElement>) {
    if (event.button !== 0) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    isDraggingRef.current = true;
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    void window.mileday?.windowResize
      ?.start({
        direction,
        screenX: event.screenX,
        screenY: event.screenY,
      })
      .then((started) => {
        if (!started) {
          handlePointerUp();
        }
      })
      .catch(() => handlePointerUp());
  }

  return (
    <div className="window-resize-layer" aria-hidden="true">
      {RESIZE_DIRECTIONS.map((direction) => (
        <div
          key={direction}
          className={`window-resize-handle ${direction}`}
          onPointerDown={(event) => handlePointerDown(direction, event)}
        />
      ))}
    </div>
  );
}

function useWindowMoveDrag() {
  const isDraggingRef = useRef(false);

  function removeListeners() {
    window.removeEventListener("pointermove", handlePointerMove);
    window.removeEventListener("pointerup", handlePointerUp);
    window.removeEventListener("pointercancel", handlePointerUp);
  }

  function handlePointerMove(event: PointerEvent) {
    if (!isDraggingRef.current) {
      return;
    }
    void window.mileday?.windowMove?.update({
      screenX: event.screenX,
      screenY: event.screenY,
    });
  }

  function handlePointerUp() {
    if (!isDraggingRef.current) {
      return;
    }
    isDraggingRef.current = false;
    removeListeners();
    void window.mileday?.windowMove?.end();
  }

  return function handleWindowMoveStart(event: ReactPointerEvent<HTMLElement>) {
    if (event.button !== 0 || !window.mileday?.windowMove) {
      return;
    }

    const target = event.target;
    if (target instanceof Element && target.closest("button, input, select, textarea, a, [data-no-window-drag]")) {
      return;
    }

    event.preventDefault();
    event.stopPropagation();
    isDraggingRef.current = true;
    window.addEventListener("pointermove", handlePointerMove);
    window.addEventListener("pointerup", handlePointerUp);
    window.addEventListener("pointercancel", handlePointerUp);

    void window.mileday.windowMove
      .start({
        screenX: event.screenX,
        screenY: event.screenY,
      })
      .then((started) => {
        if (!started) {
          handlePointerUp();
        }
      })
      .catch(() => handlePointerUp());
  };
}

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
  calendar: CalendarMonthData,
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

function countCompletedMilestones(milestones: { is_completed: boolean }[]) {
  return milestones.filter((milestone) => milestone.is_completed).length;
}

function upsertMilestoneList(milestones: Milestone[], milestone: Milestone): Milestone[] {
  return milestones.some((item) => item.id === milestone.id)
    ? milestones.map((item) => item.id === milestone.id ? milestone : item)
    : [...milestones, milestone];
}

function upsertGoalInCalendar(calendar: CalendarData, goal: Goal): CalendarData {
  return {
    ...calendar,
    goals: [...calendar.goals.filter((item) => item.id !== goal.id), goal],
    milestones: calendar.milestones.map((m) =>
      m.goal_id === goal.id ? { ...m, goal_title: goal.title } : m,
    ),
    days: calendar.days.map((day) => {
      const goals = day.goals.filter((item) => item.id !== goal.id);
      if (day.date === goal.deadline) {
        goals.push(goal);
      }
      const milestones = day.milestones.map((m) =>
        m.goal_id === goal.id ? { ...m, goal_title: goal.title } : m,
      );
      return {
        ...day,
        goals,
        milestones,
        goal_count: goals.length,
      };
    }),
  };
}

function upsertGoalInDateDetail(detail: CalendarDateData, goal: Goal): CalendarDateData {
  const goals = detail.goals.filter((item) => item.id !== goal.id);
  if (detail.date === goal.deadline) {
    goals.push(goal);
  }
  const milestones = detail.milestones.map((m) =>
    m.goal_id === goal.id ? { ...m, goal_title: goal.title } : m,
  );
  return {
    ...detail,
    goals,
    milestones,
    goal_count: goals.length,
  };
}

function upsertMilestoneInCalendar(calendar: CalendarData, milestone: Milestone): CalendarData {
  const existing = calendar.milestones.find((item) => item.id === milestone.id);
  const milestoneToUpsert = existing && milestone.goal_title == null
    ? { ...milestone, goal_title: existing.goal_title }
    : milestone;

  return {
    ...calendar,
    milestones: upsertMilestoneList(calendar.milestones, milestoneToUpsert),
    days: calendar.days.map((day) => {
      const milestones = day.date === milestoneToUpsert.scheduled_date
        ? upsertMilestoneList(day.milestones, milestoneToUpsert)
        : day.milestones.filter((item) => item.id !== milestoneToUpsert.id);
      return {
        ...day,
        milestones,
        milestone_count: milestones.length,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

function upsertMilestoneInDateDetail(detail: CalendarDateData, milestone: Milestone): CalendarDateData {
  const existing = detail.milestones.find((item) => item.id === milestone.id);
  const milestoneToUpsert = existing && milestone.goal_title == null
    ? { ...milestone, goal_title: existing.goal_title }
    : milestone;

  const milestones = detail.date === milestoneToUpsert.scheduled_date
    ? upsertMilestoneList(detail.milestones, milestoneToUpsert)
    : detail.milestones.filter((item) => item.id !== milestoneToUpsert.id);
  return {
    ...detail,
    milestones,
    milestone_count: milestones.length,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}

function removeGoalFromCalendar(calendar: CalendarData, goalId: string): CalendarData {
  return {
    ...calendar,
    goals: calendar.goals.filter((goal) => goal.id !== goalId),
    milestones: calendar.milestones.filter((milestone) => milestone.goal_id !== goalId),
    days: calendar.days.map((day) => {
      const goals = day.goals.filter((goal) => goal.id !== goalId);
      const milestones = day.milestones.filter((milestone) => milestone.goal_id !== goalId);
      return {
        ...day,
        goals,
        milestones,
        goal_count: goals.length,
        milestone_count: milestones.length,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

function removeGoalFromDateDetail(detail: CalendarDateData, goalId: string): CalendarDateData {
  const goals = detail.goals.filter((goal) => goal.id !== goalId);
  const milestones = detail.milestones.filter((milestone) => milestone.goal_id !== goalId);
  return {
    ...detail,
    goals,
    milestones,
    goal_count: goals.length,
    milestone_count: milestones.length,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}

function removeMilestoneFromCalendar(calendar: CalendarData, milestoneId: string): CalendarData {
  return {
    ...calendar,
    milestones: calendar.milestones.filter((milestone) => milestone.id !== milestoneId),
    days: calendar.days.map((day) => {
      const milestones = day.milestones.filter((milestone) => milestone.id !== milestoneId);
      return {
        ...day,
        milestones,
        milestone_count: milestones.length,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

function removeMilestoneFromDateDetail(detail: CalendarDateData, milestoneId: string): CalendarDateData {
  const milestones = detail.milestones.filter((milestone) => milestone.id !== milestoneId);
  return {
    ...detail,
    milestones,
    milestone_count: milestones.length,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}

function updateGoalCompletionInCalendar(calendar: CalendarData, goalId: string, isCompleted: boolean): CalendarData {
  const updateGoal = (goal: Goal): Goal => (
    goal.id === goalId ? { ...goal, is_completed: isCompleted } : goal
  );
  return {
    ...calendar,
    goals: calendar.goals.map(updateGoal),
    days: calendar.days.map((day) => ({
      ...day,
      goals: day.goals.map(updateGoal),
    })),
  };
}

function updateGoalCompletionInDateDetail(detail: CalendarDateData, goalId: string, isCompleted: boolean): CalendarDateData {
  return {
    ...detail,
    goals: detail.goals.map((goal) => (
      goal.id === goalId ? { ...goal, is_completed: isCompleted } : goal
    )),
  };
}

function updateGoalMilestonesCompletionInCalendar(calendar: CalendarData, goalId: string, isCompleted: boolean): CalendarData {
  const updateMilestone = (milestone: Milestone): Milestone => (
    milestone.goal_id === goalId ? { ...milestone, is_completed: isCompleted } : milestone
  );
  return {
    ...calendar,
    milestones: calendar.milestones.map(updateMilestone),
    days: calendar.days.map((day) => {
      const milestones = day.milestones.map(updateMilestone);
      return {
        ...day,
        milestones,
        completed_milestone_count: countCompletedMilestones(milestones),
      };
    }),
  };
}

function updateGoalMilestonesCompletionInDateDetail(detail: CalendarDateData, goalId: string, isCompleted: boolean): CalendarDateData {
  const milestones = detail.milestones.map((milestone) => (
    milestone.goal_id === goalId ? { ...milestone, is_completed: isCompleted } : milestone
  ));
  return {
    ...detail,
    milestones,
    completed_milestone_count: countCompletedMilestones(milestones),
  };
}

export default function App() {
  const {
    mode,
    selectedDate,
    visibleDate,
    weekStartsOn,
    setMode,
    setWeekStartsOn,
    selectDate,
    setVisibleDate,
  } = useCalendarStore();
  const [hasCheckedStoredAuth, setHasCheckedStoredAuth] = useState(apiClient.hasAccessToken());
  const [isAuthenticated, setIsAuthenticated] = useState(apiClient.hasAccessToken());
  const [authLanguage, setAuthLanguage] = useState<AuthLanguage>(() => getInitialAuthLanguage());
  const [requestState, setRequestState] = useState<RequestState>({
    isLoading: false,
    message: null,
    notice: null,
  });
  const [calendarData, setCalendarData] = useState<CalendarMonthData | CalendarWeekData | null>(
    null,
  );
  const [dateDetail, setDateDetail] = useState<CalendarDateData | null>(null);
  const [todayDetail, setTodayDetail] = useState<CalendarDateData | null>(null);
  const [todayRequest, setTodayRequest] = useState({ isLoading: false, error: null as string | null });
  const [sidePanelOpen, setSidePanelOpen] = useState(true);
  const [pendingMilestoneIds, setPendingMilestoneIds] = useState<ReadonlySet<string>>(new Set());
  const [milestoneCompletions, setMilestoneCompletions] = useState<Record<string, boolean>>({});
  const pendingMilestonesRef = useRef(new Map<string, string | null>());
  const mutationRevisionRef = useRef(0);
  const milestoneGoalIdsRef = useRef(new Map<string, string>());
  const reloadCurrentViewRef = useRef<() => void>(() => undefined);
  const sessionRevisionRef = useRef(0);
  const todaySequenceRef = useRef(0);
  const [allGoals, setAllGoals] = useState<Goal[]>([]);
  const [userSettings, setUserSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [localUiSettings, setLocalUiSettings] = useState<LocalUiSettings>(DEFAULT_LOCAL_UI_SETTINGS);
  const [hasAppliedInitialSettings, setHasAppliedInitialSettings] = useState(false);
  const [isDateDetailEditing, setIsDateDetailEditing] = useState(false);
  const [isDayViewQuickMenuOpen, setIsDayViewQuickMenuOpen] = useState(false);
  const calendarCacheRef = useRef(new Map<string, CalendarData>());
  const dateDetailCacheRef = useRef(new Map<string, CalendarDateData>());
  const settingsCacheRef = useRef<UserSettings | null>(null);
  const requestSequenceRef = useRef(0);
  const prefetchRunRef = useRef(0);
  const hasStartedLoginPrefetchRef = useRef(false);
  const currentViewRef = useRef({ mode, selectedDate, visibleDate, weekStartsOn });
  const { overlayMode, openManualCreate, openAiCreate, openSettings, openDayView, openGoalList, closeOverlay } = useUiStore();
  const handleWindowMoveStart = useWindowMoveDrag();

  currentViewRef.current = { mode, selectedDate, visibleDate, weekStartsOn };

  useEffect(() => {
    document.documentElement.style.setProperty("--app-font-size", `${localUiSettings.baseFontSize}px`);
    document.documentElement.style.setProperty("--goal-font-size", `${localUiSettings.goalFontSize}px`);
    document.documentElement.dataset.settingsPanelSize = localUiSettings.settingsPanelSize;
  }, [localUiSettings.baseFontSize, localUiSettings.goalFontSize, localUiSettings.settingsPanelSize]);

  useEffect(() => {
    const keyboardFocusRequired = !isAuthenticated || overlayMode !== "none" || isDateDetailEditing;
    void window.mileday?.windowFocus?.setKeyboardFocusRequired(keyboardFocusRequired);
  }, [isAuthenticated, isDateDetailEditing, overlayMode]);

  useEffect(() => {
    let isMounted = true;
    void apiClient
      .loadStoredAccessToken()
      .then((hasToken) => {
        if (isMounted) {
          setIsAuthenticated(hasToken);
        }
      })
      .catch(() => {
        if (isMounted) {
          setIsAuthenticated(false);
        }
      })
      .finally(() => {
        if (isMounted) {
          setHasCheckedStoredAuth(true);
        }
      });
    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    let isMounted = true;
    void window.mileday?.uiSettings
      ?.get()
      .then((settings) => {
        if (isMounted) {
          setLocalUiSettings({ ...DEFAULT_LOCAL_UI_SETTINGS, ...settings });
        }
      })
      .catch(() => undefined);
    return () => {
      isMounted = false;
    };
  }, []);

  const headerLabel = useMemo(() => {
    if (mode === "month") {
      return getMonthLabel(parseDateKey(visibleDate), userSettings.language);
    }
    return getWeekLabel(parseDateKey(visibleDate), userSettings.language);
  }, [mode, userSettings.language, visibleDate]);

  const [todayKey, setTodayKey] = useState(() => getTodayDateKey(userSettings.timezone));
  useEffect(() => {
    const updateToday = () => setTodayKey(getTodayDateKey(userSettings.timezone));
    updateToday();
    const timer = window.setInterval(updateToday, 1000);
    window.addEventListener("focus", updateToday);
    document.addEventListener("visibilitychange", updateToday);
    return () => {
      window.clearInterval(timer);
      window.removeEventListener("focus", updateToday);
      document.removeEventListener("visibilitychange", updateToday);
    };
  }, [userSettings.timezone]);

  useEffect(() => {
    if (isAuthenticated) return;
    sessionRevisionRef.current += 1;
    requestSequenceRef.current += 1;
    todaySequenceRef.current += 1;
    prefetchRunRef.current += 1;
    hasStartedLoginPrefetchRef.current = false;
    calendarCacheRef.current.clear();
    dateDetailCacheRef.current.clear();
    settingsCacheRef.current = null;
    pendingMilestonesRef.current.clear();
    setPendingMilestoneIds(new Set());
    setMilestoneCompletions({});
    milestoneGoalIdsRef.current.clear();
    setTodayDetail(null);
    setCalendarData(null);
    setDateDetail(null);
    setAllGoals([]);
    setTodayRequest({ isLoading: false, error: null });
  }, [isAuthenticated]);
  const draftAvailability = useMemo<AiScheduleDraftRequest["availability"]>(() => {
    const sourceDates = (calendarData?.days ?? [])
      .map((day) => day.date)
      .filter((date) => date >= todayKey)
      .slice(0, 45);
    const dates = sourceDates.length > 0 ? sourceDates : [selectedDate >= todayKey ? selectedDate : todayKey];
    return Array.from(new Set(dates)).map((date) => ({
      date,
      available_minutes: 120,
    }));
  }, [calendarData?.days, selectedDate, todayKey]);

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
          const calendar = await apiClient.getMonthCalendar(target.year, target.month);
          if (prefetchRunRef.current !== runId || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0) {
            return;
          }
          cacheCalendarMonth(calendarCacheRef.current, dateDetailCacheRef.current, calendar);
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
            ? apiClient.getMonthCalendar(visible.getFullYear(), visible.getMonth() + 1)
            : apiClient.getWeekCalendar(getWeekStartDate(visibleDate, weekStartsOn));

      const [settings, calendar] = await Promise.all([settingsPromise, calendarPromise]);
      const isCurrentView =
        currentViewRef.current.mode === mode &&
        currentViewRef.current.selectedDate === selectedDate &&
        currentViewRef.current.visibleDate === visibleDate &&
        currentViewRef.current.weekStartsOn === weekStartsOn;
      if (session !== sessionRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || requestSequence !== requestSequenceRef.current || !isCurrentView) {
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
        if (session !== sessionRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || requestSequence !== requestSequenceRef.current || !isStillCurrentView) {
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
        if (session !== sessionRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0) return;
        setAllGoals(goals);
        for (const goal of goals) {
          updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
          updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
        }
      }).catch((error) => {
        if (session === sessionRevisionRef.current && revision === mutationRevisionRef.current) {
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
      if (session !== sessionRevisionRef.current || revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0 || requestSequence !== requestSequenceRef.current || !isCurrentView) {
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
  ]);

  const loadToday = useCallback(async (force = false) => {
    if (!isAuthenticated || !hasAppliedInitialSettings || !localUiSettings.todaySidePanelEnabled) return;
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
      if (revision !== mutationRevisionRef.current || pendingMilestonesRef.current.size > 0) {
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
  }, [isAuthenticated, hasAppliedInitialSettings, localUiSettings.todaySidePanelEnabled, todayKey, userSettings.language]);

  useEffect(() => {
    setTodayDetail(null);
    setSidePanelOpen(true);
    void loadToday();
    return () => { todaySequenceRef.current += 1; };
  }, [loadToday]);

  reloadCurrentViewRef.current = () => {
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
    void loadCalendar();
  }, [loadCalendar]);

  useEffect(() => {
    if (overlayMode === "manual-create") {
      const session = sessionRevisionRef.current;
      const revision = mutationRevisionRef.current;
      void apiClient.listGoals().then((goals) => {
        if (session === sessionRevisionRef.current && revision === mutationRevisionRef.current) setAllGoals(goals);
      }).catch(() => undefined);
    }
  }, [overlayMode]);

  useEffect(() => {
    if (overlayMode !== "day-view") {
      setIsDayViewQuickMenuOpen(false);
    }
  }, [overlayMode]);

  useEffect(() => {
    if (overlayMode === "none") {
      return undefined;
    }

    function handleEscape(event: KeyboardEvent) {
      if (event.key === "Escape") {
        closeOverlay();
      }
    }

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [closeOverlay, overlayMode]);

  async function handleLogin(email: string, password: string, rememberLogin: boolean) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.login(email, password, rememberLogin);
      localStorage.setItem(LAST_LOGIN_EMAIL_KEY, email);
      setIsAuthenticated(true);
      setHasAppliedInitialSettings(false);
      prefetchRunRef.current += 1;
      hasStartedLoginPrefetchRef.current = false;
      calendarCacheRef.current.clear();
      dateDetailCacheRef.current.clear();
      settingsCacheRef.current = null;
      setRequestState({ isLoading: false, message: null, notice: null });
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, authLanguage), notice: null });
    }
  }

  async function handleSignup(email: string, password: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.signup(email, password);
      setRequestState({
        isLoading: false,
        message: null,
        notice: authMessages[authLanguage].signupComplete,
      });
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, authLanguage), notice: null });
    }
  }

  async function handleLogout() {
    sessionRevisionRef.current += 1;
    setIsAuthenticated(false);
    try {
      await apiClient.logout();
    } catch {
      apiClient.setAccessToken(null);
      void apiClient.persistAccessToken(null);
    } finally {
      setIsAuthenticated(false);
      setCalendarData(null);
      setDateDetail(null);
      setUserSettings(DEFAULT_USER_SETTINGS);
      prefetchRunRef.current += 1;
      hasStartedLoginPrefetchRef.current = false;
      calendarCacheRef.current.clear();
      dateDetailCacheRef.current.clear();
      settingsCacheRef.current = null;
      closeOverlay();
      setHasAppliedInitialSettings(false);
      setRequestState({ isLoading: false, message: null, notice: null });
    }
  }

  function handleModeChange(nextMode: CalendarMode) {
    setMode(nextMode);
    if (nextMode === "week") {
      setVisibleDate(getWeekStartDate(selectedDate, weekStartsOn));
    } else {
      setVisibleDate(selectedDate);
    }
  }

  function handleSelectDate(date: string) {
    selectDate(date);
    if (mode === "week") {
      setVisibleDate(getWeekStartDate(date, weekStartsOn));
    }
    setIsDayViewQuickMenuOpen(false);
    openDayView();
  }

  async function handleDeleteAccount() {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteAccount();
      setIsAuthenticated(false);
      setCalendarData(null);
      setDateDetail(null);
      setAllGoals([]);
      setUserSettings(DEFAULT_USER_SETTINGS);
      prefetchRunRef.current += 1;
      hasStartedLoginPrefetchRef.current = false;
      calendarCacheRef.current.clear();
      dateDetailCacheRef.current.clear();
      settingsCacheRef.current = null;
      closeOverlay();
      setHasAppliedInitialSettings(false);
      setRequestState({ isLoading: false, message: null, notice: null });
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  function toggleDayViewQuickMenu() {
    setIsDayViewQuickMenuOpen((current) => !current);
  }

  function handleOpenManualCreateFromDayView() {
    setIsDayViewQuickMenuOpen(false);
    openManualCreate();
  }

  function handleOpenAiCreateFromDayView() {
    setIsDayViewQuickMenuOpen(false);
    openAiCreate();
  }

  function handleOpenGoalListFromDayView() {
    setIsDayViewQuickMenuOpen(false);
    openGoalList();
  }

  function handleToday() {
    const today = todayKey;
    selectDate(today);
    setVisibleDate(mode === "week" ? getWeekStartDate(today, weekStartsOn) : today);
  }

  function handleMove(direction: -1 | 1) {
    const visible = parseDateKey(visibleDate);
    const nextDate = mode === "month" ? moveMonth(visible, direction) : moveWeek(visible, direction);
    setVisibleDate(toDateKey(nextDate));
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
      ?? Array.from(dateDetailCacheRef.current.values()).flatMap((d) => d.milestones).find((m) => m.id === milestoneId);
    const previousCompleted = previous?.is_completed ?? !isCompleted;
    pendingMilestonesRef.current.set(milestoneId, goalId);
    setPendingMilestoneIds(new Set(pendingMilestonesRef.current.keys()));
    mutationRevisionRef.current += 1;
    const applyCompletion = (completed: boolean) => {
      setMilestoneCompletions((current) => ({ ...current, [milestoneId]: completed }));
      const update = (m: Milestone) => m.id === milestoneId ? { ...m, is_completed: completed } : m;
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

  async function handleCreateManualSchedule(goalPayloadOrId: string | GoalCreatePayload, milestonePayloads: MilestoneCreatePayload[]) {
    const session = sessionRevisionRef.current;
    setRequestState({ isLoading: true, message: null, notice: null });
    let createdGoal: Goal | null = null;
    try {
      let goalId: string;
      if (typeof goalPayloadOrId === "string") {
        goalId = goalPayloadOrId;
        const targetGoal = allGoals.find(g => g.id === goalId);
        if (targetGoal && milestonePayloads.length > 0) {
          const maxMilestoneDate = milestonePayloads.map(p => p.scheduled_date).reduce((a, b) => a > b ? a : b);
          if (maxMilestoneDate > targetGoal.deadline) {
            await handleUpdateGoal(goalId, { deadline: maxMilestoneDate });
            if (session !== sessionRevisionRef.current) return;
          }
        }
      } else {
        const goal = await apiClient.createGoal(goalPayloadOrId);
        if (session !== sessionRevisionRef.current) return;
        mutationRevisionRef.current += 1;
        createdGoal = goal;
        goalId = goal.id;
        setAllGoals((current) => [...current.filter((item) => item.id !== goal.id), goal]);
        updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
        updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
      }

      for (const payload of milestonePayloads) {
        const milestone = await apiClient.createMilestone(goalId, payload);
        if (session !== sessionRevisionRef.current) return;
        mutationRevisionRef.current += 1;
        updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
        updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      }

      closeOverlay();
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      if (createdGoal) {
        const goalToRollback = createdGoal;
        try {
          await apiClient.deleteGoal(goalToRollback.id);
          if (session !== sessionRevisionRef.current) return;
          mutationRevisionRef.current += 1;
        } catch {
          // Best-effort rollback; the visible state is still cleaned up locally.
        }
        setAllGoals((current) => current.filter((item) => item.id !== goalToRollback.id));
        updateCachedCalendars((calendar) => removeGoalFromCalendar(calendar, goalToRollback.id));
        updateCachedDateDetails((detail) => removeGoalFromDateDetail(detail, goalToRollback.id));
        refreshCalendarInBackground();
      }
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
      throw error;
    }
  }

  async function handleCreateAiDraft(payload: AiScheduleDraftRequest): Promise<AiScheduleDraft> {
    if (!userSettings.gemini_data_consent) {
      throw new Error(userSettings.language === "en" ? "Gemini transfer consent is required." : "Gemini 전송 동의가 필요합니다.");
    }
    return apiClient.createScheduleDraft(payload);
  }

  async function handleGeminiDataConsentChange(geminiDataConsent: boolean) {
    const previousSettings = userSettings;
    const nextSettings = {
      ...userSettings,
      gemini_data_consent: geminiDataConsent,
    };
    setUserSettings(nextSettings);
    settingsCacheRef.current = nextSettings;
    try {
      const savedSettings = await apiClient.updateSettings({ gemini_data_consent: geminiDataConsent });
      setUserSettings(savedSettings);
      settingsCacheRef.current = savedSettings;
    } catch (error) {
      setUserSettings(previousSettings);
      settingsCacheRef.current = previousSettings;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
      throw error;
    }
  }

  async function handleSaveAiDraft(goalPayload: GoalCreatePayload, milestonePayloads: MilestoneCreatePayload[]) {
    const session = sessionRevisionRef.current;
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const goal = await apiClient.createGoal(goalPayload);
      if (session !== sessionRevisionRef.current) return;
      mutationRevisionRef.current += 1;
      setAllGoals((current) => [...current.filter((item) => item.id !== goal.id), goal]);
      for (const payload of milestonePayloads) {
        const milestone = await apiClient.createMilestone(goal.id, payload);
        if (session !== sessionRevisionRef.current) return;
        mutationRevisionRef.current += 1;
        updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
        updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      }
      updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
      updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
      closeOverlay();
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleUpdateGoal(goalId: string, payload: GoalUpdatePayload) {
    const session = sessionRevisionRef.current;
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const goal = await apiClient.updateGoal(goalId, payload);
      if (session !== sessionRevisionRef.current) return;
      mutationRevisionRef.current += 1;
      setAllGoals((current) => [...current.filter((item) => item.id !== goal.id), goal]);
      updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
      updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleDeleteGoal(goalId: string) {
    const session = sessionRevisionRef.current;
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteGoal(goalId);
      if (session !== sessionRevisionRef.current) return;
      mutationRevisionRef.current += 1;
      setAllGoals((current) => current.filter((item) => item.id !== goalId));
      updateCachedCalendars((calendar) => removeGoalFromCalendar(calendar, goalId));
      updateCachedDateDetails((detail) => removeGoalFromDateDetail(detail, goalId));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleCreateMilestone(goalId: string, payload: MilestoneCreatePayload) {
    const session = sessionRevisionRef.current;
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const milestone = await apiClient.createMilestone(goalId, payload);
      if (session !== sessionRevisionRef.current) return;
      mutationRevisionRef.current += 1;
      updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
      updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleUpdateMilestone(milestoneId: string, payload: MilestoneUpdatePayload) {
    const session = sessionRevisionRef.current;
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const milestone = await apiClient.updateMilestone(milestoneId, payload);
      if (session !== sessionRevisionRef.current) return;
      mutationRevisionRef.current += 1;
      updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
      updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleDeleteMilestone(milestoneId: string) {
    const session = sessionRevisionRef.current;
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteMilestone(milestoneId);
      if (session !== sessionRevisionRef.current) return;
      mutationRevisionRef.current += 1;
      updateCachedCalendars((calendar) => removeMilestoneFromCalendar(calendar, milestoneId));
      updateCachedDateDetails((detail) => removeMilestoneFromDateDetail(detail, milestoneId));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (session !== sessionRevisionRef.current) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleUpdateSettings(payload: UserSettingsUpdatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const settings = await apiClient.updateSettings(payload);
      setUserSettings(settings);
      settingsCacheRef.current = settings;
      applySettingsToCalendar(settings);
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleUpdateLocalUiSettings(payload: LocalUiSettingsPatch) {
    if (payload.todaySidePanelEnabled !== undefined) {
      const previous = localUiSettings;
      setLocalUiSettings({ ...previous, todaySidePanelEnabled: payload.todaySidePanelEnabled });
      try {
        const save = window.mileday?.uiSettings?.setTodaySidePanelEnabled;
        if (!save) throw new Error("Local settings storage is unavailable.");
        const saved = await save(payload.todaySidePanelEnabled);
        setLocalUiSettings((current) => ({ ...current, todaySidePanelEnabled: saved.todaySidePanelEnabled }));
      } catch (error) {
        setLocalUiSettings((current) => ({ ...current, todaySidePanelEnabled: previous.todaySidePanelEnabled }));
        throw error;
      }
      return;
    }
    const nextSettings = {
      ...localUiSettings,
      ...payload,
    };
    setLocalUiSettings(nextSettings);

    if (payload.baseFontSize !== undefined || payload.goalFontSize !== undefined) {
      const saved = await window.mileday?.uiSettings?.setFontSizes({
        baseFontSize: nextSettings.baseFontSize,
        goalFontSize: nextSettings.goalFontSize,
      });
      if (saved) {
        setLocalUiSettings(saved);
      }
    }

    if (payload.resizeEnabled !== undefined) {
      const saved = await window.mileday?.uiSettings?.setResizeEnabled(payload.resizeEnabled);
      if (saved) {
        setLocalUiSettings(saved);
      }
    }

    if (payload.opacity !== undefined) {
      const saved = await window.mileday?.uiSettings?.setOpacity(payload.opacity);
      if (saved) {
        setLocalUiSettings(saved);
      }
    }

    if (payload.settingsPanelSize !== undefined) {
      const saved = await window.mileday?.uiSettings?.setSettingsPanelSize(payload.settingsPanelSize);
      if (saved) {
        setLocalUiSettings(saved);
      }
    }
  }

  function handleAuthLanguageChange(nextLanguage: AuthLanguage) {
    setAuthLanguage(nextLanguage);
    setRequestState((current) => ({ ...current, message: null, notice: null }));
  }

  if (!hasCheckedStoredAuth) {
    return (
      <main className="auth-shell">
        <p className="muted-text">{authMessages[authLanguage].checkingSession}</p>
      </main>
    );
  }

  if (!isAuthenticated) {
    return (
      <AuthPanel
        isLoading={requestState.isLoading}
        errorMessage={requestState.message}
        noticeMessage={requestState.notice}
        language={authLanguage}
        onLanguageChange={handleAuthLanguageChange}
        onLogin={handleLogin}
        onSignup={handleSignup}
      />
    );
  }

  return (
    <main className="app-shell">
      {/*
        Logged-in UI uses the saved app language from settings. The login screen
        keeps its own local language before settings are available.
      */}
      <WindowResizeHandles enabled={localUiSettings.resizeEnabled} />
      <CalendarHeader
        label={headerLabel}
        mode={mode}
        onModeChange={handleModeChange}
        onPrevious={() => handleMove(-1)}
        onNext={() => handleMove(1)}
        onToday={handleToday}
        onOpenSettings={openSettings}
        onWindowMoveStart={handleWindowMoveStart}
        language={userSettings.language}
      />
      {requestState.message ? <p className="toast-error">{requestState.message}</p> : null}
      <div className={`workspace planner-workspace ${localUiSettings.todaySidePanelEnabled ? "has-today-panel" : ""} ${sidePanelOpen ? "today-panel-open" : ""}`}>
        {localUiSettings.todaySidePanelEnabled ? <button type="button" className="today-panel-toggle ghost-button"
          aria-expanded={sidePanelOpen} onClick={() => setSidePanelOpen((open) => !open)}>
          {userSettings.language === "en" ? "Today's schedule" : "\uC624\uB298\uC758 \uC77C\uC815"}
        </button> : null}
        <div className="primary-pane">
          <CalendarBoard
            mode={mode}
            visibleDate={visibleDate}
            selectedDate={selectedDate}
            days={calendarData?.days ?? []}
            weekStartsOn={weekStartsOn}
            holidayDisplay={userSettings.holiday_display}
            language={userSettings.language}
            onSelectDate={handleSelectDate}
            allGoals={allGoals}
          />
        </div>
        {localUiSettings.todaySidePanelEnabled ? <TodaySidePanel today={todayKey}
          detail={todayDetail?.date === todayKey ? todayDetail : null} goals={allGoals}
          language={userSettings.language} isLoading={todayRequest.isLoading || !hasAppliedInitialSettings} error={todayRequest.error}
          pendingIds={pendingMilestoneIds} onRetry={() => { void loadToday(true); }} onToggleMilestone={handleToggleMilestone} /> : null}
      </div>
      <footer className="app-credit" aria-label={appLabels[userSettings.language].credit}>
        <strong>mileday</strong>
        <span>
          made by 노준상 ·{" "}
          <a href="https://github.com/joonsang65/MileDay" target="_blank" rel="noreferrer">
            joonsang65/MileDay
          </a>
        </span>
      </footer>
      {overlayMode === "settings" ? (
        <FloatingPanel
          title={appLabels[userSettings.language].settings}
          onClose={closeOverlay}
          closeLabel={appLabels[userSettings.language].close}
          className="settings-floating-panel"
        >
          <SettingsPanel
            settings={userSettings}
            localUiSettings={localUiSettings}
            isLoading={requestState.isLoading}
            onSave={handleUpdateSettings}
            onLocalUiSettingsChange={handleUpdateLocalUiSettings}
            onClose={closeOverlay}
            onLogout={handleLogout}
            onDeleteAccount={handleDeleteAccount}
          />
        </FloatingPanel>
      ) : null}
      {overlayMode === "manual-create" ? (
        <ManualCreatePanel
          today={todayKey}
          timezone={userSettings.timezone}
          selectedDate={selectedDate}
          isLoading={requestState.isLoading}
          goals={allGoals}
          onCreateSchedule={handleCreateManualSchedule}
          onClose={closeOverlay}
          language={userSettings.language}
        />
      ) : null}
      {overlayMode === "ai-create" ? (
        <AiSchedulePanel
          selectedDate={selectedDate}
          today={todayKey}
          timezone={userSettings.timezone}
          availability={draftAvailability}
          geminiDataConsent={userSettings.gemini_data_consent}
          isSaving={requestState.isLoading}
          onCreateDraft={handleCreateAiDraft}
          onSaveDraft={handleSaveAiDraft}
          onGeminiDataConsentChange={handleGeminiDataConsentChange}
          onClose={closeOverlay}
          language={userSettings.language}
        />
      ) : null}
      {overlayMode === "goal-list" ? (
        <GoalListModal
          milestoneCompletions={milestoneCompletions}
          pendingMilestoneIds={pendingMilestoneIds}
          language={userSettings.language}
          initialGoals={allGoals}
          onClose={closeOverlay}
          onUpdateGoal={handleUpdateGoal}
          onDeleteGoal={handleDeleteGoal}
          onCreateMilestone={handleCreateMilestone}
          onUpdateMilestone={handleUpdateMilestone}
          onDeleteMilestone={handleDeleteMilestone}
          onToggleGoal={handleToggleGoal}
          onToggleMilestone={handleToggleMilestone}
        />
      ) : null}
      {overlayMode === "day-view" ? (
        <FloatingPanel
          title={dateDetailLabels[userSettings.language].title}
          subtitle={dateDetail?.date ?? selectedDate}
          onClose={closeOverlay}
          closeLabel={appLabels[userSettings.language].close}
          placement="center"
          className="goal-list-modal-panel date-detail-floating-panel"
        >
          <DateDetail
            pendingMilestoneIds={pendingMilestoneIds}
            detail={dateDetail}
            goals={allGoals}
            isLoading={requestState.isLoading && !dateDetail}
            onToggleGoal={handleToggleGoal}
            onToggleMilestone={handleToggleMilestone}
            onUpdateGoal={handleUpdateGoal}
            onDeleteGoal={handleDeleteGoal}
            onCreateMilestone={handleCreateMilestone}
            onUpdateMilestone={handleUpdateMilestone}
            onDeleteMilestone={handleDeleteMilestone}
            onEditingChange={setIsDateDetailEditing}
            onOpenQuickMenu={toggleDayViewQuickMenu}
            quickMenuContent={isDayViewQuickMenuOpen ? (
              <QuickActionPopover
                onManualCreate={handleOpenManualCreateFromDayView}
                onAiCreate={handleOpenAiCreateFromDayView}
                onGoalList={handleOpenGoalListFromDayView}
                language={userSettings.language}
              />
            ) : null}
            language={userSettings.language}
            hideHeader
          />
        </FloatingPanel>
      ) : null}
    </main>
  );
}
