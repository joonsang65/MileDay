import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CalendarBoard } from "./CalendarBoard";

describe("CalendarBoard", () => {
  it("shows holiday and goal progress text without aggregate metric badges", async () => {
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
    expect(screen.getByText("아동센터 작성 1/2")).toBeInTheDocument();
    expect(screen.queryByText("초안 작성")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /10 광복절/i }));
    expect(onSelectDate).toHaveBeenCalledWith("2026-07-10");
  });

  it("groups orphan milestone text by goal title while individual milestone titles stay hidden", () => {
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
    expect(screen.getByText("프로그램 일지 0/1")).toBeInTheDocument();
    expect(screen.queryByText("숨김 휴일")).not.toBeInTheDocument();
    expect(screen.queryByText("제출")).not.toBeInTheDocument();
  });
});
