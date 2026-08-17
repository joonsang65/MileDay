import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { CalendarHeader } from "./CalendarHeader";

describe("CalendarHeader", () => {
  it("shows the calendar controls without the quick add button", async () => {
    const user = userEvent.setup();
    const onOpenSettings = vi.fn();

    render(
      <CalendarHeader
        label="2026.07"
        mode="month"
        onModeChange={vi.fn()}
        onPrevious={vi.fn()}
        onNext={vi.fn()}
        onToday={vi.fn()}
        onOpenSettings={onOpenSettings}
        language="en"
      />,
    );

    await user.click(screen.getByTitle("Settings"));

    expect(onOpenSettings).toHaveBeenCalledTimes(1);
    expect(screen.queryByTestId("quick-add-button")).not.toBeInTheDocument();
  });
});
