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
  flow: "milestone_toggle_to_ui_updated",
  filePrefix: "milestone-toggle",
  summaryTitle: "Milestone toggle latency summary",
  runIteration: async ({ page, iteration, markApiStart }) => {
    const date = todayDateKey();
    const goalTitle = `perf toggle goal ${Date.now()}-${iteration}`;
    const milestoneTitle = `perf toggle milestone ${Date.now()}-${iteration}`;
    const goal = await createGoalViaApi(page, { title: goalTitle, deadline: date });
    const milestone = await createMilestoneViaApi(page, goal.id, {
      title: milestoneTitle,
      scheduledDate: date,
    });

    await reloadCalendarReady(page);
    const milestoneRow = page
      .locator(".editable-item")
      .filter({ hasText: milestoneTitle })
      .first();
    await milestoneRow.waitFor({ state: "visible", timeout: config.timeoutMs });

    markApiStart();
    const startedAt = performance.now();
    await Promise.all([
      milestoneRow.getByTitle("미완료로 변경").waitFor({
        state: "visible",
        timeout: config.timeoutMs,
      }),
      milestoneRow.getByTitle("완료로 변경").click(),
    ]);

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
