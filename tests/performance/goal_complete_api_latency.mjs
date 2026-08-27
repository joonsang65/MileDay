import { performance } from "node:perf_hooks";

import {
  createGoal,
  apiRequest,
  runApiLatencyFlow,
  todayDateKey,
} from "./api_latency_lib.mjs";

await runApiLatencyFlow({
  flow: "goal_complete_api",
  filePrefix: "goal-complete-api",
  summaryTitle: "Goal complete API latency summary",
  runIteration: async ({ token, iteration }) => {
    const date = todayDateKey();
    const title = `perf goal complete api ${Date.now()}-${iteration}`;
    const goal = await createGoal(token, { title, deadline: date });

    const startedAt = performance.now();
    await apiRequest(token, `/goals/${goal.id}/complete`, {
      method: "PATCH",
      body: { is_completed: true },
    });

    return {
      duration_ms: performance.now() - startedAt,
      label: title,
      goal_id: goal.id,
    };
  },
});
