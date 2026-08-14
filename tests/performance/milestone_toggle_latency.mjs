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

    const toggle = milestoneRow.getByTestId("milestone-toggle");
    await toggle.waitFor({ state: "visible", timeout: config.timeoutMs });

    markApiStart();
    const startedAt = performance.now();
    const serverResponse = page.waitForResponse(
      (response) => {
        const url = new URL(response.url());
        return (
          response.request().method() === "PATCH" &&
          url.pathname === `/milestones/${milestone.id}/complete`
        );
      },
      { timeout: config.timeoutMs },
    ).then(
      () => ({ ok: true, error: null }),
      (error) => ({ ok: false, error }),
    );
    await toggle.click();
    await page
      .locator(
        `[data-testid="milestone-toggle"][data-milestone-id="${milestone.id}"][aria-pressed="true"]`,
      )
      .waitFor({ state: "visible", timeout: config.timeoutMs });
    const visualDurationMs = performance.now() - startedAt;
    const serverResult = await serverResponse;
    if (!serverResult.ok) {
      throw serverResult.error;
    }

    return {
      duration_ms: visualDurationMs,
      server_duration_ms: performance.now() - startedAt,
      label: milestoneTitle,
      title: milestoneTitle,
      goal_title: goalTitle,
      goal_id: goal.id,
      milestone_id: milestone.id,
    };
  },
});
