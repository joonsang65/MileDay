import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { AiScheduleDraft } from "@/api/types";

import { AiSchedulePanel } from "./AiSchedulePanel";

const draft: AiScheduleDraft = {
  goal: {
    title: "데이터 분석 과제",
    deadline: "2026-09-30",
  },
  milestones: [
    {
      client_id: "draft-1",
      title: "자료 정리",
      scheduled_date: "2026-09-10",
      selected: true,
    },
  ],
  planning_preference: {
    intensity: "balanced",
    preferred_days: ["saturday"],
  },
  validation: {
    is_valid: true,
    failure_codes: [],
    warnings: [],
  },
  create_goal_payload: {
    goal: {
      title: "데이터 분석 과제",
      deadline: "2026-09-30",
      is_recurring: false,
      recurrence_type: null,
      color: "#7F9278",
    },
    milestones: [],
    write_policy: "user_confirmation_required",
  },
};

function renderPanel(overrides: Partial<Parameters<typeof AiSchedulePanel>[0]> = {}) {
  const props: Parameters<typeof AiSchedulePanel>[0] = {
    selectedDate: "2026-09-01",
    today: "2026-09-01",
    timezone: "Asia/Seoul",
    availability: [{ date: "2026-09-10", available_minutes: 120 }],
    geminiDataConsent: false,
    isSaving: false,
    onCreateDraft: vi.fn().mockResolvedValue(draft),
    onSaveDraft: vi.fn().mockResolvedValue(undefined),
    onGeminiDataConsentChange: vi.fn().mockResolvedValue(undefined),
    onClose: vi.fn(),
    language: "ko",
    ...overrides,
  };
  render(<AiSchedulePanel {...props} />);
  return props;
}

describe("AiSchedulePanel", () => {
  it("shows Gemini consent help and saves consent from the AI suggestion input", async () => {
    const user = userEvent.setup();
    const onGeminiDataConsentChange = vi.fn().mockResolvedValue(undefined);
    renderPanel({ onGeminiDataConsentChange });

    await user.click(screen.getByRole("button", { name: "동의가 필요한 이유와 전송 내용" }));
    expect(screen.getByText("왜 동의가 필요한가요?")).toBeInTheDocument();
    expect(screen.getByText(/전송 내용: 목표 설명/)).toBeInTheDocument();

    await user.click(screen.getByLabelText("Gemini 전송 동의"));
    expect(onGeminiDataConsentChange).toHaveBeenCalledWith(true);
  });

  it("blocks draft creation until Gemini consent is enabled", async () => {
    const user = userEvent.setup();
    const onCreateDraft = vi.fn().mockResolvedValue(draft);
    renderPanel({ onCreateDraft, geminiDataConsent: false });

    await user.type(screen.getByPlaceholderText(/데이터 분석 과제/), "이직 준비 계획 잡아줘");
    await user.click(screen.getByRole("button", { name: "제안 만들기" }));

    expect(await screen.findByText("Gemini 전송 동의가 필요합니다.")).toBeInTheDocument();
    expect(onCreateDraft).not.toHaveBeenCalled();
  });

  it("creates a draft when consent and prompt are present", async () => {
    const user = userEvent.setup();
    const onCreateDraft = vi.fn().mockResolvedValue(draft);
    renderPanel({ onCreateDraft, geminiDataConsent: true });

    await user.type(screen.getByPlaceholderText(/데이터 분석 과제/), "이직 준비 계획 잡아줘");
    await user.click(screen.getByRole("button", { name: "제안 만들기" }));

    await waitFor(() => expect(onCreateDraft).toHaveBeenCalledTimes(1));
    expect(onCreateDraft).toHaveBeenCalledWith({
      prompt: "이직 준비 계획 잡아줘",
      today: "2026-09-01",
      timezone: "Asia/Seoul",
      availability: [{ date: "2026-09-10", available_minutes: 120 }],
    });
  });
});
