import type {
  ApiEnvelope,
  ApiErrorEnvelope,
  AuthSession,
  CalendarDateData,
  CalendarMonthData,
  CalendarWeekData,
  Goal,
  GoalCreatePayload,
  GoalUpdatePayload,
  Milestone,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  SignUpResult,
  UserSettings,
  UserSettingsUpdatePayload,
} from "./types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";

export class ApiClientError extends Error {
  code: string;
  status: number;
  requestId?: string;
  detail?: unknown;

  constructor({
    code,
    message,
    status,
    requestId,
    detail,
  }: {
    code: string;
    message: string;
    status: number;
    requestId?: string;
    detail?: unknown;
  }) {
    super(message);
    this.name = "ApiClientError";
    this.code = code;
    this.status = status;
    this.requestId = requestId;
    this.detail = detail;
  }
}

export class MileDayApiClient {
  private readonly baseUrl: string;
  private accessToken: string | null;

  constructor({
    baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
    accessToken = localStorage.getItem("mileday.access_token"),
  }: {
    baseUrl?: string;
    accessToken?: string | null;
  } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.accessToken = accessToken;
  }

  setAccessToken(accessToken: string | null): void {
    this.accessToken = accessToken;
    if (accessToken) {
      localStorage.setItem("mileday.access_token", accessToken);
    } else {
      localStorage.removeItem("mileday.access_token");
    }
  }

  hasAccessToken(): boolean {
    return Boolean(this.accessToken);
  }

  async login(email: string, password: string): Promise<AuthSession> {
    const session = await this.request<AuthSession>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    this.setAccessToken(session.access_token);
    return session;
  }

  async signup(email: string, password: string): Promise<SignUpResult> {
    return this.request<SignUpResult>("/auth/signup", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
  }

  async logout(): Promise<void> {
    try {
      await this.request<{ message: string }>("/auth/logout", {
        method: "POST",
      });
    } finally {
      this.setAccessToken(null);
    }
  }

  getMonthCalendar(year: number, month: number): Promise<CalendarMonthData> {
    return this.request<CalendarMonthData>(
      `/calendar/month?year=${year}&month=${month}`,
    );
  }

  getWeekCalendar(startDate: string): Promise<CalendarWeekData> {
    return this.request<CalendarWeekData>(
      `/calendar/week?start_date=${startDate}`,
    );
  }

  getDateCalendar(date: string): Promise<CalendarDateData> {
    return this.request<CalendarDateData>(`/calendar/date/${date}`);
  }

  listGoals(): Promise<Goal[]> {
    return this.request<Goal[]>("/goals");
  }

  createGoal(payload: GoalCreatePayload): Promise<Goal> {
    return this.request<Goal>("/goals", {
      method: "POST",
      body: payload,
    });
  }

  updateGoal(goalId: string, payload: GoalUpdatePayload): Promise<Goal> {
    return this.request<Goal>(`/goals/${goalId}`, {
      method: "PATCH",
      body: payload,
    });
  }

  deleteGoal(goalId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/goals/${goalId}`, {
      method: "DELETE",
    });
  }

  createMilestone(goalId: string, payload: MilestoneCreatePayload): Promise<Milestone> {
    return this.request<Milestone>(`/goals/${goalId}/milestones`, {
      method: "POST",
      body: payload,
    });
  }

  updateMilestone(milestoneId: string, payload: MilestoneUpdatePayload): Promise<Milestone> {
    return this.request<Milestone>(`/milestones/${milestoneId}`, {
      method: "PATCH",
      body: payload,
    });
  }

  deleteMilestone(milestoneId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/milestones/${milestoneId}`, {
      method: "DELETE",
    });
  }

  getTodayMilestones(): Promise<Milestone[]> {
    return this.request<Milestone[]>("/milestones/today");
  }

  completeMilestone(milestoneId: string, isCompleted: boolean): Promise<Milestone> {
    return this.request<Milestone>(`/milestones/${milestoneId}/complete`, {
      method: "PATCH",
      body: { is_completed: isCompleted },
    });
  }

  getSettings(): Promise<UserSettings> {
    return this.request<UserSettings>("/settings");
  }

  updateSettings(payload: UserSettingsUpdatePayload): Promise<UserSettings> {
    return this.request<UserSettings>("/settings", {
      method: "PATCH",
      body: payload,
    });
  }

  private async request<T>(
    path: string,
    options: {
      method?: string;
      body?: unknown;
      auth?: boolean;
    } = {},
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (options.auth !== false && this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    const payload = (await response.json()) as ApiEnvelope<T> | ApiErrorEnvelope;
    if (!response.ok || payload.success === false) {
      const errorPayload = payload as ApiErrorEnvelope;
      throw new ApiClientError({
        code: errorPayload.error?.code ?? "UNKNOWN_ERROR",
        message: errorPayload.error?.message ?? "요청을 처리하지 못했습니다.",
        status: response.status,
        requestId: errorPayload.request_id,
        detail: errorPayload.error?.detail,
      });
    }

    return (payload as ApiEnvelope<T>).data;
  }
}

export const apiClient = new MileDayApiClient();
