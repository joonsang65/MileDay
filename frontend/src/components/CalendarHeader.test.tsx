import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CalendarHeader } from "./CalendarHeader";

describe("CalendarHeader", () => {
  it("로그아웃 버튼 대신 설정 버튼을 제공한다", async () => {
    const user = userEvent.setup();
    const onOpenSettings = vi.fn();
    render(
      <CalendarHeader
        label="2026.07"
        mode="month"
        isLoading={false}
        onModeChange={vi.fn()}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
        onToday={vi.fn()}
        onRefresh={vi.fn()}
        onOpenSettings={onOpenSettings}
        language="ko"
      />,
    );

    expect(screen.queryByTitle("로그아웃")).not.toBeInTheDocument();
    await user.click(screen.getByTitle("설정"));

    expect(onOpenSettings).toHaveBeenCalledTimes(1);
  });
});
