import { useCallback, useEffect, useMemo, useState } from "react";
import { ApiClientError, apiClient } from "@/api/client";
import type {
  CalendarDateData,
  CalendarMonthData,
  CalendarWeekData,
  Goal,
  GoalCreatePayload,
  GoalUpdatePayload,
  Milestone,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  UserSettings,
  UserSettingsUpdatePayload,
} from "@/api/types";
import { AuthPanel } from "@/components/AuthPanel";
import { CalendarBoard } from "@/components/CalendarBoard";
import { CalendarHeader } from "@/components/CalendarHeader";
import { CreationPanel } from "@/components/CreationPanel";
import { DateDetail } from "@/components/DateDetail";
import { SettingsPanel } from "@/components/SettingsPanel";
import { TodayList } from "@/components/TodayList";
import { useCalendarStore, type CalendarMode } from "@/store/calendarStore";
import {
  getWeekStartDate,
  getMonthLabel,
  getWeekLabel,
  moveMonth,
  moveWeek,
  parseDateKey,
  toDateKey,
} from "@/utils/date";

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

function getErrorMessage(error: unknown): string {
  if (error instanceof ApiClientError) {
    if (
      error.detail &&
      typeof error.detail === "object" &&
      "message" in error.detail &&
      typeof error.detail.message === "string"
    ) {
      return `${error.message} (${error.detail.message})`;
    }
    return error.message;
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "요청을 처리하지 못했습니다.";
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
  const [todayMilestones, setTodayMilestones] = useState<Milestone[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [userSettings, setUserSettings] = useState<UserSettings>(DEFAULT_USER_SETTINGS);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [hasAppliedInitialSettings, setHasAppliedInitialSettings] = useState(false);

  const headerLabel = useMemo(() => {
    if (mode === "month") {
      return getMonthLabel(parseDateKey(visibleDate));
    }
    return getWeekLabel(parseDateKey(visibleDate));
  }, [mode, visibleDate]);

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
      const [settings, calendar, detail, today, goalList] = await Promise.all([
        apiClient.getSettings(),
        mode === "month"
          ? apiClient.getMonthCalendar(visible.getFullYear(), visible.getMonth() + 1)
          : apiClient.getWeekCalendar(getWeekStartDate(visibleDate, weekStartsOn)),
        apiClient.getDateCalendar(selectedDate),
        apiClient.getTodayMilestones(),
        apiClient.listGoals(),
      ]);
      setUserSettings(settings);
      if (!hasAppliedInitialSettings) {
        applySettingsToCalendar(settings);
        setHasAppliedInitialSettings(true);
      }
      setCalendarData(calendar);
      setDateDetail(detail);
      setTodayMilestones(today);
      setGoals(goalList);
      setRequestState({ isLoading: false, message: null, notice: null });
    } catch (error) {
      if (error instanceof ApiClientError && error.status === 401) {
        apiClient.setAccessToken(null);
        setIsAuthenticated(false);
      }
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
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

  async function handleLogin(email: string, password: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.login(email, password);
      setIsAuthenticated(true);
      setHasAppliedInitialSettings(false);
      setRequestState({ isLoading: false, message: null, notice: null });
    } catch (error) {
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
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
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
    }
  }

  async function handleLogout() {
    await apiClient.logout();
    setIsAuthenticated(false);
    setCalendarData(null);
    setDateDetail(null);
    setTodayMilestones([]);
    setGoals([]);
    setUserSettings(DEFAULT_USER_SETTINGS);
    setIsSettingsOpen(false);
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
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
    }
  }

  async function handleCreateGoal(payload: GoalCreatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.createGoal(payload);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
    }
  }

  async function handleCreateMilestones(goalId: string, payloads: MilestoneCreatePayload[]) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      for (const payload of payloads) {
        await apiClient.createMilestone(goalId, payload);
      }
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
    }
  }

  async function handleUpdateGoal(goalId: string, payload: GoalUpdatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.updateGoal(goalId, payload);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
    }
  }

  async function handleDeleteGoal(goalId: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteGoal(goalId);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
    }
  }

  async function handleUpdateMilestone(milestoneId: string, payload: MilestoneUpdatePayload) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.updateMilestone(milestoneId, payload);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
    }
  }

  async function handleDeleteMilestone(milestoneId: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.deleteMilestone(milestoneId);
      await loadCalendar();
    } catch (error) {
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
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
      setRequestState({ isLoading: false, message: getErrorMessage(error), notice: null });
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
        onOpenSettings={() => setIsSettingsOpen(true)}
        language={userSettings.language}
      />
      {requestState.message ? <p className="toast-error">{requestState.message}</p> : null}
      <div className="workspace">
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
        <aside className="side-pane">
          {isSettingsOpen ? (
            <SettingsPanel
              settings={userSettings}
              isLoading={requestState.isLoading}
              onSave={handleUpdateSettings}
              onClose={() => setIsSettingsOpen(false)}
              onLogout={handleLogout}
            />
          ) : (
            <>
              <TodayList
                milestones={todayMilestones}
                isLoading={requestState.isLoading && todayMilestones.length === 0}
                onToggleMilestone={handleToggleMilestone}
              />
              <DateDetail
                detail={dateDetail}
                isLoading={requestState.isLoading && !dateDetail}
                onToggleMilestone={handleToggleMilestone}
                onUpdateGoal={handleUpdateGoal}
                onDeleteGoal={handleDeleteGoal}
                onUpdateMilestone={handleUpdateMilestone}
                onDeleteMilestone={handleDeleteMilestone}
              />
              <CreationPanel
                goals={goals}
                selectedDate={selectedDate}
                isLoading={requestState.isLoading}
                onCreateGoal={handleCreateGoal}
                onCreateMilestones={handleCreateMilestones}
              />
            </>
          )}
        </aside>
      </div>
    </main>
  );
}
