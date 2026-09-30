import { addMonths, startOfMonth } from "date-fns";

import { api } from "./api";
import type { CalendarDateData, CalendarMonthData } from "./types";

const CACHE_PREFIX = "mileday.mobile.month";
const REQUIRED_RADIUS = 2;
const EXTRA_RADIUS = 6;

type CachedMonth = {
  cached_at: string;
  data: CalendarMonthData;
};

export type PreloadResult = {
  ok: boolean;
  failed: string[];
};

export function getRequiredMonths(base = new Date()) {
  return monthOffsets(base, REQUIRED_RADIUS);
}

export function getExtraMonths(base = new Date()) {
  return monthOffsets(base, EXTRA_RADIUS);
}

export function readCachedMonth(year: number, month: number): CalendarMonthData | null {
  try {
    const raw = localStorage.getItem(cacheKey(year, month));
    if (!raw) {
      return null;
    }
    return (JSON.parse(raw) as CachedMonth).data;
  } catch {
    return null;
  }
}

export function readCachedDate(dateKey: string): CalendarDateData | null {
  const [year, month] = dateKey.split("-").map(Number);
  const monthData = readCachedMonth(year, month);
  return monthData?.days.find((day) => day.date === dateKey) || null;
}

export async function getMonthWithCache(year: number, month: number): Promise<CalendarMonthData> {
  const fresh = await api.getMonth(year, month);
  writeCachedMonth(fresh);
  return fresh;
}

export async function getDateWithCache(dateKey: string): Promise<CalendarDateData> {
  const cached = readCachedDate(dateKey);
  if (cached) {
    refreshDateMonth(dateKey);
    return cached;
  }
  const fresh = await api.getToday(dateKey);
  refreshDateMonth(dateKey);
  return fresh;
}

export async function preloadRequiredMonths(base = new Date()): Promise<PreloadResult> {
  return preloadMonths(getRequiredMonths(base), true);
}

export function preloadExtraMonths(base = new Date()) {
  void preloadMonths(getExtraMonths(base), false);
}

export function clearMonthCache() {
  Object.keys(localStorage)
    .filter((key) => key.startsWith(`${CACHE_PREFIX}.`))
    .forEach((key) => localStorage.removeItem(key));
}

async function preloadMonths(months: Date[], requireCurrentMonth: boolean): Promise<PreloadResult> {
  const results = await Promise.allSettled(
    months.map((month) => getMonthWithCache(month.getFullYear(), month.getMonth() + 1)),
  );
  const failed = results
    .map((result, index) => (result.status === "rejected" ? monthId(months[index]) : null))
    .filter((value): value is string => Boolean(value));

  if (!requireCurrentMonth) {
    return { ok: failed.length === 0, failed };
  }

  const now = new Date();
  const current = readCachedMonth(now.getFullYear(), now.getMonth() + 1);
  return { ok: Boolean(current), failed };
}

function writeCachedMonth(data: CalendarMonthData) {
  const payload: CachedMonth = {
    cached_at: new Date().toISOString(),
    data,
  };
  localStorage.setItem(cacheKey(data.year, data.month), JSON.stringify(payload));
}

function refreshDateMonth(dateKey: string) {
  const [year, month] = dateKey.split("-").map(Number);
  void getMonthWithCache(year, month).catch(() => undefined);
}

function monthOffsets(base: Date, radius: number) {
  const start = startOfMonth(base);
  const months: Date[] = [];
  for (let offset = -radius; offset <= radius; offset += 1) {
    months.push(addMonths(start, offset));
  }
  return months;
}

function monthId(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}`;
}

function cacheKey(year: number, month: number) {
  return `${CACHE_PREFIX}.${api.getUserId() || "anonymous"}.${year}-${String(month).padStart(2, "0")}`;
}
