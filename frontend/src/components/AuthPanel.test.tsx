import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { AuthPanel } from "./AuthPanel";

describe("AuthPanel", () => {
  it("회원가입 모드로 전환하고 입력값이 유효하면 회원가입을 요청한다", async () => {
    const user = userEvent.setup();
    const onSignup = vi.fn().mockResolvedValue(undefined);

    render(
      <AuthPanel
        isLoading={false}
        onLogin={vi.fn()}
        onSignup={onSignup}
      />,
    );

    await user.click(screen.getByRole("button", { name: "회원가입" }));
    await user.type(screen.getByLabelText("이메일"), "user@example.com");
    await user.type(screen.getByLabelText("비밀번호", { selector: "input" }), "password123");
    await user.type(screen.getByLabelText("비밀번호 확인"), "password123");
    await user.click(screen.getAllByRole("button", { name: "회원가입" }).at(-1)!);

    expect(onSignup).toHaveBeenCalledWith("user@example.com", "password123");
    expect(screen.getByRole("heading", { name: "로그인" })).toBeInTheDocument();
  });

  it("비밀번호 확인이 일치하지 않으면 회원가입 API를 호출하지 않는다", async () => {
    const user = userEvent.setup();
    const onSignup = vi.fn();

    render(
      <AuthPanel
        isLoading={false}
        onLogin={vi.fn()}
        onSignup={onSignup}
      />,
    );

    await user.click(screen.getByRole("button", { name: "회원가입" }));
    await user.type(screen.getByLabelText("이메일"), "user@example.com");
    await user.type(screen.getByLabelText("비밀번호", { selector: "input" }), "password123");
    await user.type(screen.getByLabelText("비밀번호 확인"), "password456");
    await user.click(screen.getAllByRole("button", { name: "회원가입" }).at(-1)!);

    expect(onSignup).not.toHaveBeenCalled();
    expect(screen.getByText("비밀번호 확인이 일치하지 않습니다.")).toBeInTheDocument();
  });

  it("로딩 중에는 입력과 제출을 비활성화한다", () => {
    render(
      <AuthPanel
        isLoading
        onLogin={vi.fn()}
        onSignup={vi.fn()}
      />,
    );

    expect(screen.getByLabelText("이메일")).toBeDisabled();
    expect(screen.getByLabelText("비밀번호", { selector: "input" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "처리 중" })).toBeDisabled();
  });
});
