import { performance } from "node:perf_hooks";

import {
  apiRequest,
  runApiLatencyFlow,
} from "./api_latency_lib.mjs";

await runApiLatencyFlow({
  flow: "goals_with_milestones_api",
  filePrefix: "goals-with-milestones-api",
  summaryTitle: "Goals with milestones API latency summary",
  runIteration: async ({ token }) => {
    const startedAt = performance.now();
    const goals = await apiRequest(token, "/goals/with-milestones");
    const milestoneCount = goals.reduce(
      (total, goal) => total + (Array.isArray(goal.milestones) ? goal.milestones.length : 0),
      0,
    );

    return {
      duration_ms: performance.now() - startedAt,
      label: `${goals.length} goals / ${milestoneCount} milestones`,
      goal_count: goals.length,
      milestone_count: milestoneCount,
      request_count: 1,
    };
  },
});
