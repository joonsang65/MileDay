import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CalendarBoard } from "./CalendarBoard";

describe("CalendarBoard", () => {
  it.each(["month", "week"] as const)("keeps deadline-only goals alongside milestones in %s view", (mode) => {
    const goal = { id: "g", title: "목표 마감", deadline: "2026-07-10", is_completed: false, is_recurring: false, recurrence_type: null, color: "#7F9278", created_at: "", updated_at: "" };
    render(<CalendarBoard mode={mode} visibleDate="2026-07-10" selectedDate="2026-07-10" weekStartsOn={1} holidayDisplay="hidden" onSelectDate={vi.fn()}
      days={[{ date: "2026-07-10", is_today: false, goal_count: 1, milestone_count: 1, completed_milestone_count: 0, goals: [goal], milestones: [{ id: "m", goal_id: "another-goal", title: "긴 마일스톤 제목 전체 확인", color: "#D97706", scheduled_date: "2026-07-10", is_completed: false }] }]} />);
    expect(screen.getByText("마감: 목표 마감")).toBeInTheDocument();
    expect(screen.getByTitle("긴 마일스톤 제목 전체 확인")).toBeInTheDocument();
  });

  it("shows each milestone title and completion style in the month calendar", async () => {
    const onSelectDate = vi.fn();
    render(
      <CalendarBoard
        mode="month"
        visibleDate="2026-07-10"
        selectedDate="2026-07-10"
        weekStartsOn={1}
        holidayDisplay="normal"
        onSelectDate={onSelectDate}
        days={[
          {
            date: "2026-07-10",
            is_today: true,
            is_holiday: true,
            holiday_name: "광복절",
            goal_count: 1,
            milestone_count: 2,
            completed_milestone_count: 1,
            goals: [
              {
                id: "goal-1",
                title: "아동센터 작성",
                deadline: "2026-07-10",
                is_completed: false,
                is_recurring: false,
                recurrence_type: null,
                color: "#0F766E",
                created_at: "2026-07-01T10:00:00+09:00",
                updated_at: "2026-07-01T10:00:00+09:00",
              },
            ],
            milestones: [
              {
                id: "milestone-1",
                goal_id: "goal-1",
                goal_title: "아동센터 작성",
                title: "초안 작성",
                color: "#D97706",
                scheduled_date: "2026-07-10",
                is_completed: false,
              },
              {
                id: "milestone-2",
                goal_id: "goal-1",
                goal_title: "아동센터 작성",
                title: "검토",
                color: "#E11D48",
                scheduled_date: "2026-07-10",
                is_completed: true,
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.queryByText("목표 1")).not.toBeInTheDocument();
    expect(screen.queryByText("작업 1/2")).not.toBeInTheDocument();
    expect(screen.getByText("광복절")).toBeInTheDocument();
    expect(screen.queryByText("아동센터 작성 1/2")).not.toBeInTheDocument();
    expect(screen.getByTitle("초안 작성")).toBeInTheDocument();
    expect(screen.getByText("검토")).toHaveClass("done-event");

    await userEvent.click(screen.getByRole("button", { name: /10 광복절/i }));
    expect(onSelectDate).toHaveBeenCalledWith("2026-07-10");
  });

  it("shows milestone titles without requiring a goal on the same day", () => {
    render(
      <CalendarBoard
        mode="month"
        visibleDate="2026-07-10"
        selectedDate="2026-07-11"
        weekStartsOn={0}
        holidayDisplay="hidden"
        onSelectDate={vi.fn()}
        days={[
          {
            date: "2026-07-11",
            is_today: false,
            is_holiday: true,
            holiday_name: "숨김 휴일",
            goal_count: 0,
            milestone_count: 1,
            completed_milestone_count: 0,
            goals: [],
            milestones: [
              {
                id: "milestone-1",
                goal_id: "goal-1",
                goal_title: "프로그램 일지",
                title: "제출",
                color: "#D97706",
                scheduled_date: "2026-07-11",
                is_completed: false,
              },
            ],
          },
        ]}
      />,
    );

    expect(screen.queryByText("목표 1")).not.toBeInTheDocument();
    expect(screen.queryByText("작업 0/1")).not.toBeInTheDocument();
    expect(screen.queryByText("프로그램 일지 0/1")).not.toBeInTheDocument();
    expect(screen.queryByText("숨김 휴일")).not.toBeInTheDocument();
    expect(screen.getByText("제출")).toBeInTheDocument();
  });

  it("marks saturday blue and keeps sunday separate from holidays", () => {
    render(
      <CalendarBoard
        mode="week"
        visibleDate="2026-07-11"
        selectedDate="2026-07-11"
        weekStartsOn={0}
        holidayDisplay="hidden"
        onSelectDate={vi.fn()}
        days={[]}
      />,
    );

    expect(screen.getByText("일")).toHaveClass("sunday");
    expect(screen.getByText("토")).toHaveClass("saturday");
    expect(screen.getByRole("button", { name: "11" })).toHaveClass("saturday");
    expect(screen.getByRole("button", { name: "12" })).toHaveClass("sunday");
    expect(screen.getByRole("button", { name: "11" })).not.toHaveClass("holiday");
  });
});
