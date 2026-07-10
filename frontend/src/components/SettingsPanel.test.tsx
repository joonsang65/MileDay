import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { UserSettings } from "@/api/types";

import { SettingsPanel } from "./SettingsPanel";

const settings: UserSettings = {
  calendar_view: "month",
  theme: "system",
  accent_color: "#4F46E5",
  font_family: "system",
  font_size: 14,
  ai_suggestion: false,
  holiday_display: "normal",
  week_starts_on: 1,
  completed_milestones: true,
  default_goal_color: "#4F46E5",
  default_milestone_color: "#F97316",
  language: "ko",
  timezone: "Asia/Seoul",
};

describe("SettingsPanel", () => {
  it("설정 저장 payload를 전달하고 하단 로그아웃 버튼을 제공한다", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue(undefined);
    const onLogout = vi.fn();
    const autoLaunch = {
      get: vi.fn().mockResolvedValue({ openAtLogin: false }),
      set: vi.fn().mockResolvedValue({ openAtLogin: true }),
    };
    render(
      <SettingsPanel
        settings={settings}
        isLoading={false}
        autoLaunch={autoLaunch}
        onSave={onSave}
        onClose={vi.fn()}
        onLogout={onLogout}
      />,
    );

    await user.selectOptions(screen.getByLabelText("기본 캘린더"), "week");
    await user.selectOptions(screen.getByLabelText("휴일 표현"), "weekend_like");
    await user.selectOptions(screen.getByLabelText("주 시작 요일"), "0");
    await user.selectOptions(screen.getByLabelText("언어"), "en");
    await user.click(screen.getByLabelText("Open at Windows login"));
    await user.click(screen.getByRole("button", { name: "Save" }));

    expect(autoLaunch.get).toHaveBeenCalledTimes(1);
    expect(autoLaunch.set).toHaveBeenCalledWith(true);
    expect(onSave).toHaveBeenCalledWith({
      calendar_view: "week",
      holiday_display: "weekend_like",
      week_starts_on: 0,
      language: "en",
    });

    const panel = screen.getByRole("region", { name: "Settings" });
    await user.click(within(panel).getByRole("button", { name: "Log out" }));
    expect(onLogout).toHaveBeenCalledTimes(1);
  });
});
