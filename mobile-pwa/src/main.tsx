import React from "react";
import ReactDOM from "react-dom/client";
import { Bell, CalendarDays, ChevronLeft, ChevronRight, LogOut, Settings, Sun } from "lucide-react";

import { api } from "./api";
import { displayDate, isInMonth, monthGrid, monthLabel, moveMonth, parseDateKey, rollCalendarDay, todayKey, toDateKey, watchDay, weekDateKeys } from "./date";
import type { DayState } from "./date";
import {
  clearMonthCache,
  getDateWithCache,
  getMonthWithCache,
  preloadExtraMonths,
  preloadRequiredMonths,
  readCachedDate,
  readCachedMonth,
} from "./month-cache";
import { disablePush, enablePush, isPushSupported, registerServiceWorker } from "./push";
import type { CalendarDateData, CalendarMonthData, Goal, Milestone, NotificationSettings } from "./types";
import "./styles.css";

type Tab = "today" | "calendar" | "settings";
type PreloadStatus = "idle" | "loading" | "ready" | "error";

function tabFromLocation(): Tab {
  const route = location.hash || location.pathname;
  if (route.includes("calendar")) {
    return "calendar";
  }
  if (route.includes("settings")) {
    return "settings";
  }
  return "today";
}

function App() {
  const [isAuthed, setIsAuthed] = React.useState(api.hasSession());
  const [sessionUserId, setSessionUserId] = React.useState(api.getUserId());
  const [tab, setTab] = React.useState<Tab>(tabFromLocation);
  const [preloadStatus, setPreloadStatus] = React.useState<PreloadStatus>(api.hasSession() ? "loading" : "idle");
  const [preloadError, setPreloadError] = React.useState("");
  const [preloadAttempt, setPreloadAttempt] = React.useState(0);
  const [day, setDay] = React.useState<DayState>(() => ({ today: todayKey(), revision: 0 }));

  React.useEffect(() => watchDay(setDay), []);

  React.useEffect(() => {
    void registerServiceWorker();
  }, []);

  React.useEffect(() => {
    function handleHashChange() {
      setTab(tabFromLocation());
    }
    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  React.useEffect(() => {
    function handleSessionCleared() {
      setIsAuthed(false);
      setSessionUserId(null);
      setPreloadStatus("idle");
    }
    window.addEventListener("mileday-mobile-session-cleared", handleSessionCleared);
    const handleSessionChanged = () => {
      setIsAuthed(api.hasSession());
      setSessionUserId(api.getUserId());
    };
    window.addEventListener("mileday-mobile-session-changed", handleSessionChanged);
    const stop = api.startSessionMaintenance();
    return () => {
      stop();
      window.removeEventListener("mileday-mobile-session-cleared", handleSessionCleared);
      window.removeEventListener("mileday-mobile-session-changed", handleSessionChanged);
    };
  }, []);

  React.useEffect(() => {
    if (!isAuthed) {
      return;
    }
    let alive = true;
    setPreloadStatus("loading");
    setPreloadError("");
    api.ensureSession().catch((error) => {
      // Cached schedules remain usable during a temporary auth/network outage.
      if (!api.hasSession()) throw error;
    }).then(() => preloadRequiredMonths())
      .then((result) => {
        if (!alive) {
          return;
        }
        if (!result.ok) {
          setPreloadError("이번 달 정보를 가져오지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해주세요.");
          setPreloadStatus("error");
          return;
        }
        setPreloadStatus("ready");
        preloadExtraMonths();
      })
      .catch(() => {
        if (!alive) {
          return;
        }
        setPreloadError("정보를 가져오지 못했습니다. 네트워크 상태를 확인한 뒤 다시 시도해주세요.");
        setPreloadStatus("error");
      });
    return () => {
      alive = false;
    };
  }, [isAuthed, sessionUserId, preloadAttempt]);

  React.useEffect(() => {
    if (!isAuthed || preloadStatus !== "ready") {
      return;
    }
    preloadExtraMonths(parseDateKey(day.today));
  }, [isAuthed, preloadStatus, day]);

  React.useEffect(() => {
    if (isAuthed && preloadStatus === "error") setPreloadAttempt((current) => current + 1);
  }, [day]);

  function navigate(next: Tab) {
    setTab(next);
    history.replaceState(null, "", `/#/${next}`);
  }

  if (!isAuthed) {
    return <Login onLogin={() => setIsAuthed(true)} />;
  }

  if (preloadStatus === "loading") {
    return <PreloadScreen />;
  }

  if (preloadStatus === "error") {
    return (
      <PreloadScreen
        error={preloadError}
        onRetry={() => {
          setPreloadStatus("loading");
          setPreloadAttempt((current) => current + 1);
        }}
      />
    );
  }

  return (
    <main className="app-shell" key={sessionUserId}>
      {tab === "today" ? <Today day={day} /> : null}
      {tab === "calendar" ? <Calendar day={day} /> : null}
      {tab === "settings" ? <SettingsView onLogout={() => setIsAuthed(false)} /> : null}
      <nav className="bottom-nav" aria-label="Primary">
        <button className={tab === "today" ? "active" : ""} onClick={() => navigate("today")}>
          <Sun size={20} />
          <span>오늘</span>
        </button>
        <button className={tab === "calendar" ? "active" : ""} onClick={() => navigate("calendar")}>
          <CalendarDays size={20} />
          <span>캘린더</span>
        </button>
        <button className={tab === "settings" ? "active" : ""} onClick={() => navigate("settings")}>
          <Settings size={20} />
          <span>설정</span>
        </button>
      </nav>
    </main>
  );
}

function PreloadScreen({ error, onRetry }: { error?: string; onRetry?: () => void }) {
  return (
    <main className="loading-shell">
      <section className="loading-panel" aria-live="polite">
        <p className="eyebrow">MileDay</p>
        <h1>정보를 가져오고 있습니다</h1>
        <p>{error || "오늘 일정과 캘린더를 준비하는 중입니다."}</p>
        {error && onRetry ? <button className="primary-button" onClick={onRetry}>다시 시도</button> : <span className="loading-bar" />}
      </section>
    </main>
  );
}

function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.login(email, password);
      onLogin();
    } catch (error) {
      setError(error instanceof Error ? error.message : "로그인할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <form className="login-panel" onSubmit={submit}>
        <div>
          <p className="eyebrow">MileDay</p>
          <h1>오늘 일정을 확인하세요</h1>
        </div>
        <label>
          이메일
          <input value={email} type="email" autoComplete="email" onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          비밀번호
          <input value={password} type="password" autoComplete="current-password" onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button className="primary-button" disabled={loading}>{loading ? "로그인 중" : "로그인"}</button>
      </form>
    </main>
  );
}

function Today({ day }: { day: DayState }) {
  const [today, setToday] = React.useState<CalendarDateData | null>(null);
  const [week, setWeek] = React.useState<CalendarDateData[]>([]);
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");

  React.useEffect(() => {
    let alive = true;
    setLoading(true);
    setError("");
    const weekDates = weekDateKeys(day.today);
    // Show cached days immediately, then replace them with live data if available.
    const cached = weekDates.flatMap((date) => {
      const data = readCachedDate(date);
      return data ? [data] : [];
    });
    setToday(cached.find((data) => data.date === day.today) || null);
    setWeek(cached);
    void Promise.allSettled(weekDates.map((date) => getDateWithCache(date, true)))
      .then((results) => {
        if (!alive) return;
        const days = results.flatMap((result) => result.status === "fulfilled" ? [result.value] : []);
        setToday(days.find((data) => data.date === day.today) || null);
        setWeek(days);
        if (days.length !== 7) setError("일부 일정을 가져오지 못했습니다. 네트워크 상태를 확인해주세요.");
      })
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [day]);

  return (
    <section className="screen">
      <header className="screen-header">
        <p className="eyebrow">Today</p>
        <h1>{displayDate(day.today)}</h1>
      </header>
      {loading ? <p className="status-text">불러오는 중입니다.</p> : null}
      {error ? <p className="error-text">{error}</p> : null}
      <ScheduleSection title="오늘 일정" data={today?.date === day.today ? today : null} />
      <WeekScheduleSection days={week.filter((data) => data.date > day.today)} />
    </section>
  );
}

function Calendar({ day }: { day: DayState }) {
  const [calendar, setCalendar] = React.useState(() => ({ visibleMonth: parseDateKey(day.today), selectedDate: day.today }));
  const { visibleMonth, selectedDate } = calendar;
  const previousToday = React.useRef(day.today);
  const [month, setMonth] = React.useState<CalendarMonthData | null>(null);
  const selected = month?.days.find((day) => day.date === selectedDate) || null;

  React.useEffect(() => {
    const previous = previousToday.current;
    previousToday.current = day.today;
    setCalendar((current) => rollCalendarDay(current, previous, day.today));
  }, [day.today]);

  React.useEffect(() => {
    let alive = true;
    const year = visibleMonth.getFullYear();
    const monthNumber = visibleMonth.getMonth() + 1;
    const cached = readCachedMonth(year, monthNumber);
    if (cached) {
      setMonth(cached);
    } else {
      setMonth(null);
    }
    getMonthWithCache(year, monthNumber).then((data) => { if (alive) setMonth(data); }).catch(() => undefined);
    return () => { alive = false; };
  }, [visibleMonth, day]);

  return (
    <section className="screen">
      <header className="calendar-top">
        <button className="icon-button" onClick={() => setCalendar((current) => ({ ...current, visibleMonth: moveMonth(current.visibleMonth, -1) }))} aria-label="이전 달">
          <ChevronLeft />
        </button>
        <h1>{monthLabel(visibleMonth)}</h1>
        <button className="icon-button" onClick={() => setCalendar((current) => ({ ...current, visibleMonth: moveMonth(current.visibleMonth, 1) }))} aria-label="다음 달">
          <ChevronRight />
        </button>
      </header>
      <div className="weekday-grid">
        {["일", "월", "화", "수", "목", "금", "토"].map((day) => <span key={day}>{day}</span>)}
      </div>
      <div className="month-grid">
        {monthGrid(visibleMonth).map((date) => {
          const key = toDateKey(date);
          const data = month?.days.find((item) => item.date === key);
          return (
            <button
              key={key}
              className={[
                "date-cell",
                key === day.today ? "today" : "",
                key === selectedDate ? "selected" : "",
                !isInMonth(date, visibleMonth) ? "muted" : "",
                data && data.goal_count + data.milestone_count > 0 ? "has-events" : "",
              ].filter(Boolean).join(" ")}
              aria-current={key === day.today ? "date" : undefined}
              aria-pressed={key === selectedDate}
              onClick={() => setCalendar((current) => ({ ...current, selectedDate: key }))}
            >
              <span>{date.getDate()}</span>
              <i />
            </button>
          );
        })}
      </div>
      <ScheduleSection title={displayDate(selectedDate)} data={selected} />
    </section>
  );
}

function SettingsView({ onLogout }: { onLogout: () => void }) {
  const [settings, setSettings] = React.useState<NotificationSettings | null>(null);
  const [message, setMessage] = React.useState("");
  const mutationId = React.useRef(0);

  React.useEffect(() => {
    api.getNotificationSettings().then((data) => setSettings(normalizeNotificationSettings(data)));
  }, []);

  async function updateOptimistically(patch: Partial<NotificationSettings>, fallbackMessage: string) {
    if (!settings) {
      return;
    }
    const currentMutation = mutationId.current + 1;
    mutationId.current = currentMutation;
    const previous = settings;
    setMessage("");
    setSettings(normalizeNotificationSettings({ ...settings, ...patch }));
    try {
      const next = await api.updateNotificationSettings(patch);
      if (mutationId.current === currentMutation) {
        setSettings(normalizeNotificationSettings(next));
      }
    } catch (error) {
      if (mutationId.current === currentMutation) {
        setSettings(previous);
        setMessage(error instanceof Error ? error.message : fallbackMessage);
      }
    }
  }

  async function handleEnablePush() {
    if (!settings) {
      return;
    }
    const currentMutation = mutationId.current + 1;
    mutationId.current = currentMutation;
    const previous = settings;
    setMessage("");
    setSettings(normalizeNotificationSettings({ ...settings, enabled: true }));
    try {
      await enablePush();
      const next = await api.updateNotificationSettings({ enabled: true });
      if (mutationId.current === currentMutation) {
        setSettings(normalizeNotificationSettings(next));
        setMessage("알림이 설정되었습니다.");
      }
    } catch (error) {
      if (mutationId.current === currentMutation) {
        setSettings(previous);
        setMessage(error instanceof Error ? error.message : "알림을 설정할 수 없습니다.");
      }
    }
  }

  async function handleDisablePush() {
    if (!settings) {
      return;
    }
    const currentMutation = mutationId.current + 1;
    mutationId.current = currentMutation;
    const previous = settings;
    setMessage("");
    setSettings(normalizeNotificationSettings({ ...settings, enabled: false }));
    try {
      await disablePush();
      const next = await api.updateNotificationSettings({ enabled: false });
      if (mutationId.current === currentMutation) {
        setSettings(normalizeNotificationSettings(next));
        setMessage("알림이 해제되었습니다.");
      }
    } catch (error) {
      if (mutationId.current === currentMutation) {
        setSettings(previous);
        setMessage(error instanceof Error ? error.message : "알림을 해제할 수 없습니다.");
      }
    }
  }

  async function sendTestNotification() {
    setMessage("");
    try {
      const result = await api.sendTestPush();
      if (result.reason === "no_incomplete_milestones") {
        setMessage("오늘 예정된 미완료 마일스톤이 없습니다.");
      } else if (result.sent === 0) {
        setMessage("알림을 받을 기기가 없습니다. 이 기기에서 알림을 다시 설정해 주세요.");
      } else {
        setMessage("오늘 일정 알림을 다시 보냈습니다.");
      }
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "테스트 알림을 보낼 수 없습니다.");
    }
  }

  async function logout() {
    try {
      await api.logout();
    } catch {
      // Local logout still completes when the server is unreachable.
    } finally {
      clearMonthCache();
      onLogout();
    }
  }

  return (
    <section className="screen">
      <header className="settings-header">
        <div>
          <p className="eyebrow">Settings</p>
          <h1>알림</h1>
        </div>
        <button className="small-secondary-button" onClick={sendTestNotification}>
          <Bell size={16} />
          테스트
        </button>
      </header>
      <div className="settings-list">
        <label className="setting-row">
          <span>오늘 일정 알림</span>
          <input
            type="checkbox"
            checked={settings?.enabled || false}
            disabled={!settings || !isPushSupported()}
            onChange={(event) => {
              if (event.target.checked) {
                void handleEnablePush();
                return;
              }
              void handleDisablePush();
            }}
          />
        </label>
        <label className="setting-row">
          <span>알림 시간</span>
          <input
            type="time"
            value={settings?.notification_time?.slice(0, 5) || "08:00"}
            disabled={!settings}
            onChange={(event) => {
              void updateOptimistically(
                { notification_time: event.target.value },
                "알림 시간을 저장할 수 없습니다.",
              );
            }}
          />
        </label>
      </div>
      {!isPushSupported() ? <p className="status-text">이 디바이스에서는 Web Push 알림을 사용할 수 없습니다.</p> : null}
      {message ? <p className="status-text">{message}</p> : null}
      <button className="logout-button" onClick={logout}>
        <LogOut size={18} />
        로그아웃
      </button>
    </section>
  );
}

function WeekScheduleSection({ days }: { days: CalendarDateData[] }) {
  return (
    <section className="schedule-section compact">
      <h2>이번 7일 일정</h2>
      <div className="week-list">
        {days.map((day) => {
          const items = buildScheduleItems(day.goals, day.milestones);
          return (
            <article className="week-day" key={day.date}>
              <div className="week-day-header">
                <strong>{displayDate(day.date)}</strong>
                <span>{items.length}개</span>
              </div>
              {items.length === 0 ? <p className="empty-state">일정이 없습니다.</p> : null}
              {items.length > 0 ? (
                <div className="schedule-list">
                  {items.map((item) => (
                    <div className="schedule-item" key={item.id}>
                      <span className="color-dot" style={{ background: item.color }} />
                      <div>
                        <strong>{item.title}</strong>
                        <p>{item.meta}</p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : null}
            </article>
          );
        })}
      </div>
    </section>
  );
}

function ScheduleSection({ title, data, compact = false }: { title: string; data: CalendarDateData | null; compact?: boolean }) {
  const items = data ? buildScheduleItems(data.goals, data.milestones) : [];
  return (
    <section className={compact ? "schedule-section compact" : "schedule-section"}>
      <h2>{title}</h2>
      {items.length === 0 ? <p className="empty-state">일정이 없습니다.</p> : null}
      <div className="schedule-list">
        {items.map((item) => (
          <article className="schedule-item" key={item.id}>
            <span className="color-dot" style={{ background: item.color }} />
            <div>
              <strong>{item.title}</strong>
              <p>{item.meta}</p>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

function buildScheduleItems(goals: Goal[], milestones: Milestone[]) {
  return [
    ...goals.map((goal) => ({
      id: `goal-${goal.id}`,
      title: goal.title,
      color: goal.color,
      meta: goal.is_completed ? "목표 완료" : "목표 마감",
    })),
    ...milestones.map((milestone) => ({
      id: `milestone-${milestone.id}`,
      title: milestone.title,
      color: milestone.color,
      meta: milestone.goal_title || "마일스톤",
    })),
  ].sort((a, b) => a.title.localeCompare(b.title, "ko"));
}

function normalizeNotificationSettings(settings: NotificationSettings): NotificationSettings {
  return {
    ...settings,
    notification_time: settings.notification_time?.slice(0, 5) || "08:00",
    timezone: settings.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Seoul",
  };
}

ReactDOM.createRoot(document.getElementById("root") as HTMLElement).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
