import { performance } from "node:perf_hooks";

import {
  config,
  createGoalViaApi,
  createMilestoneViaApi,
  reloadCalendarReady,
  runPerfFlow,
  todayDateKey,
} from "./perf_lib.mjs";

await runPerfFlow({
  flow: "milestone_api_create_to_ui_visible",
  filePrefix: "milestone-create",
  summaryTitle: "Milestone create latency summary",
  runIteration: async ({ page, iteration, markApiStart }) => {
    const date = todayDateKey();
    const goalTitle = `perf milestone goal ${Date.now()}-${iteration}`;
    const milestoneTitle = `perf milestone ${Date.now()}-${iteration}`;
    const goal = await createGoalViaApi(page, { title: goalTitle, deadline: date });

    markApiStart();
    const startedAt = performance.now();
    const milestone = await createMilestoneViaApi(page, goal.id, {
      title: milestoneTitle,
      scheduledDate: date,
    });
    await reloadCalendarReady(page);
    await page.getByText(milestoneTitle, { exact: true }).first().waitFor({
      state: "visible",
      timeout: config.timeoutMs,
    });

    return {
      duration_ms: performance.now() - startedAt,
      label: milestoneTitle,
      title: milestoneTitle,
      goal_title: goalTitle,
      goal_id: goal.id,
      milestone_id: milestone.id,
    };
  },
});
