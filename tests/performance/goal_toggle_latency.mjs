import { performance } from "node:perf_hooks";

import {
  config,
  createGoalViaApi,
  reloadCalendarReady,
  runPerfFlow,
  todayDateKey,
} from "./perf_lib.mjs";

await runPerfFlow({
  flow: "goal_toggle_to_ui_updated",
  filePrefix: "goal-toggle",
  summaryTitle: "Goal toggle latency summary",
  runIteration: async ({ page, iteration, markApiStart }) => {
    const date = todayDateKey();
    const goalTitle = `perf goal toggle ${Date.now()}-${iteration}`;
    const goal = await createGoalViaApi(page, { title: goalTitle, deadline: date });

    await reloadCalendarReady(page);
    const goalRow = page
      .locator(".editable-row")
      .filter({ hasText: goalTitle })
      .first();
    await goalRow.waitFor({ state: "visible", timeout: config.timeoutMs });

    const toggle = goalRow.getByTestId("goal-toggle");
    await toggle.waitFor({ state: "visible", timeout: config.timeoutMs });

    markApiStart();
    const startedAt = performance.now();
    const serverResponse = page.waitForResponse(
      (response) => {
        const url = new URL(response.url());
        return (
          response.request().method() === "PATCH" &&
          url.pathname === `/goals/${goal.id}/complete`
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
        `[data-testid="goal-toggle"][data-goal-id="${goal.id}"][aria-pressed="true"]`,
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
      label: goalTitle,
      title: goalTitle,
      goal_id: goal.id,
    };
  },
});
