import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import calendarMonth from "../../../tests/fixtures/calendar-month.json";
import { MileDayApiClient } from "./client";

function mockFetch(payload: unknown, ok = true, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue({
    ok,
    status,
    json: vi.fn().mockResolvedValue(payload),
  });
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

function mockFetchSequence(responses: { payload: unknown; ok: boolean; status: number }[]) {
  const fetchMock = vi.fn();
  for (const response of responses) {
    fetchMock.mockResolvedValueOnce({
      ok: response.ok,
      status: response.status,
      json: vi.fn().mockResolvedValue(response.payload),
    });
  }
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

describe("MileDayApiClient", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    vi.useRealTimers();
    delete window.mileday;
  });

  it("reads the server's monthly calendar response", async () => {
    const fetchMock = mockFetch(calendarMonth);
    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: "token" });
    await expect(client.getMonthCalendar(2026, 7)).resolves.toEqual(calendarMonth.data);
    expect(fetchMock).toHaveBeenCalledWith("http://api.test/calendar/month?year=2026&month=7", expect.any(Object));
  });

  it("로그인 성공 시 access token을 저장한다", async () => {
    mockFetch({
      success: true,
      data: {
        access_token: "access-token",
        refresh_token: "refresh-token",
        expires_at: null,
        token_type: "bearer",
        user: { id: "user-1", email: "user@example.com" },
      },
    });

    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: null });
    await client.login("user@example.com", "password");

    expect(JSON.parse(localStorage.getItem("mileday.session")!)).toMatchObject({
      access_token: "access-token", refresh_token: "refresh-token",
    });
  });

  it("회원가입은 인증 헤더 없이 signup API를 호출한다", async () => {
    const fetchMock = mockFetch({
      success: true,
      data: { user_id: "user-1", email: "user@example.com" },
    });

    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: "token" });
    const result = await client.signup("user@example.com", "password123");

    expect(result).toEqual({ user_id: "user-1", email: "user@example.com" });
    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/auth/signup",
      expect.objectContaining({
        method: "POST",
        headers: expect.not.objectContaining({
          Authorization: expect.any(String),
        }),
        body: JSON.stringify({ email: "user@example.com", password: "password123" }),
      }),
    );
  });

  function session(expiresAt = Math.floor(Date.now() / 1000) + 3600) {
    return { access_token: "new-access", refresh_token: "new-refresh", expires_at: expiresAt,
      token_type: "bearer", user: { id: "user-1", email: "user@example.com" } };
  }

  function saveExpiredSession() {
    localStorage.setItem("mileday.session", JSON.stringify({
      access_token: "old-access", refresh_token: "old-refresh", expires_at: 1,
    }));
  }

  it("restores expired sessions and persists both rotated tokens", async () => {
    saveExpiredSession();
    const fetchMock = mockFetch({ success: true, data: session() });
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    expect(await client.loadStoredAccessToken()).toBe(true);
    expect(fetchMock).toHaveBeenCalledWith("http://api.test/auth/refresh", expect.objectContaining({
      body: JSON.stringify({ refresh_token: "old-refresh" }),
      headers: expect.not.objectContaining({ Authorization: expect.any(String) }),
    }));
    expect(JSON.parse(localStorage.getItem("mileday.session")!)).toMatchObject({
      access_token: "new-access", refresh_token: "new-refresh", expires_at: expect.any(Number),
    });
  });

  it("deduplicates refresh for concurrent protected requests", async () => {
    saveExpiredSession();
    const fetchMock = vi.fn().mockImplementation(async (url: string) => ({
      ok: true, status: 200,
      json: async () => ({ success: true, data: url.endsWith("/auth/refresh") ? session() : [] }),
    }));
    vi.stubGlobal("fetch", fetchMock);
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    await Promise.all([client.listGoals(), client.listGoals()]);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/auth/refresh"))).toHaveLength(1);
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/goals"))).toHaveLength(2);
  });

  it("retries a rejected authenticated request once after refreshing", async () => {
    localStorage.setItem("mileday.session", JSON.stringify(session()));
    const fetchMock = mockFetchSequence([
      { ok: false, status: 401, payload: { success: false, error: { code: "AUTH_TOKEN_EXPIRED" } } },
      { ok: true, status: 200, payload: { success: true, data: session() } },
      { ok: true, status: 200, payload: { success: true, data: [] } },
    ]);
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    await expect(client.listGoals()).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("retains saved sessions during offline startup", async () => {
    saveExpiredSession();
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("offline")));
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    expect(await client.loadStoredAccessToken()).toBe(true);
    expect(JSON.parse(localStorage.getItem("mileday.session")!).refresh_token).toBe("old-refresh");
  });

  it("clears revoked refresh sessions and announces authentication loss", async () => {
    saveExpiredSession();
    mockFetch({ success: false, error: { code: "AUTH_INVALID_TOKEN" } }, false, 401);
    const cleared = vi.fn();
    window.addEventListener("mileday-session-cleared", cleared);
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    await expect(client.loadStoredAccessToken()).rejects.toMatchObject({ status: 401 });
    expect(client.hasAccessToken()).toBe(false);
    expect(localStorage.getItem("mileday.session")).toBeNull();
    expect(cleared).toHaveBeenCalledOnce();
    window.removeEventListener("mileday-session-cleared", cleared);
  });

  it("keeps unremembered sessions only in memory through refresh", async () => {
    const fetchMock = mockFetch({ success: true, data: session(1) });
    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: null });
    await client.login("user@example.com", "password", false);
    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ success: true, data: session() }) });
    fetchMock.mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ success: true, data: [] }) });
    await client.listGoals();
    expect(client.hasAccessToken()).toBe(true);
    expect(localStorage.getItem("mileday.session")).toBeNull();
  });

  it("refreshes before expiry while running and removes lifecycle timers", async () => {
    vi.useFakeTimers();
    localStorage.setItem("mileday.session", JSON.stringify(session(Math.floor(Date.now() / 1000) + 120)));
    const fetchMock = mockFetch({ success: true, data: session() });
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    const stop = client.startSessionRefresh();
    await vi.advanceTimersByTimeAsync(60_000);
    expect(fetchMock).toHaveBeenCalledOnce();
    stop();
    expect(vi.getTimerCount()).toBe(0);
  });

  it("does not restore a session after logout during an in-flight refresh", async () => {
    saveExpiredSession();
    let finish!: (value: unknown) => void;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise((resolve) => { finish = resolve; })));
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    const restoring = client.loadStoredAccessToken();
    await Promise.resolve();
    client.setAccessToken(null);
    await client.persistAccessToken(null);
    finish({ ok: true, status: 200, json: async () => ({ success: true, data: session() }) });
    expect(await restoring).toBe(false);
    expect(localStorage.getItem("mileday.session")).toBeNull();
  });

  it("stores a complete session through Electron secure storage", async () => {
    const set = vi.fn().mockResolvedValue(true);
    window.mileday = { platform: "win32", authToken: {
      get: vi.fn().mockResolvedValue(null), set, clear: vi.fn().mockResolvedValue(true),
      isEncryptionAvailable: vi.fn().mockResolvedValue(true),
    } };
    mockFetch({ success: true, data: session() });
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    await client.login("user@example.com", "password");
    expect(JSON.parse(set.mock.calls[0][0])).toMatchObject({
      access_token: "new-access", refresh_token: "new-refresh", expires_at: expect.any(Number),
    });
    expect(localStorage.getItem("mileday.session")).toBeNull();
  });

  it("can still restore a legacy access-token-only installation", async () => {
    localStorage.setItem("mileday.access_token", "legacy-access");
    const client = new MileDayApiClient({ baseUrl: "http://api.test" });
    expect(await client.loadStoredAccessToken()).toBe(true);
  });

  it("never replays an old account's mutation using a new account's token", async () => {
    let rejectOldRequest!: (value: unknown) => void;
    const fetchMock = vi.fn().mockReturnValueOnce(new Promise((resolve) => { rejectOldRequest = resolve; }))
      .mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: session() }) });
    vi.stubGlobal("fetch", fetchMock);
    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: "account-a" });
    const creating = client.createGoal({ title: "A's goal", deadline: "2026-12-31", is_recurring: false,
      recurrence_type: null, color: "#0F766E" });
    const assertion = expect(creating).rejects.toMatchObject({ code: "SESSION_CHANGED", status: 409 });
    await Promise.resolve();
    client.setAccessToken(null);
    await client.login("b@example.com", "password");
    rejectOldRequest({ ok: false, status: 401, json: async () => ({ success: false, error: { code: "AUTH_TOKEN_EXPIRED" } }) });
    await assertion;
    expect(fetchMock.mock.calls.filter(([url]) => url.endsWith("/goals"))).toHaveLength(1);
  });

  it("does not apply a login response after the session was cleared", async () => {
    let completeLogin!: (value: unknown) => void;
    vi.stubGlobal("fetch", vi.fn().mockReturnValue(new Promise((resolve) => { completeLogin = resolve; })));
    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: null });
    const loggingIn = client.login("user@example.com", "password");
    const assertion = expect(loggingIn).rejects.toMatchObject({ code: "SESSION_CHANGED" });
    client.setAccessToken(null);
    completeLogin({ ok: true, status: 200, json: async () => ({ success: true, data: session() }) });
    await assertion;
    expect(client.hasAccessToken()).toBe(false);
    expect(localStorage.getItem("mileday.session")).toBeNull();
  });

  it.each(["logout", "deleteAccount"] as const)("a pending %s cannot clear a newer login", async (operation) => {
    let finish!: (value: unknown) => void;
    const fetchMock = vi.fn().mockReturnValueOnce(new Promise((resolve) => { finish = resolve; }))
      .mockResolvedValue({ ok: true, status: 200, json: async () => ({ success: true, data: session() }) });
    vi.stubGlobal("fetch", fetchMock);
    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: "account-a" });
    const pending = client[operation]();
    const assertion = expect(pending).rejects.toMatchObject({ code: "SESSION_CHANGED" });
    await Promise.resolve();
    await client.login("b@example.com", "password");
    finish({ ok: true, status: 200, json: async () => ({ success: true, data: {} }) });
    await assertion;
    expect(client.hasAccessToken()).toBe(true);
    expect(JSON.parse(localStorage.getItem("mileday.session")!).refresh_token).toBe("new-refresh");
  });

  it("보호 API 호출은 Authorization 헤더를 포함한다", async () => {
    const fetchMock = mockFetch({
      success: true,
      data: { date: "2026-07-10", goals: [], milestones: [] },
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });
    await client.getDateCalendar("2026-07-10");

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/calendar/date/2026-07-10",
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer access-token",
        }),
      }),
    );
  });

  it("목표 목록을 조회한다", async () => {
    const fetchMock = mockFetch({
      success: true,
      data: [],
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });
    await client.listGoals();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/goals",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer access-token",
        }),
      }),
    );
  });

  it("목표와 마일스톤 통합 목록을 조회한다", async () => {
    const fetchMock = mockFetch({
      success: true,
      data: [],
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });
    await client.listGoalsWithMilestones();

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/goals/with-milestones",
      expect.objectContaining({
        method: "GET",
        headers: expect.objectContaining({
          Authorization: "Bearer access-token",
        }),
      }),
    );
  });

  it("목표 생성 payload를 그대로 전송한다", async () => {
    const payload = {
      title: "포트폴리오 준비",
      deadline: "2026-07-31",
      is_completed: false,
      is_recurring: true,
      recurrence_type: "weekly" as const,
      color: "#0F766E",
    };
    const fetchMock = mockFetch({
      success: true,
      data: {
        id: "goal-1",
        ...payload,
        user_id: "user-1",
        created_at: "2026-07-01T10:00:00+09:00",
        updated_at: "2026-07-01T10:00:00+09:00",
      },
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });
    await client.createGoal(payload);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/goals",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
  });

  it("마일스톤 생성 payload를 목표 하위 endpoint로 전송한다", async () => {
    const payload = {
      title: "이력서 초안 작성",
      scheduled_date: "2026-07-10",
      color: "#D97706",
    };
    const fetchMock = mockFetch({
      success: true,
      data: {
        id: "milestone-1",
        goal_id: "goal-1",
        user_id: "user-1",
        is_completed: false,
        created_at: "2026-07-01T10:00:00+09:00",
        updated_at: "2026-07-01T10:00:00+09:00",
        ...payload,
      },
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });
    await client.createMilestone("goal-1", payload);

    expect(fetchMock).toHaveBeenCalledWith(
      "http://api.test/goals/goal-1/milestones",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(payload),
      }),
    );
  });

  it("공통 오류 응답을 ApiClientError로 변환한다", async () => {
    mockFetch(
      {
        success: false,
        error: { code: "UNAUTHORIZED", message: "인증이 필요합니다." },
        request_id: "req-1",
      },
      false,
      401,
    );

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "bad-token",
    });

    await expect(client.getTodayMilestones()).rejects.toMatchObject({
      code: "UNAUTHORIZED",
      status: 401,
      requestId: "req-1",
    });
  });

  it("sends goal update and delete requests to goal item endpoints", async () => {
    const fetchMock = mockFetch({
      success: true,
      data: {
        id: "goal-1",
        title: "Updated",
        deadline: "2026-07-31",
        is_completed: false,
        is_recurring: false,
        recurrence_type: null,
        color: "#0F766E",
        created_at: "2026-07-01T10:00:00+09:00",
        updated_at: "2026-07-01T10:00:00+09:00",
      },
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });

    await client.updateGoal("goal-1", { title: "Updated" });
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/goals/goal-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ title: "Updated" }),
      }),
    );

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({ success: true, data: { message: "deleted" } }),
    });

    await client.deleteGoal("goal-1");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/goals/goal-1",
      expect.objectContaining({
        method: "DELETE",
      }),
    );
  });

  it("sends goal complete requests to the goal complete endpoint", async () => {
    const fetchMock = mockFetch({
      success: true,
      data: {
        id: "goal-1",
        title: "Updated",
        deadline: "2026-07-31",
        is_completed: true,
        is_recurring: false,
        recurrence_type: null,
        color: "#0F766E",
        created_at: "2026-07-01T10:00:00+09:00",
        updated_at: "2026-07-01T10:00:00+09:00",
      },
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });

    await client.completeGoal("goal-1", true);
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/goals/goal-1/complete",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ is_completed: true }),
      }),
    );
  });

  it("sends milestone update and delete requests to milestone item endpoints", async () => {
    const fetchMock = mockFetch({
      success: true,
      data: {
        id: "milestone-1",
        goal_id: "goal-1",
        user_id: "user-1",
        title: "Updated",
        scheduled_date: "2026-07-11",
        color: "#D97706",
        is_completed: false,
        created_at: "2026-07-01T10:00:00+09:00",
        updated_at: "2026-07-01T10:00:00+09:00",
      },
    });

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });

    await client.updateMilestone("milestone-1", { scheduled_date: "2026-07-11" });
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/milestones/milestone-1",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ scheduled_date: "2026-07-11" }),
      }),
    );

    fetchMock.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: vi.fn().mockResolvedValue({ success: true, data: { message: "deleted" } }),
    });

    await client.deleteMilestone("milestone-1");
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/milestones/milestone-1",
      expect.objectContaining({
        method: "DELETE",
      }),
    );
  });

  it("sends settings get and update requests to settings endpoint", async () => {
    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });
    let fetchMock = mockFetch({
      success: true,
      data: {
        calendar_view: "month",
        holiday_display: "normal",
        week_starts_on: 0,
        language: "ko",
        timezone: "Asia/Seoul",
        gemini_data_consent: false,
      },
    });

    await client.getSettings();
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/settings",
      expect.objectContaining({ method: "GET" }),
    );

    fetchMock = mockFetch({
      success: true,
      data: {
        calendar_view: "week",
        holiday_display: "weekend_like",
        week_starts_on: 0,
        language: "en",
        timezone: "Asia/Seoul",
        gemini_data_consent: true,
      },
    });

    await client.updateSettings({
      calendar_view: "week",
      holiday_display: "weekend_like",
      week_starts_on: 0,
      language: "en",
      gemini_data_consent: true,
    });
    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/settings",
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({
          calendar_view: "week",
          holiday_display: "weekend_like",
          week_starts_on: 0,
          language: "en",
          gemini_data_consent: true,
        }),
      }),
    );
  });

  it("sends account deletion request and clears the access token", async () => {
    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });
    const fetchMock = mockFetch({
      success: true,
      data: { message: "deleted" },
    });

    await client.deleteAccount();

    expect(fetchMock).toHaveBeenLastCalledWith(
      "http://api.test/auth/account",
      expect.objectContaining({
        method: "DELETE",
        headers: expect.objectContaining({ Authorization: "Bearer access-token" }),
      }),
    );
    expect(client.hasAccessToken()).toBe(false);
  });

  it("keeps backend error detail for troubleshooting", async () => {
    mockFetch(
      {
        success: false,
        error: {
          code: "GOAL_CREATE_FAILED",
          message: "Failed to create goal.",
          detail: { message: "Could not find the 'color' column" },
        },
        request_id: "req-2",
      },
      false,
      500,
    );

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });

    await expect(
      client.createGoal({
        title: "Debug goal",
        deadline: "2026-07-31",
        is_recurring: false,
        recurrence_type: null,
        color: "#0F766E",
      }),
    ).rejects.toMatchObject({
      code: "GOAL_CREATE_FAILED",
      status: 500,
      requestId: "req-2",
      detail: { message: "Could not find the 'color' column" },
    });
  });

  it("retries transient GET upstream errors", async () => {
    vi.useFakeTimers();
    const fetchMock = mockFetchSequence([
      {
        ok: false,
        status: 502,
        payload: {
          success: false,
          error: { code: "UPSTREAM_DISCONNECTED", message: "Upstream disconnected." },
        },
      },
      {
        ok: true,
        status: 200,
        payload: {
          success: true,
          data: { date: "2026-07-10", is_today: false, goal_count: 0, milestone_count: 0, completed_milestone_count: 0, goals: [], milestones: [] },
        },
      },
    ]);

    const client = new MileDayApiClient({
      baseUrl: "http://api.test",
      accessToken: "access-token",
    });

    const resultPromise = client.getDateCalendar("2026-07-10");
    await vi.advanceTimersByTimeAsync(100);
    await expect(resultPromise).resolves.toMatchObject({ date: "2026-07-10" });
    expect(fetchMock).toHaveBeenCalledTimes(2);
    vi.useRealTimers();
  });
});
