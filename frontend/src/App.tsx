import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiClientError, apiClient } from "@/api/client";
import type {
  CalendarDateData,
  CalendarMonthData,
  CalendarWeekData,
  GoalCreatePayload,
  AiScheduleDraft,
  AiScheduleDraftRequest,
  GoalUpdatePayload,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  UserSettings,
  UserSettingsUpdatePayload,
} from "@/api/types";
import { AuthPanel } from "@/components/AuthPanel";
import { AiSchedulePanel } from "@/components/AiSchedulePanel";
import { CalendarBoard } from "@/components/CalendarBoard";
import { CalendarHeader } from "@/components/CalendarHeader";
import { DateDetail } from "@/components/DateDetail";
import { FloatingPanel } from "@/components/FloatingPanel";
import { ManualCreatePanel } from "@/components/ManualCreatePanel";
import { QuickActionPopover } from "@/components/QuickActionPopover";
import { SettingsPanel } from "@/components/SettingsPanel";
import { useCalendarStore, type CalendarMode } from "@/store/calendarStore";
import { useUiStore } from "@/store/uiStore";
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

type RequestState = {
  isLoading: boolean;
  message: string | null;
  notice: string | null;
};

const DEFAULT_USER_SETTINGS: UserSettings = {
  calendar_view: "month",
  theme: "system",
  accent_color: "#4F46E5",
  font_family: "system",
  font_size: 14,
  ai_suggestion: false,
  holiday_display: "normal",
  week_starts_on: 1,
  completed_milestones: true,
  default_goal_color: "#4F46E5",
  default_milestone_color: "#F97316",
  language: "ko",
  timezone: "Asia/Seoul",
};

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
  const [isAuthenticated, setIsAuthenticated] = useState(apiClient.hasAccessToken());
  const [requestState, setRequestState] = useState<RequestState>({
    isLoading: false,
    message: null,
    notice: null,
  });
  const [calendarData, setCalendarData] = useState<CalendarMonthData | CalendarWeekData | null>(
    null,
  );
  const [dateDetail, setDateDetail] = useState<CalendarDateData | null>(null);
  const [userSettings, setUserSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [hasAppliedInitialSettings, setHasAppliedInitialSettings] = useState(false);
  const { overlayMode, openQuickMenu, openManualCreate, openAiCreate, openSettings, closeOverlay } = useUiStore();

  const headerLabel = useMemo(() => {
    if (mode === "month") {
      return getMonthLabel(parseDateKey(visibleDate));
    }
    return getWeekLabel(parseDateKey(visibleDate));
  }, [mode, visibleDate]);

  const todayKey = useMemo(() => toDateKey(new Date()), []);
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

  const loadCalendar = useCallback(async () => {
    if (!isAuthenticated) {
      return;
    }
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const visible = parseDateKey(visibleDate);
      const [settings, calendar, detail] = await Promise.all([
        apiClient.getSettings(),
        mode === "month"
          ? apiClient.getMonthCalendar(visible.getFullYear(), visible.getMonth() + 1)
          : apiClient.getWeekCalendar(getWeekStartDate(visibleDate, weekStartsOn)),
        apiClient.getDateCalendar(selectedDate),
      ]);
      setUserSettings(settings);
      if (!hasAppliedInitialSettings) {
        applySettingsToCalendar(settings);
        setHasAppliedInitialSettings(true);
      }
      setCalendarData(calendar);
      setDateDetail(detail);
      setRequestState({ isLoading: false, message: null, notice: null });
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) {
        apiClient.setAccessToken(null);
        setIsAuthenticated(false);
      }
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }, [
    applySettingsToCalendar,
    hasAppliedInitialSettings,
    isAuthenticated,
    mode,
    selectedDate,
    visibleDate,
    weekStartsOn,
  ]);

  useEffect(() => {
    void loadCalendar();
  }, [loadCalendar]);

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

  async function handleLogin(email: string, password: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.login(email, password);
      setIsAuthenticated(true);
      setHasAppliedInitialSettings(false);
      setRequestState({ isLoading: false, message: null, notice: null });
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleSignup(email: string, password: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.signup(email, password);
      setRequestState({
        isLoading: false,
        message: null,
        notice: "회원가입이 완료되었습니다. 로그인해 주세요.",
      });
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleLogout() {
    await apiClient.logout();
    setIsAuthenticated(false);
    setCalendarData(null);
    setDateDetail(null);
    setUserSettings(DEFAULT_USER_SETTINGS);
    closeOverlay();
    setHasAppliedInitialSettings(false);
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
  }

  function handleToday() {
    const today = toDateKey(new Date());
    selectDate(today);
    setVisibleDate(mode === "week" ? getWeekStartDate(today, weekStartsOn) : today);
  }

  function handleMove(direction: -1 | 1) {
    const visible = parseDateKey(visibleDate);
    const nextDate = mode === "month" ? moveMonth(visible, direction) : moveWeek(visible, direction);
    setVisibleDate(toDateKey(nextDate));
  }

  async function handleToggleMilestone(milestoneId: string, isCompleted: boolean) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.completeMilestone(milestoneId, isCompleted);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleCreateGoal(payload: GoalCreatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.createGoal(payload);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleCreateAiDraft(payload: AiScheduleDraftRequest): Promise<AiScheduleDraft> {
    return apiClient.createScheduleDraft(payload);
  }

  async function handleSaveAiDraft(goalPayload: GoalCreatePayload, milestonePayloads: MilestoneCreatePayload[]) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const goal = await apiClient.createGoal(goalPayload);
      for (const payload of milestonePayloads) {
        await apiClient.createMilestone(goal.id, payload);
      }
      closeOverlay();
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleUpdateGoal(goalId: string, payload: GoalUpdatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.updateGoal(goalId, payload);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleDeleteGoal(goalId: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteGoal(goalId);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleUpdateMilestone(milestoneId: string, payload: MilestoneUpdatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.updateMilestone(milestoneId, payload);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleDeleteMilestone(milestoneId: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteMilestone(milestoneId);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  async function handleUpdateSettings(payload: UserSettingsUpdatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const settings = await apiClient.updateSettings(payload);
      setUserSettings(settings);
      applySettingsToCalendar(settings);
      setRequestState({ isLoading: false, message: null, notice: null });
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getUserFacingErrorMessage(error), notice: null });
    }
  }

  if (!isAuthenticated) {
    return (
      <AuthPanel
        isLoading={requestState.isLoading}
        errorMessage={requestState.message}
        noticeMessage={requestState.notice}
        onLogin={handleLogin}
        onSignup={handleSignup}
      />
    );
  }

  return (
    <main className="app-shell">
      <CalendarHeader
        label={headerLabel}
        mode={mode}
        isLoading={requestState.isLoading}
        onModeChange={handleModeChange}
        onPrevious={() => handleMove(-1)}
        onNext={() => handleMove(1)}
        onToday={handleToday}
        onRefresh={loadCalendar}
        onOpenSettings={openSettings}
        onOpenQuickMenu={openQuickMenu}
        language={userSettings.language}
      />
      {overlayMode === "quick-menu" ? (
        <>
          <button type="button" className="quick-menu-backdrop" aria-label="메뉴 닫기" onClick={closeOverlay} />
          <QuickActionPopover
            onManualCreate={openManualCreate}
            onAiCreate={openAiCreate}
          />
        </>
      ) : null}
      {requestState.message ? <p className="toast-error">{requestState.message}</p> : null}
      <div className="workspace planner-workspace">
        <div className="primary-pane">
          <CalendarBoard
            mode={mode}
            visibleDate={visibleDate}
            selectedDate={selectedDate}
            days={calendarData?.days ?? []}
            weekStartsOn={weekStartsOn}
            holidayDisplay={userSettings.holiday_display}
            onSelectDate={handleSelectDate}
          />
        </div>
        <DateDetail
          detail={dateDetail}
          isLoading={requestState.isLoading && !dateDetail}
          isTodaySelected={selectedDate === todayKey}
          onGoToday={handleToday}
          onToggleMilestone={handleToggleMilestone}
          onUpdateGoal={handleUpdateGoal}
          onDeleteGoal={handleDeleteGoal}
          onUpdateMilestone={handleUpdateMilestone}
          onDeleteMilestone={handleDeleteMilestone}
        />
      </div>
      {overlayMode === "settings" ? (
        <FloatingPanel title="설정" onClose={closeOverlay}>
          <SettingsPanel
            settings={userSettings}
            isLoading={requestState.isLoading}
            onSave={handleUpdateSettings}
            onClose={closeOverlay}
            onLogout={handleLogout}
          />
        </FloatingPanel>
      ) : null}
      {overlayMode === "manual-create" ? (
        <ManualCreatePanel
          selectedDate={selectedDate}
          isLoading={requestState.isLoading}
          onCreateGoal={handleCreateGoal}
          onClose={closeOverlay}
        />
      ) : null}
      {overlayMode === "ai-create" ? (
        <AiSchedulePanel
          selectedDate={selectedDate}
          today={todayKey}
          timezone={userSettings.timezone}
          availability={draftAvailability}
          isSaving={requestState.isLoading}
          onCreateDraft={handleCreateAiDraft}
          onSaveDraft={handleSaveAiDraft}
          onClose={closeOverlay}
        />
      ) : null}
    </main>
  );
}
