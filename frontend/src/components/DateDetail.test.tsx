import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { CalendarDateData, Goal } from "@/api/types";

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
      onToggleGoal={vi.fn()}
      onToggleMilestone={vi.fn()}
      onUpdateGoal={vi.fn().mockResolvedValue(undefined)}
      onDeleteGoal={vi.fn().mockResolvedValue(undefined)}
      onCreateMilestone={vi.fn().mockResolvedValue(undefined)}
      onUpdateMilestone={vi.fn().mockResolvedValue(undefined)}
      onDeleteMilestone={vi.fn().mockResolvedValue(undefined)}
      {...overrides}
    />,
  );
}

describe("DateDetail", () => {
  it("allows editing a goal even when the goal has milestones", async () => {
    const user = userEvent.setup();
    const onUpdateGoal = vi.fn().mockResolvedValue(undefined);
    renderDateDetail({
      language: "en",
      onUpdateGoal,
      detail: {
        ...detail,
        goals: [{ ...detail.goals[0], title: "Portfolio work" }],
        milestones: [{ ...detail.milestones[0], title: "Draft content", goal_title: "Portfolio work" }],
      },
    });

    await user.click(screen.getByRole("button", { name: /Portfolio work/ }));
    const editor = screen.getByLabelText("Deadline").closest("form") as HTMLElement;

    await user.clear(within(editor).getByLabelText("Title"));
    await user.type(within(editor).getByLabelText("Title"), "Updated portfolio work");
    await user.click(within(editor).getByRole("button", { name: "Save" }));

    expect(onUpdateGoal).toHaveBeenCalledWith("goal-1", {
      title: "Updated portfolio work",
      deadline: "2026-07-10",
      color: "#0F766E",
      is_recurring: false,
      recurrence_type: null,
    });
  });

  it("opens goal editing from the goal row pencil when the goal has milestones", async () => {
    const user = userEvent.setup();
    renderDateDetail({
      language: "en",
      detail: {
        ...detail,
        goals: [{ ...detail.goals[0], title: "Childcare" }],
        milestones: [{ ...detail.milestones[0], title: "Go to center", goal_title: "Childcare" }],
      },
    });

    await user.click(screen.getByTitle("Edit goal"));

    expect(screen.getByDisplayValue("Childcare")).toBeInTheDocument();
    expect(screen.getByLabelText("Deadline")).toBeInTheDocument();
  });

  it("allows deleting a goal when the goal has no milestones", async () => {
    const user = userEvent.setup();
    const onDeleteGoal = vi.fn().mockResolvedValue(undefined);
    renderDateDetail({
      language: "en",
      onDeleteGoal,
      detail: {
        ...detail,
        milestone_count: 0,
        completed_milestone_count: 0,
        goals: [{ ...detail.goals[0], title: "Inbox cleanup" }],
        milestones: [],
      },
    });

    await user.click(screen.getByTitle("Edit goal"));
    await user.click(screen.getByRole("button", { name: "Delete" }));

    expect(onDeleteGoal).toHaveBeenCalledWith("goal-1");
  });

  it("단일 목표에는 완료 체크를 표시하고 목표 완료를 전달한다", async () => {
    const user = userEvent.setup();
    const onToggleGoal = vi.fn();
    renderDateDetail({
      onToggleGoal,
      detail: {
        ...detail,
        milestone_count: 0,
        completed_milestone_count: 0,
        milestones: [],
      },
    });

    await user.click(screen.getByTestId("goal-toggle"));

    expect(onToggleGoal).toHaveBeenCalledWith("goal-1", true);
  });

  it("마일스톤이 있는 목표에는 목표 완료 체크를 표시하지 않는다", () => {
    renderDateDetail();

    expect(screen.queryByTestId("goal-toggle")).not.toBeInTheDocument();
    expect(screen.getByTestId("milestone-toggle")).toBeInTheDocument();
  });

  it("목표 마감일이 아닌 날짜의 하루 보기에서도 해당 목표를 눌러 수정할 수 있다", async () => {
    const user = userEvent.setup();
    const onUpdateGoal = vi.fn().mockResolvedValue(undefined);
    const otherDateGoal: Goal = {
      id: "goal-2",
      title: "장기 프로젝트",
      deadline: "2026-07-31",
      is_completed: false,
      color: "#8B6FD6",
      is_recurring: false,
      recurrence_type: null,
      created_at: "2026-07-01T00:00:00Z",
      updated_at: "2026-07-01T00:00:00Z",
    };

    renderDateDetail({
      goals: [otherDateGoal],
      detail: {
        date: "2026-07-10",
        is_today: false,
        goal_count: 0,
        milestone_count: 1,
        completed_milestone_count: 0,
        goals: [],
        milestones: [
          {
            id: "milestone-2",
            goal_id: "goal-2",
            goal_title: "장기 프로젝트",
            title: "중간 보고서 작성",
            color: "#8B6FD6",
            scheduled_date: "2026-07-10",
            is_completed: false,
          },
        ],
      },
      onUpdateGoal,
    });

    const goalSection = screen.getByRole("heading", { name: "목표" }).closest(".section-block") as HTMLElement | null;
    expect(goalSection).not.toBeNull();

    await user.click(within(goalSection!).getByRole("button", { name: /장기 프로젝트/ }));
    const editor = screen.getByLabelText("마감일").closest("form");
    expect(editor).not.toBeNull();
    expect(screen.getByDisplayValue("장기 프로젝트")).toBeInTheDocument();
    expect(screen.getByDisplayValue("2026-07-31")).toBeInTheDocument();

    await user.clear(within(editor!).getByLabelText("제목"));
    await user.type(within(editor!).getByLabelText("제목"), "장기 프로젝트 v2");
    await user.click(within(editor!).getByRole("button", { name: "저장" }));

    expect(onUpdateGoal).toHaveBeenCalledWith("goal-2", {
      title: "장기 프로젝트 v2",
      deadline: "2026-07-31",
      color: "#8B6FD6",
      is_recurring: false,
      recurrence_type: null,
    });
  });

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

  it("마감 목표가 없는 날짜의 마일스톤도 연결 목표를 목표 집계에 포함한다", () => {
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
    expect(screen.queryByText("오늘은 일정이 없습니다.")).not.toBeInTheDocument();
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
