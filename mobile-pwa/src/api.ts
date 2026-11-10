import type {
  ApiEnvelope,
  AuthSession,
  CalendarDateData,
  CalendarMonthData,
  NotificationSettings,
  PushConfig,
} from "./types";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
const ACCESS_TOKEN_KEY = "mileday.mobile.access_token";
const USER_ID_KEY = "mileday.mobile.user_id";
const SESSION_KEY = "mileday.mobile.session";
const REFRESH_AHEAD_MS = 60_000;
const RETRY_MS = 30_000;

type StoredSession = Omit<AuthSession, "refresh_token" | "expires_at"> & {
  refresh_token: string | null;
  expires_at: number | null;
};

function isAuthSession(value: unknown): value is AuthSession {
  const session = value as AuthSession | null;
  return Boolean(session && typeof session.access_token === "string" && session.access_token &&
    typeof session.refresh_token === "string" && session.refresh_token &&
    typeof session.expires_at === "number" && Number.isFinite(session.expires_at) && session.expires_at > 0 &&
    session.token_type === "bearer" && typeof session.user?.id === "string" && session.user.id &&
    typeof session.user.email === "string");
}

function readSession(): StoredSession | null {
  try {
    const raw = localStorage.getItem(SESSION_KEY);
    if (raw) {
      const session: unknown = JSON.parse(raw);
      return isAuthSession(session) ? session : null;
    }
    // Existing installations can keep using their access token until it expires.
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    const userId = localStorage.getItem(USER_ID_KEY);
    return token && userId ? {
      access_token: token, refresh_token: null, expires_at: null,
      token_type: "bearer", user: { id: userId, email: "" },
    } : null;
  } catch {
    return null;
  }
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class ApiClient {
  private session = readSession();
  private generation = 0;
  private refreshInFlight: Promise<void> | null = null;
  private baseUrl = API_BASE_URL.replace(/\/$/, "");

  hasSession() {
    return Boolean(this.session);
  }

  getUserId() {
    return this.session?.user.id || null;
  }

  clearSession() {
    try {
      localStorage.removeItem(SESSION_KEY);
      localStorage.removeItem(ACCESS_TOKEN_KEY);
      localStorage.removeItem(USER_ID_KEY);
    } finally {
      this.adoptSession(null);
    }
  }

  async login(email: string, password: string) {
    const generation = this.generation;
    const session = await this.request<AuthSession>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    if (generation !== this.generation) {
      throw new ApiError("Session changed. Please try again.", 409);
    }
    this.persistSession(session);
    return session;
  }

  async logout() {
    try {
      await this.request("/auth/logout", { method: "POST" });
    } finally {
      this.clearSession();
    }
  }

  // One refresh promise covers startup, timers, and all concurrent API requests.
  async ensureSession() {
    this.syncSession();
    if (this.refreshInFlight) {
      return this.refreshInFlight;
    }
    if (this.session?.refresh_token && this.session.expires_at !== null &&
      this.session.expires_at * 1000 - Date.now() <= REFRESH_AHEAD_MS) {
      await this.refreshSession();
    }
  }

  startSessionMaintenance() {
    let stopped = false;
    let timer: number;
    const schedule = (retry = false) => {
      window.clearTimeout(timer);
      if (stopped || !this.session?.refresh_token) {
        return;
      }
      const remaining = (this.session.expires_at || 0) * 1000 - Date.now() - REFRESH_AHEAD_MS;
      timer = window.setTimeout(check, retry ? RETRY_MS : Math.min(2_147_483_647, Math.max(1000, remaining)));
    };
    const check = () => {
      void this.ensureSession().then(() => schedule(), () => schedule(true));
    };
    const visible = () => {
      if (document.visibilityState === "visible") check();
    };
    const storage = (event: StorageEvent) => {
      if (event.key === SESSION_KEY || event.key === null) {
        this.syncSession();
        check();
      }
    };
    const changed = () => schedule();
    window.addEventListener("focus", check);
    window.addEventListener("online", check);
    window.addEventListener("storage", storage);
    window.addEventListener("mileday-mobile-session-changed", changed);
    window.addEventListener("mileday-mobile-session-cleared", changed);
    document.addEventListener("visibilitychange", visible);
    check();
    return () => {
      stopped = true;
      window.clearTimeout(timer);
      window.removeEventListener("focus", check);
      window.removeEventListener("online", check);
      window.removeEventListener("storage", storage);
      window.removeEventListener("mileday-mobile-session-changed", changed);
      window.removeEventListener("mileday-mobile-session-cleared", changed);
      document.removeEventListener("visibilitychange", visible);
    };
  }

  private adoptSession(session: StoredSession | null) {
    this.session = session;
    this.generation += 1;
    this.refreshInFlight = null;
    window.dispatchEvent(new Event(session ? "mileday-mobile-session-changed" : "mileday-mobile-session-cleared"));
  }

  private syncSession() {
    const stored = readSession();
    if (JSON.stringify(stored) !== JSON.stringify(this.session)) {
      this.adoptSession(stored);
    }
  }

  private persistSession(session: AuthSession) {
    if (!isAuthSession(session)) {
      throw new ApiError("Invalid authentication response.", 502);
    }
    // A single atomic write prevents mixing tokens from different rotations.
    localStorage.setItem(SESSION_KEY, JSON.stringify(session));
    this.adoptSession(session);
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_ID_KEY);
  }

  private refreshSession(): Promise<void> {
    if (this.refreshInFlight) return this.refreshInFlight;
    const generation = this.generation;
    const session = this.session;
    if (!session?.refresh_token) return Promise.reject(new ApiError("Please log in again.", 401));
    const refresh = async () => {
      this.syncSession();
      // Another tab may have already rotated the token while we waited for the lock.
      if (this.session?.user.id === session.user.id && this.session.refresh_token !== session.refresh_token) {
        return;
      }
      if (generation !== this.generation) throw new ApiError("Session changed.", 409);
      const currentGeneration = this.generation;
      let next: AuthSession;
      try {
        next = await this.request<AuthSession>("/auth/refresh", {
          method: "POST", auth: false, body: { refresh_token: session.refresh_token },
        });
      } catch (error) {
        this.syncSession();
        if (currentGeneration === this.generation && error instanceof ApiError &&
          [400, 401, 403].includes(error.status)) this.clearSession();
        throw error;
      }
      this.syncSession();
      if (currentGeneration !== this.generation) throw new ApiError("Session changed.", 409);
      if (!isAuthSession(next) || next.user.id !== session.user.id) {
        throw new ApiError("Invalid authentication response.", 502);
      }
      this.persistSession(next);
    };
    const pending = (async () => {
      if (typeof navigator !== "undefined" && navigator.locks) {
        await navigator.locks.request(`mileday-session:${this.baseUrl}`, refresh);
      } else {
        await refresh();
      }
    })().finally(() => {
      if (this.refreshInFlight === pending) this.refreshInFlight = null;
    });
    this.refreshInFlight = pending;
    return pending;
  }

  getToday(date: string) {
    return this.request<CalendarDateData>(`/calendar/date/${date}`);
  }

  getMonth(year: number, month: number) {
    return this.request<CalendarMonthData>(`/calendar/month?year=${year}&month=${month}`);
  }

  getPushConfig() {
    return this.request<PushConfig>("/push/config", { auth: false });
  }

  getNotificationSettings() {
    return this.request<NotificationSettings>("/push/settings");
  }

  updateNotificationSettings(payload: Partial<NotificationSettings>) {
    return this.request<NotificationSettings>("/push/settings", {
      method: "PATCH",
      body: payload,
    });
  }

  subscribe(subscription: PushSubscriptionJSON) {
    return this.request("/push/subscribe", {
      method: "POST",
      body: subscription,
    });
  }

  unsubscribe(subscription: PushSubscriptionJSON) {
    return this.request("/push/unsubscribe", {
      method: "POST",
      body: subscription,
    });
  }

  sendTestPush() {
    return this.request<{ sent: number; removed: number; reason?: "no_incomplete_milestones" }>("/push/test", { method: "POST" });
  }

  private async request<T = unknown>(
    path: string,
    options: { method?: string; auth?: boolean; body?: unknown } = {},
    retried = false,
  ): Promise<T> {
    const authenticated = options.auth !== false;
    if (authenticated && !retried) await this.ensureSession();
    if (authenticated && !this.session) throw new ApiError("Please log in again.", 401);
    const token = this.session?.access_token;
    const userId = this.session?.user.id;
    const headers: Record<string, string> = {};
    if (options.body) {
      headers["Content-Type"] = "application/json";
    }
    if (authenticated && token) {
      headers.Authorization = `Bearer ${token}`;
    }

    let response: Response;
    try {
      response = await fetch(`${this.baseUrl}${path}`, {
        method: options.method || "GET",
        headers,
        body: options.body ? JSON.stringify(options.body) : undefined,
      });
    } catch (error) {
      throw new ApiError(
        `서버에 연결할 수 없습니다. API 주소와 CORS 설정을 확인하세요. (${path})`,
        0,
      );
    }
    const payload = await response.json().catch(() => null);
    if (authenticated) {
      this.syncSession();
      if (this.session?.user.id !== userId) throw new ApiError("Session changed.", 409);
    }
    if (!response.ok || payload?.success === false) {
      const unauthorized = response.status === 401 || payload?.error?.code === "AUTH_TOKEN_EXPIRED";
      if (authenticated && unauthorized && token) {
        if (!retried && this.session) {
          if (this.session.access_token === token && this.session.refresh_token) {
            await this.refreshSession();
            return this.request<T>(path, options, true);
          }
          if (this.session?.access_token !== token) return this.request<T>(path, options, true);
        }
        if (this.session?.access_token === token) this.clearSession();
      }
      throw new ApiError(payload?.error?.message || "Request failed.", response.status);
    }
    if (!payload || payload.success !== true) throw new ApiError("Invalid API response.", 502);
    return (payload as ApiEnvelope<T>).data;
  }
}

export const api = new ApiClient();
