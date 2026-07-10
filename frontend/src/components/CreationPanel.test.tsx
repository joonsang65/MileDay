import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { Goal } from "@/api/types";

import { CreationPanel } from "./CreationPanel";

const goals: Goal[] = [
  {
    id: "goal-1",
    title: "포트폴리오 준비",
    deadline: "2026-07-31",
    is_recurring: false,
    recurrence_type: null,
    color: "#0F766E",
    created_at: "2026-07-01T10:00:00+09:00",
    updated_at: "2026-07-01T10:00:00+09:00",
  },
];

describe("CreationPanel", () => {
  it("접힌 상태에서 시작하고 필요할 때 목표 생성 payload를 만든다", async () => {
    const user = userEvent.setup();
    const onCreateGoal = vi.fn().mockResolvedValue(undefined);

    render(
      <CreationPanel
        goals={goals}
        selectedDate="2026-07-10"
        isLoading={false}
        onCreateGoal={onCreateGoal}
        onCreateMilestones={vi.fn()}
      />,
    );

    expect(screen.queryByRole("button", { name: "목표 추가" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "빠른 추가" }));
    await user.type(screen.getByLabelText("제목"), "운동");
    await user.click(screen.getByRole("button", { name: "목표 추가" }));

    expect(onCreateGoal).toHaveBeenCalledWith({
      title: "운동",
      deadline: "2026-07-10",
      is_recurring: false,
      recurrence_type: null,
      color: "#0F766E",
    });
  });

  it("마일스톤 반복 설정을 실제 여러 payload로 만든다", async () => {
    const user = userEvent.setup();
    const onCreateMilestones = vi.fn().mockResolvedValue(undefined);

    render(
      <CreationPanel
        goals={goals}
        selectedDate="2026-07-10"
        isLoading={false}
        onCreateGoal={vi.fn()}
        onCreateMilestones={onCreateMilestones}
      />,
    );

    await user.click(screen.getByRole("button", { name: "빠른 추가" }));
    await user.click(screen.getByRole("button", { name: "마일스톤 추가" }));

    const milestoneForm = screen.getByRole("button", { name: "마일스톤 추가" }).closest("form");
    expect(milestoneForm).not.toBeNull();
    await user.type(within(milestoneForm!).getByLabelText("제목"), "이력서 초안 작성");
    await user.click(within(milestoneForm!).getByLabelText("반복 마일스톤"));
    await user.selectOptions(within(milestoneForm!).getByLabelText("반복 주기"), "weekly");
    await user.clear(within(milestoneForm!).getByLabelText("반복 종료일"));
    await user.type(within(milestoneForm!).getByLabelText("반복 종료일"), "2026-07-24");
    await user.click(within(milestoneForm!).getByRole("button", { name: "마일스톤 추가" }));

    expect(onCreateMilestones).toHaveBeenCalledWith("goal-1", [
      {
        title: "이력서 초안 작성",
        scheduled_date: "2026-07-10",
        color: "#D97706",
      },
      {
        title: "이력서 초안 작성",
        scheduled_date: "2026-07-17",
        color: "#D97706",
      },
      {
        title: "이력서 초안 작성",
        scheduled_date: "2026-07-24",
        color: "#D97706",
      },
    ]);
  });

  it("목표가 없으면 마일스톤 생성 토글을 비활성화한다", async () => {
    const user = userEvent.setup();

    render(
      <CreationPanel
        goals={[]}
        selectedDate="2026-07-10"
        isLoading={false}
        onCreateGoal={vi.fn()}
        onCreateMilestones={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "빠른 추가" }));

    expect(screen.getByRole("button", { name: "마일스톤 추가" })).toBeDisabled();
  });

  it("반복 종료일이 시작일보다 빠르면 마일스톤 API를 호출하지 않는다", async () => {
    const user = userEvent.setup();
    const onCreateMilestones = vi.fn().mockResolvedValue(undefined);

    render(
      <CreationPanel
        goals={goals}
        selectedDate="2026-07-10"
        isLoading={false}
        onCreateGoal={vi.fn()}
        onCreateMilestones={onCreateMilestones}
      />,
    );

    await user.click(screen.getByRole("button", { name: "빠른 추가" }));
    await user.click(screen.getByRole("button", { name: "마일스톤 추가" }));

    const milestoneForm = screen.getByRole("button", { name: "마일스톤 추가" }).closest("form") as HTMLElement;
    await user.type(within(milestoneForm).getByLabelText("제목"), "이력서 초안 작성");
    await user.click(within(milestoneForm).getByLabelText("반복 마일스톤"));
    await user.clear(within(milestoneForm).getByLabelText("반복 종료일"));
    await user.type(within(milestoneForm).getByLabelText("반복 종료일"), "2026-07-01");
    await user.click(within(milestoneForm).getByRole("button", { name: "마일스톤 추가" }));

    expect(screen.getByText("반복 종료일은 시작일 이후여야 합니다.")).toBeInTheDocument();
    expect(onCreateMilestones).not.toHaveBeenCalled();
  });

  it("로딩 중에는 추가 버튼과 입력을 비활성화한다", async () => {
    const user = userEvent.setup();

    render(
      <CreationPanel
        goals={goals}
        selectedDate="2026-07-10"
        isLoading
        onCreateGoal={vi.fn()}
        onCreateMilestones={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "빠른 추가" }));

    expect(screen.getByLabelText("제목")).toBeDisabled();
    expect(screen.getByRole("button", { name: "추가 중" })).toBeDisabled();
  });
});
