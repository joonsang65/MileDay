import assert from "node:assert/strict";
import { after, before, beforeEach, test } from "node:test";
import { setImmediate } from "node:timers/promises";
import { createServer } from "vite";

const SESSION_KEY = "mileday.mobile.session";
const NOW = Date.parse("2026-11-10T03:00:00Z");
let server, ApiClient, api, dates, cache, browser, documentTarget;

class MemoryStorage {
  getItem(key) { return Object.hasOwn(this, key) ? this[key] : null; }
  setItem(key, value) { this[key] = String(value); }
  removeItem(key) { delete this[key]; }
  clear() { for (const key of Object.keys(this)) delete this[key]; }
}

class Browser extends EventTarget {
  timers = new Map();
  sequence = 0;
  setTimeout = (callback, delay) => {
    const id = ++this.sequence;
    this.timers.set(id, { callback, delay });
    return id;
  };
  clearTimeout = (id) => this.timers.delete(id);
  tick() {
    const [id, timer] = [...this.timers].sort((a, b) => a[1].delay - b[1].delay)[0];
    this.timers.delete(id);
    timer.callback();
  }
}

function session(overrides = {}) {
  return {
    access_token: "access-old", refresh_token: "refresh-old", expires_at: NOW / 1000 + 3600,
    token_type: "bearer", user: { id: "user-a", email: "a@example.com" }, ...overrides,
  };
}

function seed(value = session()) {
  localStorage.setItem(SESSION_KEY, JSON.stringify(value));
  return new ApiClient();
}

function ok(data) { return Response.json({ success: true, data }); }
function fail(status, code = "AUTH_TOKEN_EXPIRED") {
  return Response.json({ success: false, error: { code, message: code } }, { status });
}
function deferred() {
  let resolve;
  const promise = new Promise((done) => { resolve = done; });
  return { promise, resolve };
}
async function flush() { for (let i = 0; i < 6; i++) await setImmediate(); }
function mockNow(t, now = NOW) { t.mock.timers.enable({ apis: ["Date"], now }); }
function day(date, is_today = false, title = "cached") {
  return {
    date, is_today, goal_count: 1, milestone_count: 0, completed_milestone_count: 0,
    goals: [{ id: title, title }], milestones: [],
  };
}
function month(days) { return { year: 2026, month: 11, days, goals: [], milestones: [] }; }
function seedMonth(data) {
  localStorage.setItem(`mileday.mobile.month.${api.getUserId()}.${data.year}-${String(data.month).padStart(2, "0")}`,
    JSON.stringify({ cached_at: "old", data }));
}

before(async () => {
  globalThis.window = new Browser();
  globalThis.document = new EventTarget();
  globalThis.localStorage = new MemoryStorage();
  server = await createServer({
    configFile: false, appType: "custom",
    server: { middlewareMode: true, hmr: false, watch: null },
  });
  ({ ApiClient, api } = await server.ssrLoadModule("/src/api.ts"));
  dates = await server.ssrLoadModule("/src/date.ts");
  cache = await server.ssrLoadModule("/src/month-cache.ts");
});
after(async () => { await server?.close(); });
beforeEach(() => {
  browser = globalThis.window = new Browser();
  documentTarget = globalThis.document = new EventTarget();
  documentTarget.visibilityState = "visible";
  localStorage.clear();
  api.clearSession();
  globalThis.fetch = async () => { throw new TypeError("offline"); };
});

test("login atomically stores the full session and restores it without legacy keys", async (t) => {
  mockNow(t);
  localStorage.setItem("mileday.mobile.access_token", "legacy");
  localStorage.setItem("mileday.mobile.user_id", "user-a");
  const client = new ApiClient();
  const writes = [];
  const setItem = localStorage.setItem.bind(localStorage);
  t.mock.method(localStorage, "setItem", (key, value) => { writes.push(key); setItem(key, value); });
  globalThis.fetch = async (url, options) => {
    assert.ok(url.endsWith("/auth/login"));
    assert.equal(options.headers.Authorization, undefined);
    return ok(session());
  };
  await client.login("a@example.com", "password");
  assert.deepEqual(writes, [SESSION_KEY]);
  assert.deepEqual(JSON.parse(localStorage.getItem(SESSION_KEY)), session());
  assert.equal(localStorage.getItem("mileday.mobile.access_token"), null);
  assert.equal(new ApiClient().getUserId(), "user-a");
});

