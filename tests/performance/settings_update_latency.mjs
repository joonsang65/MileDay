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
    const currentFirstWeekday = (await firstWeekday.textContent())?.trim() ?? "";
    const weekStartSelect = panel.locator(".settings-form select").nth(2);
    const currentWeekStart = await weekStartSelect.inputValue();
    const nextWeekStart = currentWeekStart === "1" ? "0" : "1";

    await weekStartSelect.selectOption(nextWeekStart);

    markApiStart();
    const startedAt = performance.now();
    await Promise.all([
      page.waitForFunction(
        ({ previous }) =>
          document.querySelector(".weekday-row span")?.textContent?.trim() !== previous,
        { previous: currentFirstWeekday },
        { timeout: config.timeoutMs },
      ),
      panel.getByRole("button", { name: /저장|Save|Saving/ }).click(),
    ]);

    return {
      duration_ms: performance.now() - startedAt,
      label: `week_starts_on=${nextWeekStart}`,
      week_starts_on: Number(nextWeekStart),
    };
  },
});
