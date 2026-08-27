import { performance } from "node:perf_hooks";

import {
  apiRequest,
  runApiLatencyFlow,
} from "./api_latency_lib.mjs";

await runApiLatencyFlow({
  flow: "goals_legacy_list_api",
  filePrefix: "goals-legacy-list-api",
  summaryTitle: "Goals legacy list API latency summary",
  runIteration: async ({ token }) => {
    const startedAt = performance.now();
    const goals = await apiRequest(token, "/goals");
    for (const goal of goals) {
      await apiRequest(token, `/goals/${goal.id}/milestones`);
    }

    return {
      duration_ms: performance.now() - startedAt,
      label: `${goals.length} goals`,
      goal_count: goals.length,
      request_count: goals.length + 1,
    };
  },
});
