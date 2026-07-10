import { beforeEach, describe, expect, it, vi } from "vitest";

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

describe("MileDayApiClient", () => {
  beforeEach(() => {
    localStorage.clear();
    vi.unstubAllGlobals();
  });

  it("로그인 성공 시 access token을 저장한다", async () => {
    mockFetch({
      success: true,
      data: {
        access_token: "access-token",
        refresh_token: "refresh-token",
        token_type: "bearer",
        user: { id: "user-1", email: "user@example.com" },
      },
    });

    const client = new MileDayApiClient({ baseUrl: "http://api.test", accessToken: null });
    await client.login("user@example.com", "password");

    expect(localStorage.getItem("mileday.access_token")).toBe("access-token");
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

  it("목표 생성 payload를 그대로 전송한다", async () => {
    const payload = {
      title: "포트폴리오 준비",
      deadline: "2026-07-31",
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
});