test("startup rotates an expired stored session before concurrent preload requests", async (t) => {
  mockNow(t);
  const client = seed(session({ expires_at: NOW / 1000 - 5 }));
  let refreshes = 0;
  const gate = deferred();
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/auth/refresh")) {
      refreshes++;
      assert.deepEqual(JSON.parse(options.body), { refresh_token: "refresh-old" });
      assert.equal(options.headers.Authorization, undefined);
      await gate.promise;
      return ok(session({ access_token: "access-new", refresh_token: "refresh-new" }));
    }
    assert.equal(options.headers.Authorization, "Bearer access-new");
    return ok({ loaded: true });
  };
  const stop = client.startSessionMaintenance();
  const requests = Array.from({ length: 5 }, () => client.getMonth(2026, 11));
  await flush();
  assert.equal(refreshes, 1);
  gate.resolve();
  await Promise.all(requests);
  assert.equal(JSON.parse(localStorage.getItem(SESSION_KEY)).refresh_token, "refresh-new");
  stop();
  assert.equal(browser.timers.size, 0);
});

test("expiry timer refreshes early and transient startup failure retains session for online retry", async (t) => {
  mockNow(t);
  const client = seed(session({ expires_at: NOW / 1000 + 120 }));
  const stop = client.startSessionMaintenance();
  await flush();
  assert.equal([...browser.timers.values()][0].delay, 60_000);
  t.mock.timers.setTime(NOW + 60_000);
  browser.tick();
  await flush();
  assert.equal(client.hasSession(), true);
  assert.equal([...browser.timers.values()][0].delay, 30_000);
  globalThis.fetch = async () => ok(session({ expires_at: NOW / 1000 + 7200, refresh_token: "rotated" }));
  browser.dispatchEvent(new Event("online"));
  await flush();
  assert.equal(JSON.parse(localStorage.getItem(SESSION_KEY)).refresh_token, "rotated");
  stop();
});

test("network, server, rate-limit and malformed refresh failures retain persisted credentials", async (t) => {
  mockNow(t);
  for (const response of [null, fail(503), fail(429), ok({}), new Response("broken")]) {
    const client = seed(session({ expires_at: NOW / 1000 - 1 }));
    const stored = localStorage.getItem(SESSION_KEY);
    globalThis.fetch = async () => {
      if (response === null) throw new TypeError("offline");
      return response;
    };
    await assert.rejects(client.ensureSession());
    assert.equal(client.hasSession(), true);
    assert.equal(localStorage.getItem(SESSION_KEY), stored);
  }
});

test("revoked refresh credentials clear session while public failures and ordinary 403 do not", async (t) => {
  mockNow(t);
  for (const status of [400, 401, 403]) {
    const client = seed(session({ expires_at: NOW / 1000 - 1 }));
    globalThis.fetch = async () => fail(status, "AUTH_INVALID_TOKEN");
    await assert.rejects(client.ensureSession());
    assert.equal(client.hasSession(), false);
    assert.equal(localStorage.getItem(SESSION_KEY), null);
  }
  const client = seed();
  globalThis.fetch = async () => fail(403, "FORBIDDEN");
  await assert.rejects(client.getMonth(2026, 11));
  assert.equal(client.hasSession(), true);
  globalThis.fetch = async () => fail(401, "AUTH_INVALID_CREDENTIALS");
  await assert.rejects(client.login("a@example.com", "wrong"));
  await assert.rejects(client.getPushConfig());
  assert.equal(client.hasSession(), true);
});

test("concurrent expired responses share one refresh and retry original method and body once", async (t) => {
  mockNow(t);
  const client = seed();
  let refreshes = 0, original = 0, retried = 0;
  const gate = deferred();
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/auth/refresh")) {
      refreshes++;
      await gate.promise;
      return ok(session({ access_token: "access-new", refresh_token: "refresh-new" }));
    }
    assert.equal(options.method, "PATCH");
    assert.deepEqual(JSON.parse(options.body), { enabled: true });
    if (options.headers.Authorization === "Bearer access-old") { original++; return fail(401); }
    retried++;
    return ok({ enabled: true });
  };
  const requests = Array.from({ length: 4 }, () => client.updateNotificationSettings({ enabled: true }));
  await flush();
  assert.equal(original, 4);
  assert.equal(refreshes, 1);
  gate.resolve();
  await Promise.all(requests);
  assert.equal(retried, 4);
  assert.equal(refreshes, 1);
});

test("a second expired response ends the session without a refresh loop", async (t) => {
  mockNow(t);
  const client = seed();
  let refreshes = 0, requests = 0;
  globalThis.fetch = async (url) => {
    if (url.endsWith("/auth/refresh")) {
      refreshes++;
      return ok(session({ access_token: "new", refresh_token: "new" }));
    }
    requests++;
    return fail(401);
  };
  await assert.rejects(client.getMonth(2026, 11));
  assert.equal(refreshes, 1);
  assert.equal(requests, 2);
  assert.equal(client.hasSession(), false);
});

