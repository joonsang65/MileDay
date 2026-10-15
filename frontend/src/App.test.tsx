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
  vi.spyOn(apiClient, "getSettings").mockResolvedValue(DEFAULT_USER_SETTINGS);
  vi.spyOn(apiClient, "listGoals").mockResolvedValue([goal]);
  vi.spyOn(apiClient, "listGoalsWithMilestones").mockResolvedValue([{ ...goal, milestones: [milestone] }]);
  vi.spyOn(apiClient, "getDateCalendar").mockImplementation(async (date) => detail(date));
  vi.spyOn(apiClient, "getMonthCalendar").mockImplementation(async (year, month) => ({ year, month, days: [detail(`${year}-${String(month).padStart(2, "0")}-10`)], goals: [], milestones: [] }));
  vi.spyOn(apiClient, "completeMilestone").mockImplementation(async (id, completed) => ({ ...milestone, id, is_completed: completed }));
  window.mileday = { platform: "win32", uiSettings: { get: vi.fn().mockResolvedValue(localSettings()), setTodaySidePanelEnabled: vi.fn().mockImplementation(async (enabled) => localSettings(enabled)) } } as unknown as NonNullable<Window["mileday"]>;
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
