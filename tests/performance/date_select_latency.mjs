import { performance } from "node:perf_hooks";

import {
  config,
  runPerfFlow,
} from "./perf_lib.mjs";

await runPerfFlow({
  flow: "calendar_date_select_loaded",
  filePrefix: "date-select",
  summaryTitle: "Date select latency summary",
  runIteration: async ({ page, iteration, markApiStart }) => {
    const candidates = page.locator(".day-cell:not(.muted):not(.selected)");
    const count = await candidates.count();
    if (count < 2) {
      throw new Error("Selectable calendar date cells were not found.");
    }

    const index = iteration % count;
    const target = candidates.nth(index);
    const targetDate = await target.getAttribute("data-date");
    if (!targetDate) {
      throw new Error("Calendar date cell does not expose data-date.");
    }

    markApiStart();
    const startedAt = performance.now();
    await Promise.all([
      page.locator(".detail-panel").getByText(targetDate, { exact: true }).waitFor({
        state: "visible",
        timeout: config.timeoutMs,
      }),
      target.click(),
    ]);

    return {
      duration_ms: performance.now() - startedAt,
      label: targetDate,
      date: targetDate,
    };
  },
});