test("late old-bearer responses reuse the rotated session without another refresh", async (t) => {
  mockNow(t);
  const client = seed();
  const late = deferred();
  let originals = 0, refreshes = 0;
  globalThis.fetch = async (url, options) => {
    if (url.endsWith("/auth/refresh")) {
      refreshes++;
      return ok(session({ access_token: "new", refresh_token: "new" }));
    }
    if (options.headers.Authorization === "Bearer access-old") {
      if (++originals === 2) await late.promise;
      return fail(401);
    }
    return ok({});
  };
  const first = client.getMonth(2026, 11);
  const second = client.getMonth(2026, 12);
  await first;
  late.resolve();
  await second;
  assert.equal(refreshes, 1);
});

test("pending refresh cannot resurrect logout or overwrite a different account", async (t) => {
  mockNow(t);
  for (const replacement of [null, session({ user: { id: "user-b", email: "b@example.com" } })]) {
    const client = seed(session({ expires_at: NOW / 1000 - 1 }));
    const gate = deferred();
    globalThis.fetch = async () => { await gate.promise; return ok(session({ access_token: "late" })); };
    const pending = client.ensureSession();
    await flush();
    if (replacement) localStorage.setItem(SESSION_KEY, JSON.stringify(replacement));
    else client.clearSession();
    gate.resolve();
    await assert.rejects(pending, { status: 409 });
    assert.equal(client.getUserId(), replacement?.user.id || null);
    assert.equal(localStorage.getItem(SESSION_KEY), replacement ? JSON.stringify(replacement) : null);
  }
});

test("storage failure cannot partially replace a persisted session", async (t) => {
  mockNow(t);
  const client = seed();
  const saved = localStorage.getItem(SESSION_KEY);
  globalThis.fetch = async () => ok(session({ access_token: "new", refresh_token: "new" }));
  t.mock.method(localStorage, "setItem", () => { throw new Error("quota"); });
  await assert.rejects(client.login("a@example.com", "password"), /quota/);
  assert.equal(localStorage.getItem(SESSION_KEY), saved);
  assert.equal(client.hasSession(), true);
});

test("Web Locks serialize refresh rotation across separate clients", async (t) => {
  mockNow(t);
  const descriptor = Object.getOwnPropertyDescriptor(navigator, "locks");
  let tail = Promise.resolve();
  Object.defineProperty(navigator, "locks", { configurable: true, value: {
    request: (_key, callback) => {
      const pending = tail.then(callback);
      tail = pending.catch(() => undefined);
      return pending;
    },
  } });
  t.after(() => {
    if (descriptor) Object.defineProperty(navigator, "locks", descriptor);
    else delete navigator.locks;
  });
  const first = seed(session({ expires_at: NOW / 1000 - 1 }));
  const second = new ApiClient();
  let refreshes = 0;
  globalThis.fetch = async () => {
    refreshes++;
    return ok(session({ refresh_token: "rotated", access_token: "rotated" }));
  };
  await Promise.all([first.ensureSession(), second.ensureSession()]);
  assert.equal(refreshes, 1);
  assert.equal(second.hasSession(), true);
});

test("corrupt storage is safe and old access-only installs work until expiry", async (t) => {
  mockNow(t);
  localStorage.setItem(SESSION_KEY, "broken");
  assert.equal(new ApiClient().hasSession(), false);
  localStorage.removeItem(SESSION_KEY);
  localStorage.setItem("mileday.mobile.access_token", "legacy");
  localStorage.setItem("mileday.mobile.user_id", "user-a");
  const client = new ApiClient();
  globalThis.fetch = async () => fail(401);
  await assert.rejects(client.getMonth(2026, 11));
  assert.equal(client.hasSession(), false);
});

test("cached is_today is recalculated locally, even when server and user timezone disagree", async (t) => {
  mockNow(t);
  seed();
  await api.ensureSession();
  const today = dates.todayKey();
  const previous = dates.toDateKey(new Date(NOW - 86_400_000));
  seedMonth(month([day(previous, true), day(today, false)]));
  const cached = cache.readCachedMonth(2026, 11);
  assert.equal(cached.days.find((value) => value.date === previous).is_today, false);
  assert.equal(cached.days.find((value) => value.date === today).is_today, true);
  globalThis.fetch = async () => { throw new Error("offline"); };
  assert.equal((await cache.getDateWithCache(today, true)).is_today, true);
  assert.equal(api.hasSession(), true);
});

