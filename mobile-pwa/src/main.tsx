import React from "react";
import ReactDOM from "react-dom/client";
import { Bell, CalendarDays, ChevronLeft, ChevronRight, LogOut, Settings, Sun } from "lucide-react";

import { api } from "./api";
import { displayDate, isInMonth, monthGrid, monthLabel, moveMonth, parseDateKey, todayKey, toDateKey } from "./date";
import { disablePush, enablePush, isPushSupported, permissionLabel, registerServiceWorker } from "./push";
import type { CalendarDateData, CalendarMonthData, Goal, Milestone, NotificationSettings } from "./types";
import "./styles.css";

type Tab = "today" | "calendar" | "settings";

function App() {
  const [isAuthed, setIsAuthed] = React.useState(api.hasSession());
  const [tab, setTab] = React.useState<Tab>(location.pathname.includes("calendar") ? "calendar" : location.pathname.includes("settings") ? "settings" : "today");

  React.useEffect(() => {
    void registerServiceWorker();
  }, []);

  React.useEffect(() => {
    function handleSessionCleared() {
      setIsAuthed(false);
    }
    window.addEventListener("mileday-mobile-session-cleared", handleSessionCleared);
    return () => window.removeEventListener("mileday-mobile-session-cleared", handleSessionCleared);
  }, []);

  function navigate(next: Tab) {
    setTab(next);
    history.replaceState(null, "", next === "today" ? "/today" : `/${next}`);
  }

  if (!isAuthed) {
    return <Login onLogin={() => setIsAuthed(true)} />;
  }

  return (
    <main className="app-shell">
      {tab === "today" ? <Today /> : null}
      {tab === "calendar" ? <Calendar /> : null}
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

function Today() {
  const [today, setToday] = React.useState<CalendarDateData | null>(null);
  const [tomorrow, setTomorrow] = React.useState<CalendarDateData | null>(null);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    const now = new Date();
    const next = new Date(now);
    next.setDate(now.getDate() + 1);
    Promise.all([api.getToday(toDateKey(now)), api.getToday(toDateKey(next))])
      .then(([todayData, tomorrowData]) => {
        setToday(todayData);
        setTomorrow(tomorrowData);
      })
      .finally(() => setLoading(false));
  }, []);

  return (
    <section className="screen">
      <header className="screen-header">
        <p className="eyebrow">Today</p>
        <h1>{displayDate(todayKey())}</h1>
      </header>
      {loading ? <p className="status-text">불러오는 중입니다.</p> : null}
      <ScheduleSection title="오늘 일정" data={today} />
      <ScheduleSection title="내일 일정" data={tomorrow} compact />
    </section>
  );
}

function Calendar() {
  const [visibleMonth, setVisibleMonth] = React.useState(new Date());
  const [selectedDate, setSelectedDate] = React.useState(todayKey());
  const [month, setMonth] = React.useState<CalendarMonthData | null>(null);
  const selected = month?.days.find((day) => day.date === selectedDate) || null;

  React.useEffect(() => {
    api.getMonth(visibleMonth.getFullYear(), visibleMonth.getMonth() + 1).then(setMonth);
  }, [visibleMonth]);

  return (
    <section className="screen">
      <header className="calendar-top">
        <button className="icon-button" onClick={() => setVisibleMonth((current) => moveMonth(current, -1))} aria-label="이전 달">
          <ChevronLeft />
        </button>
        <h1>{monthLabel(visibleMonth)}</h1>
        <button className="icon-button" onClick={() => setVisibleMonth((current) => moveMonth(current, 1))} aria-label="다음 달">
          <ChevronRight />
        </button>
      </header>
      <div className="weekday-grid">
        {["일", "월", "화", "수", "목", "금", "토"].map((day) => <span key={day}>{day}</span>)}
      </div>
      <div className="month-grid">
        {monthGrid(visibleMonth).map((date) => {
          const key = toDateKey(date);
          const day = month?.days.find((item) => item.date === key);
          return (
            <button
              key={key}
              className={[
                "date-cell",
                key === selectedDate ? "selected" : "",
                !isInMonth(date, visibleMonth) ? "muted" : "",
                day && day.goal_count + day.milestone_count > 0 ? "has-events" : "",
              ].filter(Boolean).join(" ")}
              onClick={() => setSelectedDate(key)}
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
  const [permission, setPermission] = React.useState(permissionLabel());
  const [message, setMessage] = React.useState("");

  React.useEffect(() => {
    api.getNotificationSettings().then((data) => setSettings(normalizeNotificationSettings(data)));
  }, []);

  async function update(patch: Partial<NotificationSettings>) {
    const next = await api.updateNotificationSettings(patch);
    setSettings(normalizeNotificationSettings(next));
  }

  async function handleEnablePush() {
    setMessage("");
    try {
      await enablePush();
      setPermission(permissionLabel());
      await update({ enabled: true });
      setMessage("알림이 설정되었습니다.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "알림을 설정할 수 없습니다.");
    }
  }

  async function logout() {
    await api.logout();
    onLogout();
  }

  return (
    <section className="screen">
      <header className="screen-header">
        <p className="eyebrow">Settings</p>
        <h1>알림</h1>
      </header>
      <div className="settings-list">
        <label className="setting-row">
          <span>매일 일정 알림</span>
          <input
            type="checkbox"
            checked={settings?.enabled || false}
            onChange={(event) => {
              if (event.target.checked) {
                void handleEnablePush();
                return;
              }
              void disablePush().then(() => update({ enabled: false }));
            }}
          />
        </label>
        <label className="setting-row">
          <span>알림 시간</span>
          <input
            type="time"
            value={settings?.notification_time?.slice(0, 5) || "08:00"}
            onChange={(event) => update({ notification_time: event.target.value })}
          />
        </label>
        <div className="setting-row">
          <span>권한 상태</span>
          <strong>{permission}</strong>
        </div>
      </div>
      <button className="primary-button" disabled={!isPushSupported()} onClick={handleEnablePush}>
        <Bell size={18} />
        알림 허용하기
      </button>
      <button className="secondary-button" onClick={() => disablePush().then(() => update({ enabled: false }))}>알림 해제</button>
      <button className="secondary-button" onClick={() => api.sendTestPush().then(() => setMessage("테스트 알림을 보냈습니다."))}>테스트 알림</button>
      {message ? <p className="status-text">{message}</p> : null}
      <button className="logout-button" onClick={logout}>
        <LogOut size={18} />
        로그아웃
      </button>
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
