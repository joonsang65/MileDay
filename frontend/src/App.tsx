import { useCallback, useEffect, useMemo, useState } from "react";
import { startOfWeek } from "date-fns";

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
} from "@/api/types";
import { AuthPanel } from "@/components/AuthPanel";
import { CalendarBoard } from "@/components/CalendarBoard";
import { CalendarHeader } from "@/components/CalendarHeader";
import { CreationPanel } from "@/components/CreationPanel";
import { DateDetail } from "@/components/DateDetail";
import { TodayList } from "@/components/TodayList";
import { useCalendarStore, type CalendarMode } from "@/store/calendarStore";
import {
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

function getWeekStart(dateKey: string): string {
  return toDateKey(startOfWeek(parseDateKey(dateKey), { weekStartsOn: 1 }));
}

export default function App() {
  const {
    mode,
    selectedDate,
    visibleDate,
    setMode,
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

  const headerLabel = useMemo(() => {
    if (mode === "month") {
      return getMonthLabel(parseDateKey(visibleDate));
    }
    return getWeekLabel(parseDateKey(visibleDate));
  }, [mode, visibleDate]);

  const loadCalendar = useCallback(async () => {
    if (!isAuthenticated) {
      return;
    }
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      const visible = parseDateKey(visibleDate);
      const [calendar, detail, today, goalList] = await Promise.all([
        mode === "month"
          ? apiClient.getMonthCalendar(visible.getFullYear(), visible.getMonth() + 1)
          : apiClient.getWeekCalendar(getWeekStart(visibleDate)),
        apiClient.getDateCalendar(selectedDate),
        apiClient.getTodayMilestones(),
        apiClient.listGoals(),
      ]);
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
  }, [isAuthenticated, mode, selectedDate, visibleDate]);

  useEffect(() => {
    void loadCalendar();
  }, [loadCalendar]);

  async function handleLogin(email: string, password: string) {
    setRequestState({ isLoading: true, message: null, notice: null });
    try {
      await apiClient.login(email, password);
      setIsAuthenticated(true);
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
  }

  function handleModeChange(nextMode: CalendarMode) {
    setMode(nextMode);
    if (nextMode === "week") {
      setVisibleDate(getWeekStart(selectedDate));
    } else {
      setVisibleDate(selectedDate);
    }
  }

  function handleSelectDate(date: string) {
    selectDate(date);
    if (mode === "week") {
      setVisibleDate(getWeekStart(date));
    }
  }

  function handleToday() {
    const today = toDateKey(new Date());
    selectDate(today);
    setVisibleDate(mode === "week" ? getWeekStart(today) : today);
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
        onLogout={handleLogout}
      />
      {requestState.message ? <p className="toast-error">{requestState.message}</p> : null}
      <div className="workspace">
        <div className="primary-pane">
          <CalendarBoard
            mode={mode}
            visibleDate={visibleDate}
            selectedDate={selectedDate}
            days={calendarData?.days ?? []}
            onSelectDate={handleSelectDate}
          />
        </div>
        <aside className="side-pane">
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
        </aside>
      </div>
    </main>
  );
}
