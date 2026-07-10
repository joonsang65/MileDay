import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CalendarDateData } from "@/api/types";

import { DateDetail } from "./DateDetail";

const detail: CalendarDateData = {
  date: "2026-07-10",
  is_today: false,
  goal_count: 1,
  milestone_count: 1,
  completed_milestone_count: 0,
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
      user_id: "user-1",
      goal_title: "포트폴리오 준비",
      title: "이력서 초안 작성",
      color: "#D97706",
      scheduled_date: "2026-07-10",
      is_completed: false,
      created_at: "2026-07-01T10:00:00+09:00",
      updated_at: "2026-07-01T10:00:00+09:00",
    },
  ],
};

function renderDateDetail(overrides = {}) {
  return render(
    <DateDetail
      detail={detail}
      isLoading={false}
      onToggleMilestone={vi.fn()}
      onUpdateGoal={vi.fn().mockResolvedValue(undefined)}
      onDeleteGoal={vi.fn().mockResolvedValue(undefined)}
      onUpdateMilestone={vi.fn().mockResolvedValue(undefined)}
      onDeleteMilestone={vi.fn().mockResolvedValue(undefined)}
      {...overrides}
    />,
  );
}

describe("DateDetail", () => {
  it("목표 row를 누르면 수정 폼이 열리고 저장 payload를 전달한다", async () => {
    const user = userEvent.setup();
    const onUpdateGoal = vi.fn().mockResolvedValue(undefined);
    renderDateDetail({ onUpdateGoal });

    const goalSection = screen.getByRole("heading", { name: "목표" }).closest(".section-block") as HTMLElement | null;
    expect(goalSection).not.toBeNull();

    await user.click(within(goalSection!).getByRole("button", { name: /포트폴리오 준비/ }));
    const editor = screen.getByLabelText("마감일").closest("form");
    expect(editor).not.toBeNull();

    await user.clear(within(editor!).getByLabelText("제목"));
    await user.type(within(editor!).getByLabelText("제목"), "프로젝트 마감");
    await user.click(within(editor!).getByRole("button", { name: "저장" }));

    expect(onUpdateGoal).toHaveBeenCalledWith("goal-1", {
      title: "프로젝트 마감",
      deadline: "2026-07-10",
      color: "#0F766E",
      is_recurring: false,
      recurrence_type: null,
    });
  });

  it("마일스톤 row를 누르면 수정 폼이 열리고 삭제를 전달한다", async () => {
    const user = userEvent.setup();
    const onDeleteMilestone = vi.fn().mockResolvedValue(undefined);
    renderDateDetail({ onDeleteMilestone });

    await user.click(screen.getByRole("button", { name: /이력서 초안 작성/ }));
    await user.click(screen.getByRole("button", { name: "삭제" }));

    expect(onDeleteMilestone).toHaveBeenCalledWith("milestone-1");
  });

  it("마감 목표가 없는 날짜도 마일스톤의 연결 목표를 목표 집계에 포함한다", () => {
    renderDateDetail({
      detail: {
        ...detail,
        goal_count: 0,
        goals: [],
        milestones: [
          {
            ...detail.milestones[0],
            goal_title: "프로그램 일지",
            title: "제출",
          },
        ],
      },
    });

    expect(screen.getByText("목표 1")).toBeInTheDocument();
    expect(screen.getAllByText("작업 0/1")).toHaveLength(2);
    expect(screen.getByText("프로그램 일지")).toBeInTheDocument();
    expect(screen.getByText("제출")).toBeInTheDocument();
    expect(screen.queryByText("연결된 목표가 없습니다.")).not.toBeInTheDocument();
  });

  it("수정 폼의 제목이 공백이면 저장 API를 호출하지 않는다", async () => {
    const user = userEvent.setup();
    const onUpdateGoal = vi.fn().mockResolvedValue(undefined);
    renderDateDetail({ onUpdateGoal });

    const goalSection = screen.getByRole("heading", { name: "목표" }).closest(".section-block") as HTMLElement;
    await user.click(within(goalSection).getByRole("button", { name: /포트폴리오 준비/ }));

    const editor = screen.getByLabelText("마감일").closest("form") as HTMLElement;
    await user.clear(within(editor).getByLabelText("제목"));
    await user.click(within(editor).getByRole("button", { name: "저장" }));

    expect(screen.getByText("목표 제목을 입력해 주세요.")).toBeInTheDocument();
    expect(onUpdateGoal).not.toHaveBeenCalled();
  });

  it("로딩 중에는 수정/삭제 버튼을 비활성화한다", async () => {
    const user = userEvent.setup();
    renderDateDetail({ isLoading: true });

    const goalSection = screen.getByRole("heading", { name: "목표" }).closest(".section-block") as HTMLElement;
    await user.click(within(goalSection).getByRole("button", { name: /포트폴리오 준비/ }));

    expect(screen.getByRole("button", { name: "저장 중" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "삭제 중" })).toBeDisabled();
  });
});
