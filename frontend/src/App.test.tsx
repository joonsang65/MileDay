import { act, cleanup, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
import { apiClient } from "@/api/client";
import type { CalendarDateData, Goal, Milestone } from "@/api/types";
import { DEFAULT_USER_SETTINGS } from "@/config/defaultUserSettings";
import { DEFAULT_LOCAL_UI_SETTINGS } from "@/types/localUiSettings";
import { useCalendarStore } from "@/store/calendarStore";
import { useUiStore } from "@/store/uiStore";

const goal: Goal = { id: "g", title: "목표", deadline: "2026-10-15", is_completed: false, is_recurring: false, recurrence_type: null, color: "#7F9278", created_at: "", updated_at: "" };
const milestone: Milestone = { id: "m", goal_id: "g", goal_title: goal.title, title: "오늘 작업", scheduled_date: "2026-10-15", is_completed: false, color: goal.color };
const detail = (date: string): CalendarDateData => ({ date, is_today: date === "2026-10-15", goals: date === "2026-10-15" ? [goal] : [], milestones: date === "2026-10-15" ? [milestone, { ...milestone, id: "m2", title: "다른 작업" }] : [], goal_count: 1, milestone_count: 2, completed_milestone_count: 0 });

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

function localSettings(enabled = true) {
  return { ...DEFAULT_LOCAL_UI_SETTINGS, todaySidePanelEnabled: enabled };
}

beforeEach(() => {
  vi.useFakeTimers({ toFake: ["Date"] });
  vi.setSystemTime(new Date("2026-10-15T12:00:00+09:00"));
  useCalendarStore.setState({ mode: "month", selectedDate: "2026-12-10", visibleDate: "2026-12-10", weekStartsOn: 1 });
  useUiStore.setState({ overlayMode: "none" });
  vi.spyOn(apiClient, "hasAccessToken").mockReturnValue(true);
  vi.spyOn(apiClient, "loadStoredAccessToken").mockResolvedValue(true);
  vi.spyOn(apiClient, "startSessionRefresh").mockReturnValue(vi.fn());
  vi.spyOn(apiClient, "getSettings").mockResolvedValue(DEFAULT_USER_SETTINGS);
  vi.spyOn(apiClient, "listGoals").mockResolvedValue([goal]);
  vi.spyOn(apiClient, "listGoalsWithMilestones").mockResolvedValue([{ ...goal, milestones: [milestone] }]);
  vi.spyOn(apiClient, "getDateCalendar").mockImplementation(async (date) => detail(date));
  vi.spyOn(apiClient, "getMonthCalendar").mockImplementation(async (year, month) => ({ year, month, days: [detail(`${year}-${String(month).padStart(2, "0")}-10`)], goals: [], milestones: [] }));
  vi.spyOn(apiClient, "completeMilestone").mockImplementation(async (id, completed) => ({ ...milestone, id, is_completed: completed }));
  window.mileday = { platform: "win32", uiSettings: { get: vi.fn().mockResolvedValue(localSettings()), setTodaySidePanelEnabled: vi.fn().mockImplementation(async (enabled) => localSettings(enabled)) } } as unknown as NonNullable<Window["mileday"]>;
});

describe("desktop date rollover", () => {
  async function flush() {
    await act(async () => {
      for (let turn = 0; turn < 20; turn += 1) await Promise.resolve();
    });
  }

  async function startAt(date: string, mode: "month" | "week" = "month", visibleDate = date, timezone = "Asia/Seoul") {
    vi.useRealTimers();
    vi.useFakeTimers();
    vi.setSystemTime(new Date(`${date}T23:59:59.000+09:00`));
    useCalendarStore.setState({ mode, selectedDate: date, visibleDate });
    vi.mocked(apiClient.getSettings).mockResolvedValue({ ...DEFAULT_USER_SETTINGS, calendar_view: mode, week_starts_on: 1, timezone });
    vi.mocked(apiClient.listGoals).mockResolvedValue([]);
    vi.spyOn(apiClient, "getWeekCalendar").mockImplementation(async (start_date) => ({ start_date, end_date: start_date, days: [], goals: [], milestones: [] }));
    const result = render(<App />);
    await flush();
    // Finish initial prefetch so later assertions distinguish cached data from fresh reads.
    await act(async () => { await vi.advanceTimersByTimeAsync(0); });
    await flush();
    return result;
  }

  it.each([
    ["2026-10-09", "2026-10-10", "month", "2026-10-10"],
    ["2026-10-15", "2026-10-16", "month", "2026-10-16"],
    ["2026-10-31", "2026-11-01", "month", "2026-11-01"],
    ["2026-12-31", "2027-01-01", "month", "2027-01-01"],
    ["2026-12-31", "2027-01-01", "week", "2026-12-28"],
    ["2027-01-03", "2027-01-04", "week", "2027-01-04"],
  ] as const)("rolls %s to %s while awake in %s view", async (before, after, mode, visibleDate) => {
    const { container } = await startAt(before, mode);
    vi.mocked(apiClient.getDateCalendar).mockClear();
    vi.mocked(apiClient.getMonthCalendar).mockClear();
    vi.mocked(apiClient.getWeekCalendar).mockClear();
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    await flush();
    expect(useCalendarStore.getState()).toMatchObject({ selectedDate: after, visibleDate });
    expect(container.querySelector(`[data-date="${after}"]`)).toHaveClass("today");
    expect(container.querySelector(`[data-date="${before}"].today`)).toBeNull();
    expect(screen.getByRole("complementary")).toHaveTextContent(after);
    expect(apiClient.getDateCalendar).toHaveBeenCalledWith(after);
    if (mode === "month") {
      const [year, month] = after.split("-").map(Number);
      expect(apiClient.getMonthCalendar).toHaveBeenCalledWith(year, month);
    } else {
      expect(apiClient.getWeekCalendar).toHaveBeenCalledWith(visibleDate);
    }
  });

  it.each(["focus", "visibilitychange", "online"])("refreshes immediately on %s after sleeping past midnight and preserves browsing", async (eventName) => {
    await startAt("2026-10-15");
    act(() => useCalendarStore.setState({ selectedDate: "2026-12-10", visibleDate: "2026-12-10" }));
    await flush();
    vi.mocked(apiClient.getMonthCalendar).mockClear();
    vi.mocked(apiClient.getDateCalendar).mockClear();
    act(() => {
      vi.setSystemTime(new Date("2027-01-01T00:00:00+09:00"));
      (eventName === "visibilitychange" ? document : window).dispatchEvent(new Event(eventName));
    });
    await flush();
    expect(useCalendarStore.getState()).toMatchObject({ selectedDate: "2026-12-10", visibleDate: "2026-12-10" });
    expect(apiClient.getMonthCalendar).toHaveBeenCalledWith(2026, 12);
    expect(apiClient.getDateCalendar).toHaveBeenCalledWith("2027-01-01");
    expect(screen.getByRole("complementary")).toHaveTextContent("2027-01-01");
  });

  it("preserves a separately browsed month even when selection follows today", async () => {
    await startAt("2026-10-31");
    act(() => useCalendarStore.setState({ visibleDate: "2027-02-01" }));
    await flush();
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(useCalendarStore.getState()).toMatchObject({ selectedDate: "2026-11-01", visibleDate: "2027-02-01" });
  });

  it("uses the configured timezone rather than the host date", async () => {
    const { container } = await startAt("2026-10-15", "month", "2026-10-15", "America/New_York");
    act(() => {
      vi.setSystemTime(new Date("2026-10-16T01:00:00+09:00"));
      window.dispatchEvent(new Event("focus"));
    });
    await flush();
    expect(screen.getByRole("complementary")).toHaveTextContent("2026-10-15");
    expect(container.querySelector('[data-date="2026-10-15"]')).toHaveClass("today");
    act(() => {
      vi.setSystemTime(new Date("2026-10-16T00:00:00-04:00"));
      window.dispatchEvent(new Event("focus"));
    });
    await flush();
    expect(screen.getByRole("complementary")).toHaveTextContent("2026-10-16");
    expect(container.querySelector('[data-date="2026-10-16"]')).toHaveClass("today");
  });

  it("defers rollover reads until a pending milestone mutation settles", async () => {
    const saving = deferred<Milestone>();
    vi.mocked(apiClient.completeMilestone).mockReturnValueOnce(saving.promise);
    await startAt("2026-10-15");
    fireEvent.click(within(screen.getByRole("complementary")).getByRole("button", { name: "오늘 작업" }));
    vi.mocked(apiClient.getMonthCalendar).mockClear();
    vi.mocked(apiClient.getDateCalendar).mockClear();
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(apiClient.getMonthCalendar).not.toHaveBeenCalled();
    expect(apiClient.getDateCalendar).not.toHaveBeenCalled();
    expect(apiClient.completeMilestone).toHaveBeenCalledTimes(1);
    await act(async () => saving.resolve({ ...milestone, is_completed: true }));
    await flush();
    expect(apiClient.getMonthCalendar).toHaveBeenCalledWith(2026, 10);
    expect(apiClient.getDateCalendar).toHaveBeenCalledWith("2026-10-16");
    expect(useCalendarStore.getState().selectedDate).toBe("2026-10-16");
  });

  it("preserves a pending optimistic goal completion during rollover", async () => {
    const saving = deferred<Goal>();
    vi.spyOn(apiClient, "completeGoal").mockReturnValue(saving.promise);
    vi.mocked(apiClient.getDateCalendar).mockImplementation(async (date) => ({ ...detail(date), milestones: [], milestone_count: 0 }));
    await startAt("2026-10-15");
    act(() => useUiStore.getState().openDayView());
    fireEvent.click(screen.getByTestId("goal-toggle"));
    expect(screen.getByTestId("goal-toggle")).toHaveAttribute("aria-pressed", "true");
    vi.mocked(apiClient.getMonthCalendar).mockClear();
    vi.mocked(apiClient.getDateCalendar).mockClear();
    await act(async () => { await vi.advanceTimersByTimeAsync(1000); });
    expect(screen.getByTestId("goal-toggle")).toHaveAttribute("aria-pressed", "true");
    expect(apiClient.getMonthCalendar).not.toHaveBeenCalled();
    expect(apiClient.getDateCalendar).not.toHaveBeenCalled();
    await act(async () => saving.resolve({ ...goal, is_completed: true }));
    await flush();
    expect(apiClient.getMonthCalendar).toHaveBeenCalledWith(2026, 10);
    expect(apiClient.getDateCalendar).toHaveBeenCalledWith("2026-10-16");
  });

  it.each(["focus", "visibilitychange", "online"])("forces fresh data on same-day %s without moving the selection", async (eventName) => {
    await startAt("2026-10-15");
    vi.mocked(apiClient.getMonthCalendar).mockClear();
    vi.mocked(apiClient.getDateCalendar).mockClear();
    act(() => (eventName === "visibilitychange" ? document : window).dispatchEvent(new Event(eventName)));
    await flush();
    expect(apiClient.getMonthCalendar).toHaveBeenCalledWith(2026, 10);
    expect(apiClient.getDateCalendar).toHaveBeenCalledWith("2026-10-15");
    expect(useCalendarStore.getState()).toMatchObject({ selectedDate: "2026-10-15", visibleDate: "2026-10-15" });
  });

  it("starts session refresh, handles cleared sessions, and cleans up on unmount", async () => {
    const stop = vi.fn();
    vi.mocked(apiClient.startSessionRefresh).mockReturnValue(stop);
    const { unmount } = await startAt("2026-10-15");
    expect(apiClient.startSessionRefresh).toHaveBeenCalledTimes(1);
    act(() => window.dispatchEvent(new Event("mileday-session-cleared")));
    await flush();
    expect(screen.getByRole("heading", { name: "로그인" })).toBeInTheDocument();
    unmount();
    expect(stop).toHaveBeenCalledTimes(1);
  });
});

afterEach(() => { cleanup(); vi.restoreAllMocks(); vi.useRealTimers(); delete window.mileday; });

async function start() {
  render(<App />);
  return within(await screen.findByRole("complementary", { name: "오늘의 일정" }));
}

describe("today side panel integration", () => {
  it("defaults off and does not fetch panel-only data", async () => {
    vi.mocked(window.mileday!.uiSettings!.get).mockResolvedValue(DEFAULT_LOCAL_UI_SETTINGS);
    render(<App />);
    await waitFor(() => expect(apiClient.getMonthCalendar).toHaveBeenCalled());
    expect(screen.queryByRole("complementary")).not.toBeInTheDocument();
    expect(apiClient.getDateCalendar).not.toHaveBeenCalledWith("2026-10-15");
  });

  it("stays on today while another month and date are selected, with one goal group", async () => {
    const panel = await start();
    expect(await panel.findByRole("button", { name: "오늘 작업" })).toBeInTheDocument();
    expect(panel.getAllByRole("heading", { name: "목표" })).toHaveLength(1);
    await act(async () => { useCalendarStore.setState({ selectedDate: "2027-01-10", visibleDate: "2027-01-10" }); });
    expect(panel.getByText("2026-10-15")).toBeInTheDocument();
    expect(panel.getByRole("button", { name: "오늘 작업" })).toBeInTheDocument();
  });

  it("optimistically toggles, blocks duplicate clicks, and keeps other milestones usable", async () => {
    const saving = deferred<Milestone>();
    vi.mocked(apiClient.completeMilestone).mockReturnValueOnce(saving.promise);
    const panel = await start();
    const toggle = await panel.findByRole("button", { name: "오늘 작업" });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(toggle).toBeDisabled();
    fireEvent.click(toggle);
    expect(apiClient.completeMilestone).toHaveBeenCalledTimes(1);
    expect(panel.getByRole("button", { name: "다른 작업" })).toBeEnabled();
    await act(async () => saving.resolve({ ...milestone, is_completed: true }));
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    expect(panel.getAllByRole("button")[0]).toBe(toggle);
    await waitFor(() => expect(toggle).toBeEnabled());
  });

  it("rolls back the panel and shared date cache after failure", async () => {
    const saving = deferred<Milestone>();
    vi.mocked(apiClient.completeMilestone).mockReturnValueOnce(saving.promise);
    const panel = await start();
    const toggle = await panel.findByRole("button", { name: "오늘 작업" });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
    await act(async () => saving.reject(new Error("save failed")));
    expect(toggle).toHaveAttribute("aria-pressed", "false");
    act(() => { useCalendarStore.setState({ selectedDate: "2026-10-15", visibleDate: "2026-10-15" }); useUiStore.getState().openDayView(); });
    await waitFor(() => expect(screen.getByRole("dialog")).toBeInTheDocument());
    expect(screen.getByRole("dialog").querySelector(".done")).toBeNull();
  });

  it("changes today at the user's midnight and discards the previous day", async () => {
    const panel = await start();
    await panel.findByRole("button", { name: "오늘 작업" });
    act(() => { vi.setSystemTime(new Date("2026-10-16T00:00:01+09:00")); window.dispatchEvent(new Event("focus")); });
    await waitFor(() => expect(panel.getByText("2026-10-16")).toBeInTheDocument());
    await waitFor(() => expect(apiClient.getDateCalendar).toHaveBeenCalledWith("2026-10-16"));
    expect(panel.queryByRole("button", { name: "오늘 작업" })).not.toBeInTheDocument();
  });

  it("shows a retry action after a today query fails", async () => {
    vi.mocked(apiClient.getDateCalendar).mockRejectedValueOnce(new Error("offline"));
    const panel = await start();
    fireEvent.click(await panel.findByRole("button", { name: "다시 시도" }));
    expect(await panel.findByRole("button", { name: "오늘 작업" })).toBeInTheDocument();
  });

  it("restores the setting and panel when saving the local option fails", async () => {
    const panel = await start();
    await panel.findByRole("button", { name: "오늘 작업" });
    vi.mocked(window.mileday!.uiSettings!.setTodaySidePanelEnabled).mockRejectedValueOnce(new Error("disk full"));
    act(() => useUiStore.getState().openSettings());
    fireEvent.click(screen.getByRole("checkbox", { name: "오늘의 사이드 패널" }));
    await waitFor(() => expect(screen.getByRole("checkbox", { name: "오늘의 사이드 패널" })).toBeChecked());
    expect(await screen.findByRole("alert")).toHaveTextContent("저장하지 못했습니다");
    expect(screen.getByRole("complementary")).toBeInTheDocument();
  });

  it("keeps successful changes when a different concurrent milestone fails", async () => {
    const first = deferred<Milestone>();
    const second = deferred<Milestone>();
    vi.mocked(apiClient.completeMilestone).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise);
    const panel = await start();
    const one = await panel.findByRole("button", { name: "오늘 작업" });
    const two = panel.getByRole("button", { name: "다른 작업" });
    fireEvent.click(one);
    fireEvent.click(two);
    await act(async () => second.resolve({ ...milestone, id: "m2", title: "다른 작업", is_completed: true }));
    await act(async () => first.reject(new Error("failed")));
    expect(one).toHaveAttribute("aria-pressed", "false");
    expect(two).toHaveAttribute("aria-pressed", "true");
  });

  it("reflects the server's final completion value instead of assuming the requested value", async () => {
    vi.mocked(apiClient.completeMilestone).mockResolvedValueOnce({ ...milestone, is_completed: false });
    const panel = await start();
    const toggle = await panel.findByRole("button", { name: "오늘 작업" });
    fireEvent.click(toggle);
    await waitFor(() => expect(toggle).toBeEnabled());
    expect(toggle).toHaveAttribute("aria-pressed", "false");
  });

  it("discards pending today data on logout and on login to another account", async () => {
    const oldRequest = deferred<CalendarDateData>();
    vi.mocked(apiClient.getDateCalendar).mockReturnValueOnce(oldRequest.promise);
    vi.spyOn(apiClient, "logout").mockResolvedValue(undefined);
    vi.spyOn(apiClient, "login").mockResolvedValue({ access_token: "new", refresh_token: "new", token_type: "bearer", user: { id: "new", email: "new@example.com" } });
    await start();
    await waitFor(() => expect(apiClient.getDateCalendar).toHaveBeenCalledWith("2026-10-15"));
    act(() => useUiStore.getState().openSettings());
    fireEvent.click(screen.getByRole("button", { name: "로그아웃" }));
    await screen.findByRole("heading", { name: "로그인" });
    vi.mocked(apiClient.listGoals).mockResolvedValue([]);
    vi.mocked(apiClient.getDateCalendar).mockImplementation(async (date) => ({ ...detail(date), goals: [], milestones: [] }));
    fireEvent.change(screen.getByLabelText("이메일"), { target: { value: "new@example.com" } });
    fireEvent.change(screen.getByLabelText("비밀번호", { selector: "input" }), { target: { value: "password123" } });
    fireEvent.click(screen.getAllByRole("button", { name: "로그인" }).at(-1)!);
    const newPanel = within(await screen.findByRole("complementary"));
    await newPanel.findByText("오늘 예정된 일정이 없습니다.");
    await act(async () => oldRequest.resolve(detail("2026-10-15")));
    expect(newPanel.queryByText("오늘 작업")).not.toBeInTheDocument();
  });

  it("updates today's panel after adding a milestone while a future date is selected", async () => {
    const created = { ...milestone, id: "new", title: "추가한 작업" };
    vi.spyOn(apiClient, "createMilestone").mockImplementation(async () => {
      vi.mocked(apiClient.getDateCalendar).mockImplementation(async (date) => date === "2026-10-15" ? { ...detail(date), milestones: [...detail(date).milestones, created] } : detail(date));
      return created;
    });
    const panel = await start();
    await panel.findByRole("button", { name: "오늘 작업" });
    act(() => useUiStore.getState().openManualCreate());
    fireEvent.click(screen.getByRole("button", { name: "기존 목표에 추가" }));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "g" } });
    fireEvent.click(screen.getByRole("button", { name: "세부 마일스톤 추가" }));
    fireEvent.change(screen.getByLabelText("이름"), { target: { value: created.title } });
    fireEvent.change(screen.getByLabelText("날짜"), { target: { value: "2026-10-15" } });
    fireEvent.click(screen.getByRole("button", { name: "일정 추가" }));
    expect(await panel.findByRole("button", { name: created.title })).toBeInTheDocument();
    expect(apiClient.createMilestone).toHaveBeenCalledWith("g", expect.objectContaining({ title: created.title, scheduled_date: "2026-10-15" }));
  });

  it("keeps due goals with no milestones visible without a goal completion toggle", async () => {
    vi.mocked(apiClient.getDateCalendar).mockResolvedValue({ ...detail("2026-10-15"), milestones: [], milestone_count: 0 });
    const panel = await start();
    expect(await panel.findByRole("heading", { name: "목표" })).toBeInTheDocument();
    expect(panel.getByText("오늘 마감")).toBeInTheDocument();
    expect(panel.queryAllByRole("button")).toHaveLength(0);
  });
});