test("fresh date revalidation returns changed data while offline fallback keeps cache", async (t) => {
  mockNow(t);
  seed();
  await api.ensureSession();
  const today = dates.todayKey();
  seedMonth(month([day(today)]));
  globalThis.fetch = async (url) => url.includes("/calendar/date/")
    ? ok(day(today, false, "fresh")) : ok(month([day(today, false, "fresh")]));
  assert.equal((await cache.getDateWithCache(today, true)).goals[0].title, "fresh");
  await flush();
  assert.equal(cache.readCachedDate(today).goals[0].title, "fresh");
});

test("account changes reject old date/month responses and never write them under the new user", async (t) => {
  mockNow(t);
  for (const load of [() => cache.getMonthWithCache(2026, 11), () => cache.getDateWithCache(dates.todayKey(), true)]) {
    seed();
    await api.ensureSession();
    seedMonth(month([day(dates.todayKey())]));
    const gate = deferred();
    globalThis.fetch = async (url) => {
      await gate.promise;
      return ok(url.includes("/calendar/date/") ? day(dates.todayKey()) : month([day(dates.todayKey())]));
    };
    const pending = load();
    await flush();
    localStorage.setItem(SESSION_KEY, JSON.stringify(session({ user: { id: "user-b", email: "b@example.com" } })));
    await api.ensureSession();
    gate.resolve();
    await assert.rejects(pending, { status: 409 });
    assert.equal(cache.readCachedMonth(2026, 11), null);
    assert.equal(localStorage.getItem("mileday.mobile.month.user-b.2026-11"), null);
    await flush();
  }
});

test("midnight rolls day state forward and resume events revalidate without changing the date", (t) => {
  const midnight = new Date(2026, 10, 11).getTime();
  mockNow(t, midnight - 5);
  const updates = [];
  const stop = dates.watchDay((value) => updates.push(value));
  assert.equal([...browser.timers.values()][0].delay, 5);
  assert.equal(updates.at(-1).today, "2026-11-10");
  t.mock.timers.setTime(midnight);
  browser.tick();
  assert.equal(updates.at(-1).today, "2026-11-11");
  const revision = updates.at(-1).revision;
  browser.dispatchEvent(new Event("focus"));
  browser.dispatchEvent(new Event("online"));
  documentTarget.visibilityState = "hidden";
  documentTarget.dispatchEvent(new Event("visibilitychange"));
  assert.equal(updates.at(-1).revision, revision + 2);
  documentTarget.visibilityState = "visible";
  t.mock.timers.setTime(new Date(2026, 10, 13, 12).getTime());
  documentTarget.dispatchEvent(new Event("visibilitychange"));
  assert.equal(updates.at(-1).today, "2026-11-13");
  stop();
  browser.dispatchEvent(new Event("focus"));
  assert.equal(browser.timers.size, 0);
});

test("rollover only follows the previous today and moves months only when following its month", () => {
  const state = { selectedDate: "2026-12-31", visibleMonth: dates.parseDateKey("2026-12-01") };
  const next = dates.rollCalendarDay(state, "2026-12-31", "2027-01-01");
  assert.equal(next.selectedDate, "2027-01-01");
  assert.equal(dates.monthLabel(next.visibleMonth), "2027.01");
  const browsing = { ...state, selectedDate: "2026-12-20" };
  assert.equal(dates.rollCalendarDay(browsing, "2026-12-31", "2027-01-01"), browsing);
  const otherMonth = { ...state, visibleMonth: dates.parseDateKey("2026-10-01") };
  assert.equal(dates.rollCalendarDay(otherMonth, "2026-12-31", "2027-01-01").visibleMonth, otherMonth.visibleMonth);
});

test("device-local date keys, DST weeks and midnight work in Seoul and Los Angeles", (t) => {
  const originalZone = process.env.TZ;
  t.after(() => {
    if (originalZone === undefined) delete process.env.TZ;
    else process.env.TZ = originalZone;
  });
  for (const timezone of ["Asia/Seoul", "America/Los_Angeles"]) {
    process.env.TZ = timezone;
    assert.equal(dates.toDateKey(new Date("2026-11-10T01:00:00Z")),
      timezone === "Asia/Seoul" ? "2026-11-10" : "2026-11-09");
    assert.deepEqual(dates.weekDateKeys("2026-03-06"), [
      "2026-03-06", "2026-03-07", "2026-03-08", "2026-03-09", "2026-03-10", "2026-03-11", "2026-03-12",
    ]);
    assert.deepEqual(dates.weekDateKeys("2026-10-30"), [
      "2026-10-30", "2026-10-31", "2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05",
    ]);
  }
  assert.deepEqual(dates.weekDateKeys("2026-12-29"), [
    "2026-12-29", "2026-12-30", "2026-12-31", "2027-01-01", "2027-01-02", "2027-01-03", "2027-01-04",
  ]);
});
