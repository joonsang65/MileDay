import { existsSync } from "node:fs";
import { appendFile, mkdir, readFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { performance } from "node:perf_hooks";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
export const rootDir = resolve(__dirname, "../..");
export const logsDir = resolve(rootDir, "logs/perf");

await loadEnvFile(resolve(rootDir, ".env"));
await loadEnvFile(resolve(rootDir, "frontend/.env"));

export const apiConfig = {
  apiBaseUrl: process.env.VITE_API_BASE_URL || "http://localhost:8000",
  email: process.env.PERF_TEST_EMAIL,
  password: process.env.PERF_TEST_PASSWORD,
  iterations: parsePositiveInteger(process.env.PERF_ITERATIONS, 10),
};

export async function runApiLatencyFlow({ flow, filePrefix, summaryTitle, runIteration }) {
  if (!apiConfig.email || !apiConfig.password) {
    throw new Error("PERF_TEST_EMAIL and PERF_TEST_PASSWORD are required.");
  }

  await mkdir(logsDir, { recursive: true });
  const outputFile = resolve(logsDir, `${filePrefix}-${formatTimestampForFile(new Date())}.jsonl`);
  const token = await login();
  const durations = [];
  let failedCount = 0;

  for (let iteration = 1; iteration <= apiConfig.iterations; iteration += 1) {
    const createdAt = new Date().toISOString();
    try {
      const result = await runIteration({ token, iteration });
      const durationMs = roundMs(result.duration_ms);
      durations.push(durationMs);
      await writeResult(outputFile, {
        success: true,
        flow,
        iteration,
        ...result,
        duration_ms: durationMs,
        created_at: createdAt,
      });
      console.log(`[${iteration}/${apiConfig.iterations}] ${durationMs}ms ${result.label ?? ""}`.trim());
    } catch (error) {
      failedCount += 1;
      await writeResult(outputFile, {
        success: false,
        flow,
        iteration,
        error: getErrorText(error),
        created_at: createdAt,
      });
      console.error(`[${iteration}/${apiConfig.iterations}] failed: ${getErrorText(error)}`);
    }
  }

  const summary = summarize(durations);
  console.log("");
  console.log(summaryTitle);
  console.log(`count: ${summary.count}`);
  console.log(`failed: ${failedCount}`);
  console.log(`average_ms: ${summary.average}`);
  console.log(`min_ms: ${summary.min}`);
  console.log(`max_ms: ${summary.max}`);
  console.log(`p50_ms: ${summary.p50}`);
  console.log(`p95_ms: ${summary.p95}`);
  console.log(`output: ${outputFile}`);

  if (failedCount > 0 || durations.length !== apiConfig.iterations) {
    process.exitCode = 1;
  }

  return { summary, failedCount, outputFile };
}

export async function createGoal(token, { title, deadline = todayDateKey(), color = "#0F766E" }) {
  return apiRequest(token, "/goals", {
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

export async function apiRequest(token, path, { method = "GET", body } = {}) {
  const response = await fetch(`${apiConfig.apiBaseUrl.replace(/\/$/, "")}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
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

async function login() {
  const response = await fetch(`${apiConfig.apiBaseUrl.replace(/\/$/, "")}/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      email: apiConfig.email,
      password: apiConfig.password,
    }),
  });
  const text = await response.text();
  const payload = text ? JSON.parse(text) : null;
  if (!response.ok || payload?.success === false) {
    throw new Error(`POST /auth/login failed with ${response.status}: ${text}`);
  }
  return payload.data.access_token;
}

async function writeResult(outputFile, result) {
  await appendFile(outputFile, `${JSON.stringify(result)}\n`, "utf8");
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
