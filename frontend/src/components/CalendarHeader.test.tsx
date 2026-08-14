import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CalendarHeader } from "./CalendarHeader";

describe("CalendarHeader", () => {
  it("설정과 일정 만들기 액션을 제공한다", async () => {
    const user = userEvent.setup();
    const onOpenSettings = vi.fn();
    const onOpenQuickMenu = vi.fn();

    render(
      <CalendarHeader
        label="2026.07"
        mode="month"
        onModeChange={vi.fn()}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
        onToday={vi.fn()}
        onOpenSettings={onOpenSettings}
        onOpenQuickMenu={onOpenQuickMenu}
        language="ko"
      />,
    );

    expect(screen.queryByTitle("로그아웃")).not.toBeInTheDocument();

    await user.click(screen.getByTitle("설정"));
    await user.click(screen.getByTitle("일정 만들기"));

    expect(onOpenSettings).toHaveBeenCalledTimes(1);
    expect(onOpenQuickMenu).toHaveBeenCalledTimes(1);
  });
});
