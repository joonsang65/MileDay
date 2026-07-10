import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CalendarBoard } from "./CalendarBoard";

describe("CalendarBoard", () => {
  it("목표와 마일스톤 집계를 날짜 칸에 표시하고 날짜 선택을 전달한다", async () => {
    const onSelectDate = vi.fn();
    render(
      <CalendarBoard
        mode="month"
        visibleDate="2026-07-10"
        selectedDate="2026-07-10"
        onSelectDate={onSelectDate}
        days={[
          {
            date: "2026-07-10",
            is_today: true,
            goal_count: 1,
            milestone_count: 2,
            completed_milestone_count: 1,
            goals: [
              {
                id: "goal-1",
                title: "포트폴리오 준비",
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
                goal_title: "포트폴리오 준비",
                title: "이력서 초안 작성",
                color: "#D97706",
                scheduled_date: "2026-07-10",
                is_completed: false,
              },
              {
                id: "milestone-2",
                goal_id: "goal-1",
                goal_title: "포트폴리오 준비",
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

    expect(screen.getByText("목표 1")).toBeInTheDocument();
    expect(screen.getByText("작업 1/2")).toBeInTheDocument();
    expect(screen.getByText("포트폴리오 준비 작업 1/2")).toBeInTheDocument();
    expect(screen.queryByText("이력서 초안 작성")).not.toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: /10 목표 1 작업 1\/2/i }));
    expect(onSelectDate).toHaveBeenCalledWith("2026-07-10");
  });

  it("마일스톤만 있는 날짜도 연결된 목표 단위로 묶어 보여준다", () => {
    render(
      <CalendarBoard
        mode="month"
        visibleDate="2026-07-10"
        selectedDate="2026-07-11"
        onSelectDate={vi.fn()}
        days={[
          {
            date: "2026-07-11",
            is_today: false,
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

    expect(screen.getByText("목표 1")).toBeInTheDocument();
    expect(screen.getByText("작업 0/1")).toBeInTheDocument();
    expect(screen.getByText("프로그램 일지 작업 0/1")).toBeInTheDocument();
    expect(screen.queryByText("제출")).not.toBeInTheDocument();
  });
});
