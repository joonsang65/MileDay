import type {
  ApiEnvelope,
  ApiErrorEnvelope,
  AuthSession,
  CalendarDateData,
  CalendarMonthData,
  CalendarWeekData,
  Goal,
  GoalCreatePayload,
  AiScheduleDraft,
  AiScheduleDraftRequest,
  GoalUpdatePayload,
  GoalWithMilestones,
  Milestone,
  MilestoneCreatePayload,
  MilestoneUpdatePayload,
  SignUpResult,
  UserSettings,
  UserSettingsUpdatePayload,
} from "./types";

const DEFAULT_API_BASE_URL = "http://localhost:8000";
const RETRYABLE_STATUSES = new Set([502, 503, 504]);
const ACCESS_TOKEN_STORAGE_KEY = "mileday.access_token";

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
    accessToken = window.mileday?.authToken ? null : localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY),
  }: {
    baseUrl?: string;
    accessToken?: string | null;
  } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.accessToken = accessToken;
  }

  setAccessToken(accessToken: string | null): void {
    this.accessToken = accessToken;
  }

  async loadStoredAccessToken(): Promise<boolean> {
    const accessToken = await readPersistedAccessToken();
    this.accessToken = accessToken;
    return Boolean(accessToken);
  }

  async persistAccessToken(accessToken: string | null): Promise<void> {
    if (accessToken) {
      await writePersistedAccessToken(accessToken);
    } else {
      await clearPersistedAccessToken();
    }
  }

  hasAccessToken(): boolean {
    return Boolean(this.accessToken);
  }

  async login(email: string, password: string, rememberLogin = true): Promise<AuthSession> {
    const session = await this.request<AuthSession>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    this.setAccessToken(session.access_token);
    await this.persistAccessToken(rememberLogin ? session.access_token : null);
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
      await this.persistAccessToken(null);
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

  async deleteAccount(): Promise<void> {
    try {
      await this.request<{ message: string }>("/auth/account", {
        method: "DELETE",
      });
    } finally {
      this.setAccessToken(null);
      await this.persistAccessToken(null);
    }
  }

  listGoalsWithMilestones(): Promise<GoalWithMilestones[]> {
    return this.request<GoalWithMilestones[]>("/goals/with-milestones");
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

  completeGoal(goalId: string, isCompleted: boolean): Promise<Goal> {
    return this.request<Goal>(`/goals/${goalId}/complete`, {
      method: "PATCH",
      body: { is_completed: isCompleted },
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

  getGoalMilestones(goalId: string): Promise<Milestone[]> {
    return this.request<Milestone[]>(`/goals/${goalId}/milestones`);
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

  createScheduleDraft(payload: AiScheduleDraftRequest): Promise<AiScheduleDraft> {
    return this.request<AiScheduleDraft>("/ai/schedule/draft", {
      method: "POST",
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
    const method = options.method ?? "GET";
    const maxAttempts = method === "GET" ? 3 : 1;
    let lastError: unknown = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        return await this.requestOnce<T>(path, { ...options, method });
      } catch (error) {
        lastError = error;
        if (!this.shouldRetry(error, attempt, maxAttempts)) {
          throw error;
        }
        await delay(attempt === 1 ? 100 : 300);
      }
    }

    throw lastError;
  }

  private async requestOnce<T>(
    path: string,
    options: {
      method: string;
      body?: unknown;
      auth?: boolean;
    },
  ): Promise<T> {
    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };

    if (options.auth !== false && this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
    }

    const response = await fetch(`${this.baseUrl}${path}`, {
      method: options.method,
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

  private shouldRetry(error: unknown, attempt: number, maxAttempts: number): boolean {
    if (attempt >= maxAttempts) {
      return false;
    }
    if (error instanceof ApiClientError) {
      return RETRYABLE_STATUSES.has(error.status);
    }
    return error instanceof TypeError;
  }
}

export const apiClient = new MileDayApiClient();

async function readPersistedAccessToken(): Promise<string | null> {
  if (window.mileday?.authToken) {
    return window.mileday.authToken.get();
  }
  return localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

async function writePersistedAccessToken(accessToken: string): Promise<void> {
  if (window.mileday?.authToken) {
    const saved = await window.mileday.authToken.set(accessToken);
    if (!saved) {
      throw new Error("Secure token storage is unavailable.");
    }
    localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    return;
  }
  localStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, accessToken);
}

async function clearPersistedAccessToken(): Promise<void> {
  if (window.mileday?.authToken) {
    await window.mileday.authToken.clear();
  }
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
