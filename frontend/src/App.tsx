import { type PointerEvent as ReactPointerEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { apiClient } from "@/api/client";
import type {
  Goal,
  GoalCreatePayload,
  AiScheduleDraft,
  AiScheduleDraftRequest,
  GoalUpdatePayload,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  UserSettingsUpdatePayload,
} from "@/api/types";
import {
  upsertGoalInCalendar,
  upsertGoalInDateDetail,
  upsertMilestoneInCalendar,
  upsertMilestoneInDateDetail,
  removeGoalFromCalendar,
  removeGoalFromDateDetail,
  removeMilestoneFromCalendar,
  removeMilestoneFromDateDetail,
} from "@/calendar/calendarUpdates";
import { useCalendarData, type RequestState } from "@/calendar/useCalendarData";
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
import { LAST_LOGIN_EMAIL_KEY } from "@/config/storageKeys";
import { useCalendarStore, type CalendarMode } from "@/store/calendarStore";
import { useUiStore } from "@/store/uiStore";
import type { AuthLanguage } from "@/types/auth";
import { DEFAULT_LOCAL_UI_SETTINGS, type LocalUiSettings, type LocalUiSettingsPatch } from "@/types/localUiSettings";
import { RESIZE_DIRECTIONS, type ResizeDirection } from "@/types/windowResize";
import { getInitialAuthLanguage } from "@/utils/authLanguage";
import {
  getWeekStartDate,
  getMonthLabel,
  getWeekLabel,
  moveMonth,
  moveWeek,
  parseDateKey,
  toDateKey,
} from "@/utils/date";
import { getUserFacingErrorMessage } from "@/utils/errorMessages";

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

export default function App() {
  const {
    mode,
    selectedDate,
    visibleDate,
    weekStartsOn,
    setMode,
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
  const [sidePanelOpen, setSidePanelOpen] = useState(true);
  const resetTodayView = useCallback(() => setSidePanelOpen(true), []);
  const [localUiSettings, setLocalUiSettings] = useState<LocalUiSettings>(DEFAULT_LOCAL_UI_SETTINGS);
  const [isDateDetailEditing, setIsDateDetailEditing] = useState(false);
  const [isDayViewQuickMenuOpen, setIsDayViewQuickMenuOpen] = useState(false);
  const { overlayMode, openManualCreate, openAiCreate, openSettings, openDayView, openGoalList, closeOverlay } = useUiStore();
  const handleWindowMoveStart = useWindowMoveDrag();

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

  useEffect(() => {
    const handleSessionCleared = () => setIsAuthenticated(false);
    window.addEventListener("mileday-session-cleared", handleSessionCleared);
    const stopSessionRefresh = apiClient.startSessionRefresh();
    return () => {
      stopSessionRefresh();
      window.removeEventListener("mileday-session-cleared", handleSessionCleared);
    };
  }, []);

  const {
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
  } = useCalendarData({
    mode, selectedDate, visibleDate, weekStartsOn, authLanguage, isAuthenticated,
    setIsAuthenticated, setRequestState,
    todaySidePanelEnabled: localUiSettings.todaySidePanelEnabled,
    isManualCreateOpen: overlayMode === "manual-create",
    onTodayViewReset: resetTodayView,
  });

  const headerLabel = useMemo(() => {
    if (mode === "month") {
      return getMonthLabel(parseDateKey(visibleDate), userSettings.language);
    }
    return getWeekLabel(parseDateKey(visibleDate), userSettings.language);
  }, [mode, userSettings.language, visibleDate]);

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
      prepareCalendarLogin();
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
    invalidateCalendarSession();
    setIsAuthenticated(false);
    clearCalendarView();
    closeOverlay();
    setRequestState({ isLoading: false, message: null, notice: null });
    await apiClient.logout().catch(() => undefined);
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
      clearCalendarView();
      setAllGoals([]);
      closeOverlay();
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

  async function handleCreateManualSchedule(goalPayloadOrId: string | GoalCreatePayload, milestonePayloads: MilestoneCreatePayload[]) {
    const mutation = trackCalendarMutation();
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
            if (!mutation.isCurrent()) return;
          }
        }
      } else {
        const goal = await apiClient.createGoal(goalPayloadOrId);
        if (!mutation.isCurrent()) return;
        mutation.recordChange();
        createdGoal = goal;
        goalId = goal.id;
        setAllGoals((current) => [...current.filter((item) => item.id !== goal.id), goal]);
        updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
        updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
      }

      for (const payload of milestonePayloads) {
        const milestone = await apiClient.createMilestone(goalId, payload);
        if (!mutation.isCurrent()) return;
        mutation.recordChange();
        updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
        updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      }

      closeOverlay();
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (!mutation.isCurrent()) return;
      if (createdGoal) {
        const goalToRollback = createdGoal;
        try {
          await apiClient.deleteGoal(goalToRollback.id);
          if (!mutation.isCurrent()) return;
          mutation.recordChange();
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
    storeUserSettings(nextSettings);
    try {
      const savedSettings = await apiClient.updateSettings({ gemini_data_consent: geminiDataConsent });
      storeUserSettings(savedSettings);
    } catch (error) {
      storeUserSettings(previousSettings);
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
      throw error;
    }
  }

  async function handleSaveAiDraft(goalPayload: GoalCreatePayload, milestonePayloads: MilestoneCreatePayload[]) {
    const mutation = trackCalendarMutation();
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const goal = await apiClient.createGoal(goalPayload);
      if (!mutation.isCurrent()) return;
      mutation.recordChange();
      setAllGoals((current) => [...current.filter((item) => item.id !== goal.id), goal]);
      for (const payload of milestonePayloads) {
        const milestone = await apiClient.createMilestone(goal.id, payload);
        if (!mutation.isCurrent()) return;
        mutation.recordChange();
        updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
        updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      }
      updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
      updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
      closeOverlay();
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (!mutation.isCurrent()) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleUpdateGoal(goalId: string, payload: GoalUpdatePayload) {
    const mutation = trackCalendarMutation();
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const goal = await apiClient.updateGoal(goalId, payload);
      if (!mutation.isCurrent()) return;
      mutation.recordChange();
      setAllGoals((current) => [...current.filter((item) => item.id !== goal.id), goal]);
      updateCachedCalendars((calendar) => upsertGoalInCalendar(calendar, goal));
      updateCachedDateDetails((detail) => upsertGoalInDateDetail(detail, goal));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (!mutation.isCurrent()) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleDeleteGoal(goalId: string) {
    const mutation = trackCalendarMutation();
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteGoal(goalId);
      if (!mutation.isCurrent()) return;
      mutation.recordChange();
      setAllGoals((current) => current.filter((item) => item.id !== goalId));
      updateCachedCalendars((calendar) => removeGoalFromCalendar(calendar, goalId));
      updateCachedDateDetails((detail) => removeGoalFromDateDetail(detail, goalId));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (!mutation.isCurrent()) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleCreateMilestone(goalId: string, payload: MilestoneCreatePayload) {
    const mutation = trackCalendarMutation();
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const milestone = await apiClient.createMilestone(goalId, payload);
      if (!mutation.isCurrent()) return;
      mutation.recordChange();
      updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
      updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (!mutation.isCurrent()) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleUpdateMilestone(milestoneId: string, payload: MilestoneUpdatePayload) {
    const mutation = trackCalendarMutation();
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const milestone = await apiClient.updateMilestone(milestoneId, payload);
      if (!mutation.isCurrent()) return;
      mutation.recordChange();
      updateCachedCalendars((calendar) => upsertMilestoneInCalendar(calendar, milestone));
      updateCachedDateDetails((detail) => upsertMilestoneInDateDetail(detail, milestone));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (!mutation.isCurrent()) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleDeleteMilestone(milestoneId: string) {
    const mutation = trackCalendarMutation();
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteMilestone(milestoneId);
      if (!mutation.isCurrent()) return;
      mutation.recordChange();
      updateCachedCalendars((calendar) => removeMilestoneFromCalendar(calendar, milestoneId));
      updateCachedDateDetails((detail) => removeMilestoneFromDateDetail(detail, milestoneId));
      setRequestState({ isLoading: false, message: null, notice: null });
      refreshCalendarInBackground();
    } catch (error) {
      if (!mutation.isCurrent()) return;
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error, userSettings.language), notice: null });
    }
  }

  async function handleUpdateSettings(payload: UserSettingsUpdatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const settings = await apiClient.updateSettings(payload);
      storeUserSettings(settings);
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
            today={todayKey}
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
