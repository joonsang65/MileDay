import { performance } from "node:perf_hooks";

import {
  config,
  createGoalViaApi,
  getMilestoneForm,
  openMilestoneForm,
  reloadCalendarReady,
  runPerfFlow,
  todayDateKey,
} from "./perf_lib.mjs";

await runPerfFlow({
  flow: "milestone_create_to_ui_visible",
  filePrefix: "milestone-create",
  summaryTitle: "Milestone create latency summary",
  runIteration: async ({ page, iteration, markApiStart }) => {
    const date = todayDateKey();
    const goalTitle = `perf milestone goal ${Date.now()}-${iteration}`;
    const milestoneTitle = `perf milestone ${Date.now()}-${iteration}`;
    const goal = await createGoalViaApi(page, { title: goalTitle, deadline: date });

    await reloadCalendarReady(page);
    await openMilestoneForm(page);
    const milestoneForm = getMilestoneForm(page);
    await milestoneForm.getByLabel("목표").selectOption(goal.id);
    await milestoneForm.getByLabel("제목").fill(milestoneTitle);
    await milestoneForm.getByLabel("예정일").fill(date);

    markApiStart();
    const startedAt = performance.now();
    const createdMilestone = page.getByText(milestoneTitle, { exact: true }).first();
    await Promise.all([
      createdMilestone.waitFor({
        state: "visible",
        timeout: config.timeoutMs,
      }),
      milestoneForm.getByRole("button", { name: /마일스톤 추가|추가 중/ }).click(),
    ]);

    return {
      duration_ms: performance.now() - startedAt,
      label: milestoneTitle,
      title: milestoneTitle,
      goal_title: goalTitle,
      goal_id: goal.id,
    };
  },
});
