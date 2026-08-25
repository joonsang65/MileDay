import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { AuthPanel } from "./AuthPanel";

describe("AuthPanel", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("회원가입 전에 온보딩을 마지막 슬라이드까지 보여준다", async () => {
    const user = userEvent.setup();

    render(
      <AuthPanel
        isLoading={false}
        onLogin={vi.fn()}
        onSignup={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "회원가입" }));

    const onboarding = screen.getByRole("region", { name: "MileDay 소개" });
    expect(within(onboarding).getByText("달력에서 흐름 확인")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "로그인" })).toBeInTheDocument();

    await user.click(within(onboarding).getByRole("button", { name: "다음" }));
    await user.click(within(onboarding).getByRole("button", { name: "다음" }));
    await user.click(within(onboarding).getByRole("button", { name: "다음" }));
    await user.click(within(onboarding).getByRole("button", { name: "회원가입 시작" }));

    expect(screen.getByRole("heading", { name: "회원가입" })).toBeInTheDocument();
  });

  it("마지막 슬라이드에서 다시 보지 않기를 누르면 다음부터 바로 회원가입으로 전환한다", async () => {
    const user = userEvent.setup();

    render(
      <AuthPanel
        isLoading={false}
        onLogin={vi.fn()}
        onSignup={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "회원가입" }));
    const onboarding = screen.getByRole("region", { name: "MileDay 소개" });
    await user.click(within(onboarding).getByRole("button", { name: "다음" }));
    await user.click(within(onboarding).getByRole("button", { name: "다음" }));
    await user.click(within(onboarding).getByRole("button", { name: "다음" }));
    await user.click(within(onboarding).getByRole("button", { name: "다시 보지 않기" }));

    expect(localStorage.getItem("mileday.signup_onboarding_dismissed")).toBe("true");
    expect(screen.getByRole("heading", { name: "회원가입" })).toBeInTheDocument();
  });

  it("온보딩을 보지 않기로 한 사용자는 회원가입을 바로 요청할 수 있다", async () => {
    const user = userEvent.setup();
    const onSignup = vi.fn().mockResolvedValue(undefined);
    localStorage.setItem("mileday.signup_onboarding_dismissed", "true");

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

  it("로그인 시 자동 로그인 여부를 함께 전달한다", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn().mockResolvedValue(undefined);

    render(
      <AuthPanel
        isLoading={false}
        onLogin={onLogin}
        onSignup={vi.fn()}
      />,
    );

    await user.click(screen.getByLabelText("자동 로그인"));
    await user.type(screen.getByLabelText("이메일"), "user@example.com");
    await user.type(screen.getByLabelText("비밀번호", { selector: "input" }), "password123");
    await user.click(within(screen.getByLabelText("이메일").closest("form")!).getByRole("button", { name: "로그인" }));

    expect(onLogin).toHaveBeenCalledWith("user@example.com", "password123", false);
  });

  it("비밀번호 확인이 일치하지 않으면 회원가입 API를 호출하지 않는다", async () => {
    const user = userEvent.setup();
    const onSignup = vi.fn();
    localStorage.setItem("mileday.signup_onboarding_dismissed", "true");

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

  it("영어 토글을 누르면 로그인 화면 문구와 외부 에러 메시지를 영어로 표시한다", async () => {
    const user = userEvent.setup();
    const onLanguageChange = vi.fn();

    render(
      <AuthPanel
        isLoading={false}
        language="en"
        errorMessage="Please check your email or password."
        onLanguageChange={onLanguageChange}
        onLogin={vi.fn()}
        onSignup={vi.fn()}
      />,
    );

    expect(screen.getByRole("heading", { name: "Log in" })).toBeInTheDocument();
    expect(screen.getByLabelText("Email")).toBeInTheDocument();
    expect(screen.getByText("Please check your email or password.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "한국어" }));

    expect(onLanguageChange).toHaveBeenCalledWith("ko");
  });

  it("영어 화면에서는 이메일 형식 오류도 앱 내부 영어 메시지로 표시한다", async () => {
    const user = userEvent.setup();
    const onLogin = vi.fn();

    render(
      <AuthPanel
        isLoading={false}
        language="en"
        onLogin={onLogin}
        onSignup={vi.fn()}
      />,
    );

    await user.type(screen.getByLabelText("Email"), "junsang2704a");
    await user.type(screen.getByLabelText("Password", { selector: "input" }), "password123");
    await user.click(within(screen.getByLabelText("Email").closest("form")!).getByRole("button", { name: "Log in" }));

    expect(screen.getByText("Please enter a valid email address.")).toBeInTheDocument();
    expect(onLogin).not.toHaveBeenCalled();
  });
});
