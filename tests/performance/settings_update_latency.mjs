import { performance } from "node:perf_hooks";

import {
  config,
  openSettingsPanel,
  runPerfFlow,
} from "./perf_lib.mjs";

await runPerfFlow({
  flow: "settings_update_to_calendar_changed",
  filePrefix: "settings-update",
  summaryTitle: "Settings update latency summary",
  runIteration: async ({ page, markApiStart }) => {
    const panel = await openSettingsPanel(page);
    const firstWeekday = page.locator(".weekday-row span").first();
    const currentFirstWeekday = (await firstWeekday.textContent())?.trim();
    const nextWeekStart = currentFirstWeekday === "일" ? "1" : "0";
    const expectedFirstWeekday = nextWeekStart === "1" ? "월" : "일";

    await panel.locator(".settings-form select").nth(2).selectOption(nextWeekStart);

    markApiStart();
    const startedAt = performance.now();
    await Promise.all([
      firstWeekday.filter({ hasText: expectedFirstWeekday }).waitFor({
        state: "visible",
        timeout: config.timeoutMs,
      }),
      panel.getByRole("button", { name: /저장|Save|저장 중|Saving/ }).click(),
    ]);

    return {
      duration_ms: performance.now() - startedAt,
      label: `week_starts_on=${nextWeekStart}`,
      week_starts_on: Number(nextWeekStart),
    };
  },
});
