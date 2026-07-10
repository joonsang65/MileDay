import { performance } from "node:perf_hooks";

import {
  config,
  ensureQuickAddOpen,
  getGoalForm,
  runPerfFlow,
} from "./perf_lib.mjs";

await runPerfFlow({
  flow: "goal_create_to_ui_visible",
  filePrefix: "goal-create",
  summaryTitle: "Goal create latency summary",
  runIteration: async ({ page, iteration, markApiStart }) => {
    const title = `perf goal ${Date.now()}-${iteration}`;

    await ensureQuickAddOpen(page);
    const goalForm = getGoalForm(page);
    await goalForm.getByLabel("제목").fill(title);

    markApiStart();
    const startedAt = performance.now();
    const createdGoal = page.getByText(title, { exact: true }).first();
    await Promise.all([
      createdGoal.waitFor({
        state: "visible",
        timeout: config.timeoutMs,
      }),
      goalForm.getByRole("button", { name: /목표 추가|추가 중/ }).click(),
    ]);

    return {
      duration_ms: performance.now() - startedAt,
      label: title,
      title,
    };
  },
});
