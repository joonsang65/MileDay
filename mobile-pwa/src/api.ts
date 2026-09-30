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

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export class ApiClient {
  private accessToken = localStorage.getItem(ACCESS_TOKEN_KEY);
  private userId = localStorage.getItem(USER_ID_KEY);
  private baseUrl = API_BASE_URL.replace(/\/$/, "");

  hasSession() {
    return Boolean(this.accessToken);
  }

  getUserId() {
    return this.userId;
  }

  clearSession() {
    this.accessToken = null;
    this.userId = null;
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(USER_ID_KEY);
    window.dispatchEvent(new Event("mileday-mobile-session-cleared"));
  }

  async login(email: string, password: string) {
    const session = await this.request<AuthSession>("/auth/login", {
      method: "POST",
      auth: false,
      body: { email, password },
    });
    this.accessToken = session.access_token;
    this.userId = session.user.id;
    localStorage.setItem(ACCESS_TOKEN_KEY, session.access_token);
    localStorage.setItem(USER_ID_KEY, session.user.id);
    return session;
  }

  async logout() {
    try {
      await this.request("/auth/logout", { method: "POST" });
    } finally {
      this.clearSession();
    }
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
    return this.request("/push/test", { method: "POST" });
  }

  private async request<T = unknown>(
    path: string,
    options: { method?: string; auth?: boolean; body?: unknown } = {},
  ): Promise<T> {
    const headers: Record<string, string> = {};
    if (options.body) {
      headers["Content-Type"] = "application/json";
    }
    if (options.auth !== false && this.accessToken) {
      headers.Authorization = `Bearer ${this.accessToken}`;
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
    if (!response.ok || payload?.success === false) {
      if (response.status === 401 || response.status === 403) {
        this.clearSession();
      }
      throw new ApiError(payload?.error?.message || "Request failed.", response.status);
    }
    return (payload as ApiEnvelope<T>).data;
  }
}

export const api = new ApiClient();
