import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { Goal } from "@/api/types";
import { ManualCreatePanel } from "./ManualCreatePanel";

const goal = (id: string, deadline: string, completed = false): Goal => ({ id, title: id, deadline, is_completed: completed, is_recurring: false, recurrence_type: null, color: "#7F9278", created_at: "", updated_at: "" });
const props = { selectedDate: "2020-01-01", today: "2026-10-15", language: "ko" as const, isLoading: false, onCreateSchedule: vi.fn().mockResolvedValue(undefined), onClose: vi.fn() };
afterEach(cleanup);

describe("existing goal eligibility", () => {
  it("excludes yesterday, includes today and future even if completed, independently of selected date", () => {
    render(<ManualCreatePanel {...props} goals={[goal("어제", "2026-10-14"), goal("오늘", "2026-10-15", true), goal("미래", "2026-10-16")]} />);
    fireEvent.click(screen.getByRole("button", { name: "기존 목표에 추가" }));
    expect(screen.queryByRole("option", { name: "어제" })).not.toBeInTheDocument();
    expect(screen.getByRole("option", { name: "오늘" })).toBeInTheDocument();
    expect(screen.getByRole("option", { name: "미래" })).toBeInTheDocument();
  });

  it("invalidates selection on expiry/deletion and allows it again after extending the deadline", () => {
    const view = render(<ManualCreatePanel {...props} goals={[goal("목표", "2026-10-15")]} />);
    fireEvent.click(screen.getByRole("button", { name: "기존 목표에 추가" }));
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "목표" } });
    view.rerender(<ManualCreatePanel {...props} goals={[goal("목표", "2026-10-14")]} />);
    expect(screen.getByRole("combobox")).toHaveValue("");
    expect(screen.getByText("추가할 수 있는 목표가 없습니다.")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "일정 추가" })).toBeDisabled();
    view.rerender(<ManualCreatePanel {...props} goals={[goal("목표", "2026-10-17")]} />);
    expect(screen.getByRole("option", { name: "목표" })).toBeInTheDocument();
    fireEvent.change(screen.getByRole("combobox"), { target: { value: "목표" } });
    view.rerender(<ManualCreatePanel {...props} goals={[]} />);
    expect(screen.getByRole("combobox")).toHaveValue("");
    expect(screen.getByRole("button", { name: "일정 추가" })).toBeDisabled();
  });
});
