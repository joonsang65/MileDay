import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { Goal, Milestone } from "@/api/types";
import { apiClient } from "@/api/client";

import { GoalListModal } from "./GoalListModal";

vi.mock("@/api/client", () => ({
  apiClient: {
    listGoalsWithMilestones: vi.fn(),
  },
}));

const goal: Goal = {
  id: "goal-1",
  user_id: "user-1",
  title: "포트폴리오 준비",
  deadline: "2026-07-31",
  is_completed: false,
  is_recurring: false,
  recurrence_type: null,
  color: "#0F766E",
  created_at: "2026-07-01T10:00:00+09:00",
  updated_at: "2026-07-01T10:00:00+09:00",
};

const milestone: Milestone = {
  id: "milestone-1",
  goal_id: "goal-1",
  user_id: "user-1",
  title: "이력서 초안 작성",
  color: "#0F766E",
  scheduled_date: "2026-07-10",
  is_completed: false,
  created_at: "2026-07-01T10:00:00+09:00",
  updated_at: "2026-07-01T10:00:00+09:00",
};

function renderGoalList(overrides = {}) {
  return render(
    <GoalListModal
      language="ko"
      initialGoals={[goal]}
      onClose={vi.fn()}
      onUpdateGoal={vi.fn().mockResolvedValue(undefined)}
      onDeleteGoal={vi.fn().mockResolvedValue(undefined)}
      onCreateMilestone={vi.fn().mockResolvedValue(undefined)}
      onToggleGoal={vi.fn().mockResolvedValue(undefined)}
      onToggleMilestone={vi.fn().mockResolvedValue(undefined)}
      onUpdateMilestone={vi.fn().mockResolvedValue(undefined)}
      onDeleteMilestone={vi.fn().mockResolvedValue(undefined)}
      {...overrides}
    />,
  );
}

describe("GoalListModal", () => {
  beforeEach(() => {
    vi.mocked(apiClient.listGoalsWithMilestones).mockReset();
    vi.mocked(apiClient.listGoalsWithMilestones).mockResolvedValue([
      { ...goal, milestones: [milestone] },
    ]);
  });

  it("진행중 패널에서만 목표 완료 체크를 표시하고 목표 완료를 전달한다", async () => {
    const user = userEvent.setup();
    const onToggleGoal = vi.fn().mockResolvedValue(undefined);
    renderGoalList({ onToggleGoal });

    await waitFor(() => expect(screen.getByText("포트폴리오 준비")).toBeInTheDocument());
    await user.click(screen.getByTitle("목표 완료"));

    expect(onToggleGoal).toHaveBeenCalledWith("goal-1", true);

    await user.click(screen.getByRole("button", { name: "전체" }));

    expect(screen.queryByTitle("목표 완료")).not.toBeInTheDocument();
  });

  it("마일스톤이 없는 단일 목표도 완료 체크 요청을 처리한다", async () => {
    const user = userEvent.setup();
    const onToggleGoal = vi.fn().mockResolvedValue(undefined);
    vi.mocked(apiClient.listGoalsWithMilestones).mockResolvedValue([
      { ...goal, milestones: [] },
    ]);
    renderGoalList({ onToggleGoal });

    await waitFor(() => expect(screen.getByText("포트폴리오 준비")).toBeInTheDocument());
    await user.click(screen.getByTitle("목표 완료"));

    expect(onToggleGoal).toHaveBeenCalledWith("goal-1", true);
    await waitFor(() => expect(screen.getByText("포트폴리오 준비")).toBeInTheDocument());
    expect(screen.queryByTitle("목표 완료")).not.toBeInTheDocument();
  });

  it("초기 목표 목록이 비어 있어도 API에서 목표와 마일스톤을 불러와 표시한다", async () => {
    renderGoalList({ initialGoals: [] });

    await waitFor(() => expect(screen.getByText("포트폴리오 준비")).toBeInTheDocument());
    await userEvent.click(screen.getByRole("button", { name: /포트폴리오 준비/ }));

    expect(screen.getByText("이력서 초안 작성")).toBeInTheDocument();
    expect(apiClient.listGoalsWithMilestones).toHaveBeenCalledTimes(1);
  });
});
