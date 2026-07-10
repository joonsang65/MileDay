import { existsSync } from "node:fs";
import { appendFile, mkdir, readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";

const requireFromFrontend = createRequire(new URL("../../frontend/package.json", import.meta.url));
export const { chromium } = requireFromFrontend("@playwright/test");

const __dirname = dirname(fileURLToPath(import.meta.url));
export const rootDir = resolve(__dirname, "../..");
export const logsDir = resolve(rootDir, "logs/perf");

await loadEnvFile(resolve(rootDir, ".env"));
await loadEnvFile(resolve(rootDir, "frontend/.env"));

export const config = {
  baseUrl: process.env.PERF_BASE_URL || "http://localhost:5173",
  apiBaseUrl: process.env.VITE_API_BASE_URL || "http://localhost:8000",
  email: process.env.PERF_TEST_EMAIL,
  password: process.env.PERF_TEST_PASSWORD,
  iterations: parsePositiveInteger(process.env.PERF_ITERATIONS, 10),
  timeoutMs: parsePositiveInteger(process.env.PERF_TIMEOUT_MS, 30000),
  headless: process.env.PERF_HEADLESS !== "false",
};

export async function runPerfFlow({
  flow,
  filePrefix,
  summaryTitle,
  runIteration,
}) {
  if (!config.email || !config.password) {
    console.error(
      "PERF_TEST_EMAIL and PERF_TEST_PASSWORD are required. Set them in shell env or .env.",
    );
    process.exit(1);
  }

  await mkdir(logsDir, { recursive: true });
  const outputFile = resolve(
    logsDir,
    `${filePrefix}-${formatTimestampForFile(new Date())}.jsonl`,
  );
  const durations = [];
  let failedCount = 0;
  let browser;

  try {
    browser = await chromium.launch({ headless: config.headless });
    const context = await browser.newContext();
    const page = await context.newPage();
    const tracker = createApiTracker(page);

    await prepareLoggedInSession(page);

    for (let iteration = 1; iteration <= config.iterations; iteration += 1) {
      const createdAt = new Date().toISOString();
      let apiStartIndex = tracker.events.length;

      try {
        const result = await runIteration({
          page,
          iteration,
          apiEvents: tracker.events,
          markApiStart: () => {
            apiStartIndex = tracker.events.length;
          },
        });
        const durationMs = roundMs(result.duration_ms);
        durations.push(durationMs);
        await writeResult(outputFile, {
          success: true,
          flow,
          iteration,
          ...result,
          duration_ms: durationMs,
          api: tracker.events.slice(apiStartIndex),
          created_at: createdAt,
        });
        console.log(`[${iteration}/${config.iterations}] ${durationMs}ms ${result.label ?? ""}`.trim());
      } catch (error) {
        failedCount += 1;
        await writeResult(outputFile, {
          success: false,
          flow,
          iteration,
          api: tracker.events.slice(apiStartIndex),
          error: getErrorText(error),
          created_at: createdAt,
        });
        console.error(`[${iteration}/${config.iterations}] failed: ${getErrorText(error)}`);
      }
    }
  } catch (error) {
    console.error(`Performance run failed: ${getErrorText(error)}`);
    process.exitCode = 1;
  } finally {
    if (browser) {
      await browser.close();
    }
  }

  printSummary({
    title: summaryTitle,
    durations,
    failedCount,
    outputFile,
  });

  if (failedCount > 0 || durations.length !== config.iterations) {
    process.exitCode = 1;
  }
}

export async function prepareLoggedInSession(page) {
  try {
    await page.goto(config.baseUrl, {
      waitUntil: "domcontentloaded",
      timeout: config.timeoutMs,
    });
  } catch (error) {
    throw new Error(
      `Could not connect to PERF_BASE_URL=${config.baseUrl}. Start the dev server first. ${getErrorText(error)}`,
    );
  }

  const quickAddButton = page.getByRole("button", { name: "빠른 추가" });
  if (await quickAddButton.isVisible().catch(() => false)) {
    await waitForAppIdle(page);
    return;
  }

  const authForm = page.locator("form.auth-form");
  await authForm.getByLabel("이메일").fill(config.email);
  await authForm.getByLabel("비밀번호", { exact: true }).fill(config.password);
  await authForm.getByRole("button", { name: "로그인" }).click();
  await quickAddButton.waitFor({
    state: "visible",
    timeout: config.timeoutMs,
  });
  await waitForAppIdle(page);
}

export async function ensureQuickAddOpen(page) {
  const toggle = page.getByRole("button", { name: "빠른 추가" });
  await toggle.waitFor({ state: "visible", timeout: config.timeoutMs });
  const expanded = await toggle.getAttribute("aria-expanded");
  if (expanded !== "true") {
    await toggle.click();
  }
}

export async function reloadCalendarReady(page) {
  await page.reload({ waitUntil: "domcontentloaded", timeout: config.timeoutMs });
  await page.getByRole("button", { name: "빠른 추가" }).waitFor({
    state: "visible",
    timeout: config.timeoutMs,
  });
  await waitForAppIdle(page);
}

export async function waitForAppIdle(page) {
  await page.getByText("불러오는 중입니다.").waitFor({
    state: "detached",
    timeout: config.timeoutMs,
  }).catch(() => undefined);
}

export async function createGoalViaApi(page, { title, deadline = todayDateKey(), color = "#0F766E" }) {
  return apiRequestInPage(page, "/goals", {
    method: "POST",
    body: {
      title,
      deadline,
      is_recurring: false,
      recurrence_type: null,
      color,
    },
  });
}

export async function createMilestoneViaApi(
  page,
  goalId,
  { title, scheduledDate = todayDateKey(), color = "#D97706" },
) {
  return apiRequestInPage(page, `/goals/${goalId}/milestones`, {
    method: "POST",
    body: {
      title,
      scheduled_date: scheduledDate,
      color,
    },
  });
}

export async function apiRequestInPage(page, path, { method = "GET", body } = {}) {
  return page.evaluate(
    async ({ apiBaseUrl, path, method, body }) => {
      const token = window.localStorage.getItem("mileday.access_token");
      const response = await window.fetch(`${apiBaseUrl.replace(/\/$/, "")}${path}`, {
        method,
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: body ? JSON.stringify(body) : undefined,
      });
      const text = await response.text();
      const payload = text ? JSON.parse(text) : null;
      if (!response.ok || payload?.success === false) {
        throw new Error(`${method} ${path} failed with ${response.status}: ${text}`);
      }
      return payload?.data ?? payload;
    },
    { apiBaseUrl: config.apiBaseUrl, path, method, body },
  );
}

export function getGoalForm(page) {
  return page
    .locator("form.creation-form")
    .filter({ has: page.getByRole("heading", { name: "목표" }) });
}

export function getMilestoneForm(page) {
  return page
    .locator("form.creation-form")
    .filter({ has: page.getByLabel("예정일") });
}

export async function openMilestoneForm(page) {
  await ensureQuickAddOpen(page);
  const form = getMilestoneForm(page);
  if (await form.isVisible().catch(() => false)) {
    return form;
  }
  await page.getByRole("button", { name: "마일스톤 추가" }).click();
  await form.waitFor({ state: "visible", timeout: config.timeoutMs });
  return form;
}

export async function openSettingsPanel(page) {
  const settingsButton = page.locator("button[title='설정'], button[title='Settings']").first();
  await settingsButton.waitFor({ state: "visible", timeout: config.timeoutMs });
  await settingsButton.click();
  const panel = page.locator(".settings-panel");
  await panel.waitFor({ state: "visible", timeout: config.timeoutMs });
  return panel;
}

export function todayDateKey() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

export function roundMs(value) {
  return Math.round(value * 100) / 100;
}

export function getErrorText(error) {
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}

function createApiTracker(page) {
  const inFlightRequests = new Map();
  const events = [];

  page.on("request", (request) => {
    if (!isMeasuredApiUrl(request.url())) {
      return;
    }
    inFlightRequests.set(request, performance.now());
  });

  page.on("response", (response) => {
    const request = response.request();
    const startedAt = inFlightRequests.get(request);
    if (startedAt === undefined) {
      return;
    }
    inFlightRequests.delete(request);
    events.push({
      method: request.method(),
      url: normalizeApiUrl(response.url()),
      status: response.status(),
      duration_ms: roundMs(performance.now() - startedAt),
    });
  });

  return { events };
}

async function writeResult(outputFile, result) {
  await appendFile(outputFile, `${JSON.stringify(result)}\n`, "utf8");
}

function printSummary({ title, durations, failedCount, outputFile }) {
  const summary = summarize(durations);
  console.log("");
  console.log(title);
  console.log(`count: ${summary.count}`);
  console.log(`failed: ${failedCount}`);
  console.log(`average_ms: ${summary.average}`);
  console.log(`min_ms: ${summary.min}`);
  console.log(`max_ms: ${summary.max}`);
  console.log(`p50_ms: ${summary.p50}`);
  console.log(`p95_ms: ${summary.p95}`);
  console.log(`output: ${outputFile}`);
}

function summarize(values) {
  if (values.length === 0) {
    return {
      count: 0,
      average: null,
      min: null,
      max: null,
      p50: null,
      p95: null,
    };
  }

  const sorted = [...values].sort((left, right) => left - right);
  const sum = sorted.reduce((total, value) => total + value, 0);
  return {
    count: sorted.length,
    average: roundMs(sum / sorted.length),
    min: sorted[0],
    max: sorted[sorted.length - 1],
    p50: percentile(sorted, 50),
    p95: percentile(sorted, 95),
  };
}

function percentile(sortedValues, percentileRank) {
  if (sortedValues.length === 0) {
    return null;
  }
  const index = Math.ceil((percentileRank / 100) * sortedValues.length) - 1;
  return sortedValues[Math.max(0, Math.min(index, sortedValues.length - 1))];
}

function isMeasuredApiUrl(url) {
  return ["/goals", "/calendar", "/milestones", "/settings"].some((path) =>
    new URL(url).pathname.startsWith(path),
  );
}

function normalizeApiUrl(url) {
  const parsedUrl = new URL(url);
  return `${parsedUrl.pathname}${parsedUrl.search}`;
}

function parsePositiveInteger(value, fallback) {
  const parsed = Number.parseInt(value ?? "", 10);
  return Number.isFinite(parsed) && parsed > 0 ? parsed : fallback;
}

function formatTimestampForFile(value) {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Seoul",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(value);
  const byType = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  return `${byType.year}${byType.month}${byType.day}-${byType.hour}${byType.minute}${byType.second}-KST`;
}

async function loadEnvFile(path) {
  if (!existsSync(path)) {
    return;
  }

  const content = await readFile(path, "utf8");
  for (const line of content.split(/\r?\n/)) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) {
      continue;
    }
    const [key, ...valueParts] = trimmed.split("=");
    if (process.env[key]) {
      continue;
    }
    process.env[key] = valueParts.join("=").replace(/^["']|["']$/g, "");
  }
}
