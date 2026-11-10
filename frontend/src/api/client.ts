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
const SESSION_STORAGE_KEY = "mileday.session";
const REFRESH_MARGIN_MS = 60_000;

type StoredSession = {
  access_token: string;
  refresh_token: string | null;
  expires_at: number | null;
};

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
  private refreshToken: string | null = null;
  private expiresAt: number | null = null;
  private rememberLogin = false;
  private sessionRevision = 0;
  private refreshPromise: Promise<void> | null = null;
  private persistenceQueue: Promise<void> = Promise.resolve();
  private refreshTimer: number | undefined;
  private refreshEnabled = false;

  constructor({
    baseUrl = import.meta.env.VITE_API_BASE_URL || DEFAULT_API_BASE_URL,
    accessToken,
  }: {
    baseUrl?: string;
    accessToken?: string | null;
  } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    const stored = !window.mileday?.authToken && accessToken === undefined
      ? parseStoredSession(localStorage.getItem(SESSION_STORAGE_KEY) ?? localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY))
      : null;
    this.accessToken = accessToken ?? stored?.access_token ?? null;
    this.refreshToken = stored?.refresh_token ?? null;
    this.expiresAt = stored?.expires_at ?? getTokenExpiry(this.accessToken);
    this.rememberLogin = Boolean(stored);
  }

  setAccessToken(accessToken: string | null): void {
    this.sessionRevision += 1;
    this.accessToken = accessToken;
    this.refreshToken = null;
    this.expiresAt = getTokenExpiry(accessToken);
    this.refreshPromise = null;
    window.clearTimeout(this.refreshTimer);
  }

  async loadStoredAccessToken(): Promise<boolean> {
    const revision = this.sessionRevision;
    const stored = parseStoredSession(await readPersistedAccessToken());
    if (revision !== this.sessionRevision) return this.hasAccessToken();
    this.accessToken = stored?.access_token ?? null;
    this.refreshToken = stored?.refresh_token ?? null;
    this.expiresAt = stored?.expires_at ?? getTokenExpiry(this.accessToken);
    this.rememberLogin = Boolean(stored);
    try {
      await this.refreshSession();
    } catch (error) {
      if (!this.accessToken) throw error;
      // Offline startup keeps the saved session available for a later retry.
    }
    this.scheduleRefresh();
    return this.hasAccessToken();
  }

  async persistAccessToken(accessToken: string | null): Promise<void> {
    if (accessToken) {
      if (accessToken !== this.accessToken) this.setAccessToken(accessToken);
      this.rememberLogin = true;
      await this.persistSession();
    } else {
      await this.queuePersistence(() => clearPersistedAccessToken());
    }
  }

  hasAccessToken(): boolean {
    return Boolean(this.accessToken);
  }

  async login(email: string, password: string, rememberLogin = true): Promise<AuthSession> {
    const revision = this.sessionRevision;
    const session = await this.request<AuthSession>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    this.assertSessionRevision(revision);
    this.sessionRevision += 1;
    this.refreshPromise = null;
    this.rememberLogin = rememberLogin;
    this.applySession(session);
    await this.persistSession();
    this.scheduleRefresh();
    return session;
  }

  startSessionRefresh(): () => void {
    this.refreshEnabled = true;
    const resume = () => {
      if (document.visibilityState === "hidden") return;
      void this.refreshSession().catch(() => undefined).finally(() => this.scheduleRefresh());
    };
    window.addEventListener("focus", resume);
    window.addEventListener("online", resume);
    document.addEventListener("visibilitychange", resume);
    this.scheduleRefresh();
    return () => {
      this.refreshEnabled = false;
      window.clearTimeout(this.refreshTimer);
      window.removeEventListener("focus", resume);
      window.removeEventListener("online", resume);
      document.removeEventListener("visibilitychange", resume);
    };
  }

  private applySession(session: Pick<AuthSession, "access_token" | "refresh_token" | "expires_at">): void {
    if (!session || typeof session.access_token !== "string" || !session.access_token
      || typeof session.refresh_token !== "string" || !session.refresh_token) {
      throw new ApiClientError({ code: "INVALID_AUTH_RESPONSE", message: "Invalid authentication response.", status: 502 });
    }
    this.accessToken = session.access_token;
    this.refreshToken = session.refresh_token;
    this.expiresAt = session.expires_at ?? getTokenExpiry(session.access_token);
  }

  private queuePersistence(operation: () => Promise<void>): Promise<void> {
    const pending = this.persistenceQueue.catch(() => undefined).then(operation);
    this.persistenceQueue = pending;
    return pending;
  }

  private persistSession(): Promise<void> {
    const revision = this.sessionRevision;
    const serialized = JSON.stringify({
      access_token: this.accessToken,
      refresh_token: this.refreshToken,
      expires_at: this.expiresAt,
    });
    const remember = this.rememberLogin;
    return this.queuePersistence(async () => {
      if (revision !== this.sessionRevision) return;
      if (remember) await writePersistedAccessToken(serialized);
      else await clearPersistedAccessToken();
    });
  }

  private scheduleRefresh(): void {
    window.clearTimeout(this.refreshTimer);
    if (!this.refreshEnabled || !this.refreshToken) return;
    const delayMs = this.expiresAt === null ? 30_000
      : Math.max(30_000, this.expiresAt * 1000 - Date.now() - REFRESH_MARGIN_MS);
    this.refreshTimer = window.setTimeout(() => {
      void this.refreshSession().catch(() => undefined).finally(() => this.scheduleRefresh());
    }, Math.min(delayMs, 2_147_483_647));
  }

  private async refreshSession(force = false): Promise<void> {
    if (this.refreshPromise) return this.refreshPromise;
    if (!this.refreshToken || (!force && (this.expiresAt === null || this.expiresAt * 1000 > Date.now() + REFRESH_MARGIN_MS))) return;
    const revision = this.sessionRevision;
    const refreshToken = this.refreshToken;
    const operation = (async () => {
      try {
        const session = await this.requestOnce<AuthSession>("/auth/refresh", {
          method: "POST", auth: false, body: { refresh_token: refreshToken },
        });
        if (revision !== this.sessionRevision) return;
        this.applySession(session);
        await this.persistSession();
      } catch (error) {
        if (revision === this.sessionRevision && error instanceof ApiClientError && [400, 401, 403].includes(error.status)) {
          this.setAccessToken(null);
          await this.persistAccessToken(null);
          window.dispatchEvent(new Event("mileday-session-cleared"));
        }
        throw error;
      }
    })();
    this.refreshPromise = operation;
    try {
      await operation;
    } finally {
      if (this.refreshPromise === operation) this.refreshPromise = null;
      this.scheduleRefresh();
    }
  }

  async signup(email: string, password: string): Promise<SignUpResult> {
    return this.request<SignUpResult>("/auth/signup", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
  }

  async logout(): Promise<void> {
    const revision = this.sessionRevision;
    try {
      await this.request<{ message: string }>("/auth/logout", {
        method: "POST",
      });
    } finally {
      if (revision === this.sessionRevision) {
        this.setAccessToken(null);
        await this.persistAccessToken(null);
      }
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
    const revision = this.sessionRevision;
    try {
      await this.request<{ message: string }>("/auth/account", {
        method: "DELETE",
      });
    } finally {
      if (revision === this.sessionRevision) {
        this.setAccessToken(null);
        await this.persistAccessToken(null);
      }
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
    const revision = options.auth === false ? null : this.sessionRevision;
    const maxAttempts = method === "GET" ? 3 : 1;
    let lastError: unknown = null;

    for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
      try {
        this.assertSessionRevision(revision);
        if (options.auth !== false) await this.refreshSession();
        this.assertSessionRevision(revision);
        const usedToken = this.accessToken;
        try {
          const result = await this.requestOnce<T>(path, { ...options, method });
          this.assertSessionRevision(revision);
          return result;
        } catch (error) {
          this.assertSessionRevision(revision);
          if (options.auth === false || !(error instanceof ApiClientError) || error.status !== 401 || !this.refreshToken) throw error;
          if (usedToken === this.accessToken) await this.refreshSession(true);
          this.assertSessionRevision(revision);
          const result = await this.requestOnce<T>(path, { ...options, method });
          this.assertSessionRevision(revision);
          return result;
        }
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

  private assertSessionRevision(revision: number | null): void {
    if (revision !== null && revision !== this.sessionRevision) {
      throw new ApiClientError({ code: "SESSION_CHANGED", message: "Session changed. Please try again.", status: 409 });
    }
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
  return localStorage.getItem(SESSION_STORAGE_KEY) ?? localStorage.getItem(ACCESS_TOKEN_STORAGE_KEY);
}

async function writePersistedAccessToken(accessToken: string): Promise<void> {
  if (window.mileday?.authToken) {
    const saved = await window.mileday.authToken.set(accessToken);
    if (!saved) {
      throw new Error("Secure token storage is unavailable.");
    }
    localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
    localStorage.removeItem(SESSION_STORAGE_KEY);
    return;
  }
  localStorage.setItem(SESSION_STORAGE_KEY, accessToken);
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

async function clearPersistedAccessToken(): Promise<void> {
  if (window.mileday?.authToken) {
    await window.mileday.authToken.clear();
  }
  localStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
  localStorage.removeItem(SESSION_STORAGE_KEY);
}

function getTokenExpiry(token: string | null): number | null {
  if (!token) return null;
  try {
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return typeof payload.exp === "number" && Number.isFinite(payload.exp) ? payload.exp : null;
  } catch {
    return null;
  }
}

function parseStoredSession(value: string | null): StoredSession | null {
  if (!value) return null;
  if (!value.startsWith("{")) {
    return { access_token: value, refresh_token: null, expires_at: getTokenExpiry(value) };
  }
  try {
    const session = JSON.parse(value);
    if (typeof session.access_token !== "string" || !session.access_token) return null;
    return {
      access_token: session.access_token,
      refresh_token: typeof session.refresh_token === "string" ? session.refresh_token : null,
      expires_at: typeof session.expires_at === "number" && Number.isFinite(session.expires_at)
        ? session.expires_at : getTokenExpiry(session.access_token),
    };
  } catch {
    return null;
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}
