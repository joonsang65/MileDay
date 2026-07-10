import {
  config,
  getErrorText,
} from "./perf_lib.mjs";

const DEFAULT_SETTINGS = {
  calendar_view: "month",
  theme: "system",
  accent_color: "#4F46E5",
  font_family: "system",
  font_size: 14,
  ai_suggestion: false,
  holiday_display: "normal",
  week_starts_on: 1,
  completed_milestones: true,
  default_goal_color: "#4F46E5",
  default_milestone_color: "#F97316",
  language: "ko",
  timezone: "Asia/Seoul",
};

if (!config.email || !config.password) {
  console.error(
    "PERF_TEST_EMAIL and PERF_TEST_PASSWORD are required. Set them in shell env or .env.",
  );
  process.exit(1);
}

try {
  const session = await request("/auth/login", {
    method: "POST",
    auth: false,
    body: {
      email: config.email,
      password: config.password,
    },
  });
  const accessToken = session.access_token;
  const goals = await request("/goals", { accessToken });
  const failures = [];

  console.log(`Cleaning performance test data for ${config.email}`);
  console.log(`goals_to_delete: ${goals.length}`);

  for (const goal of goals) {
    try {
      await request(`/goals/${goal.id}`, {
        method: "DELETE",
        accessToken,
      });
      console.log(`deleted_goal: ${goal.id} ${goal.title}`);
    } catch (error) {
      const message = `failed_goal: ${goal.id} ${getErrorText(error)}`;
      failures.push(message);
      console.error(message);
    }
  }

  if (process.env.PERF_CLEANUP_RESET_SETTINGS !== "false") {
    await request("/settings", {
      method: "PATCH",
      accessToken,
      body: DEFAULT_SETTINGS,
    });
    console.log("settings_reset: true");
  } else {
    console.log("settings_reset: skipped");
  }

  console.log("");
  console.log("Performance cleanup summary");
  console.log(`deleted_goals: ${goals.length - failures.length}`);
  console.log(`failed: ${failures.length}`);

  if (failures.length > 0) {
    process.exitCode = 1;
  }
} catch (error) {
  console.error(`Performance cleanup failed: ${getErrorText(error)}`);
  process.exitCode = 1;
}

async function request(path, { method = "GET", body, accessToken, auth = true } = {}) {
  const response = await fetch(`${config.apiBaseUrl.replace(/\/$/, "")}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      ...(auth && accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
    },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok || payload?.success === false) {
    throw new Error(`${method} ${path} failed with ${response.status}: ${text}`);
  }
  return payload?.data ?? payload;
}
