import React from "react";
import { Bell, LogOut } from "lucide-react";

import { api } from "../api";
import { clearMonthCache } from "../month-cache";
import { disablePush, enablePush, isPushSupported } from "../push";
import type { NotificationSettings } from "../types";

export function SettingsView({ onLogout }: { onLogout: () => void }) {
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
      } else if (result.sent > 0) {
        setMessage("오늘 일정 알림을 푸시 서버에 전송했습니다. 휴대폰 알림 표시까지 잠시 걸릴 수 있습니다.");
      } else if (result.sent === 0) {
        setMessage("알림을 받을 기기가 없습니다. 이 기기에서 알림을 다시 설정해 주세요.");
      } else {
        setMessage("알림 전송 결과를 확인할 수 없습니다. 잠시 후 다시 시도해 주세요.");
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

function normalizeNotificationSettings(settings: NotificationSettings): NotificationSettings {
  return {
    ...settings,
    notification_time: settings.notification_time?.slice(0, 5) || "08:00",
    timezone: settings.timezone || Intl.DateTimeFormat().resolvedOptions().timeZone || "Asia/Seoul",
  };
}
