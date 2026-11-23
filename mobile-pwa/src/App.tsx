import React from "react";
import { CalendarDays, Settings, Sun } from "lucide-react";

import { api } from "./api";
import { parseDateKey, todayKey, watchDay } from "./date";
import type { DayState } from "./date";
import { preloadExtraMonths, preloadRequiredMonths } from "./month-cache";
import { registerServiceWorker } from "./push";
import { Calendar } from "./screens/Calendar";
import { Login } from "./screens/Login";
import { SettingsView } from "./screens/SettingsView";
import { Today } from "./screens/Today";

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

export function App() {
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
