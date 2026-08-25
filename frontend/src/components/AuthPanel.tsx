import { FormEvent, useState } from "react";
import { CalendarPlus, CheckSquare, ChevronLeft, ChevronRight, ListTodo, LogIn, Plus, Sparkles, UserPlus } from "lucide-react";

import { AUTH_LANGUAGE_KEY, ONBOARDING_DISMISSED_KEY } from "@/config/storageKeys";
import type { AuthLanguage } from "@/types/auth";
import { getInitialAuthLanguage } from "@/utils/authLanguage";

type AuthPanelProps = {
  isLoading: boolean;
  errorMessage?: string | null;
  noticeMessage?: string | null;
  language?: AuthLanguage;
  onLanguageChange?: (language: AuthLanguage) => void;
  onLogin: (email: string, password: string, rememberLogin: boolean) => Promise<void>;
  onSignup: (email: string, password: string) => Promise<void>;
};

type AuthMode = "login" | "signup";

type OnboardingSlide = {
  title: string;
  description: string;
  points: string[];
  icon: "goal" | "milestone" | "day" | "quick";
};

const authText = {
  ko: {
    appDescription: "매일의 목표와 할 일을 달력 위에서 가볍게 정리하는 위젯입니다.",
    pocNotice: "POC 테스트 환경에서는 서버가 가동되는 데 약 1분 정도 걸릴 수 있습니다.",
    login: "로그인",
    signup: "회원가입",
    authMode: "인증 방식",
    email: "이메일",
    password: "비밀번호",
    passwordConfirm: "비밀번호 확인",
    rememberLogin: "자동 로그인",
    rememberLoginHint: "다음 실행부터 로그인 없이 바로 시작합니다.",
    processing: "처리 중",
    languageLabel: "언어",
    introLabel: "MileDay 소개",
    previous: "이전",
    next: "다음",
    startSignup: "회원가입 시작",
    dismissOnboarding: "다시 보지 않기",
    validation: {
      emailRequired: "이메일을 입력해 주세요.",
      emailInvalid: "이메일 형식을 확인해 주세요.",
      passwordRequired: "비밀번호를 입력해 주세요.",
      passwordTooShort: "비밀번호는 8자 이상이어야 합니다.",
      passwordMismatch: "비밀번호 확인이 일치하지 않습니다.",
    },
    onboardingSlides: [
      {
        title: "달력에서 흐름 확인",
        description: "목표와 작업 일정을 달력에서 가볍게 확인하고, 필요한 날짜만 열어 자세히 봅니다.",
        points: [
          "날짜별 목표와 작업 수를 빠르게 확인합니다.",
          "공휴일과 일정을 함께 확인합니다.",
          "날짜를 누르면 하루보기 패널에서 세부 내용을 확인합니다.",
        ],
        icon: "goal",
      },
      {
        title: "목표와 작업 나누기",
        description: "큰 목표는 마감일과 색상으로 구분하고, 필요한 경우 세부 작업을 날짜별로 나눕니다.",
        points: [
          "목표 제목과 마감일을 먼저 설정합니다.",
          "작업은 필요한 만큼 추가합니다.",
          "단순 일정은 목표만으로도 등록할 수 있습니다.",
        ],
        icon: "milestone",
      },
      {
        title: "하루보기에서 집중 관리",
        description: "선택한 날짜의 목표와 작업을 플로팅 패널에서 컴팩트하게 확인하고 수정합니다.",
        points: [
          "목표와 작업을 한 화면에서 확인합니다.",
          "완료 체크와 수정 작업을 처리합니다.",
          "일정이 없을 때는 빈 상태를 중앙에 표시합니다.",
        ],
        icon: "day",
      },
      {
        title: "빠르게 추가하고 전체 목표 확인",
        description: "하루보기의 + 버튼에서 일정 추가, 일정 추천, 전체 목표를 바로 열 수 있습니다.",
        points: [
          "일정 추가로 목표와 작업을 직접 등록합니다.",
          "일정 추천으로 필요한 일정을 빠르게 만들 수 있습니다.",
          "전체 목표에서 진행 중, 완료, 전체 목표를 한 번에 확인합니다.",
        ],
        icon: "quick",
      },
    ] satisfies OnboardingSlide[],
    visual: {
      weekdays: ["월", "화", "수"],
      mainGoalProgress: "프로젝트 준비 2/4",
      holiday: "공휴일",
      taskProgress: "자료 정리 0/1",
      createTitle: "일정 추가",
      goalTitle: "목표 제목",
      goalExample: "프로젝트 완료",
      deadline: "마감일",
      milestoneExample: "자료 조사",
      dayView: "하루 보기",
      goalCount: "목표 1",
      taskCount: "작업 0/1",
      quickTitle: "빠른 추가",
      manualCreate: "일정 추가",
      manualHint: "직접 일정 만들기",
      aiCreate: "일정 추천",
      aiHint: "AI에게 제안받기",
      allGoals: "전체 목표",
      allGoalsHint: "전체 목표 관리하기",
      ongoing: "진행중",
      completed: "완료",
      all: "전체",
    },
  },
  en: {
    appDescription: "A lightweight desktop widget for organizing daily goals and tasks on a calendar.",
    pocNotice: "In the POC test environment, the server may take about 1 minute to start.",
    login: "Log in",
    signup: "Sign up",
    authMode: "Authentication mode",
    email: "Email",
    password: "Password",
    passwordConfirm: "Confirm password",
    rememberLogin: "Auto login",
    rememberLoginHint: "Start without logging in again from the next launch.",
    processing: "Processing",
    languageLabel: "Language",
    introLabel: "MileDay intro",
    previous: "Previous",
    next: "Next",
    startSignup: "Start sign up",
    dismissOnboarding: "Do not show again",
    validation: {
      emailRequired: "Please enter your email.",
      emailInvalid: "Please enter a valid email address.",
      passwordRequired: "Please enter your password.",
      passwordTooShort: "Password must be at least 8 characters.",
      passwordMismatch: "Password confirmation does not match.",
    },
    onboardingSlides: [
      {
        title: "Check the Calendar Flow",
        description: "Lightly scan goals and tasks on the calendar, then open only the dates that need detail.",
        points: [
          "Quickly check goal and task counts by date.",
          "View holidays and schedules together.",
          "Open the day view panel from a selected date.",
        ],
        icon: "goal",
      },
      {
        title: "Split Goals and Tasks",
        description: "Use deadlines and colors for larger goals, then split them into dated tasks when needed.",
        points: [
          "Set the goal title and deadline first.",
          "Add as many tasks as you need.",
          "Register simple schedules as goals only.",
        ],
        icon: "milestone",
      },
      {
        title: "Focus in Day View",
        description: "Use the floating day view panel to compactly review and edit the selected date.",
        points: [
          "Review goals and tasks in one panel.",
          "Handle completion and edits in place.",
          "Show a centered empty state when nothing is scheduled.",
        ],
        icon: "day",
      },
      {
        title: "Add Quickly and Review All Goals",
        description: "Use the + button in day view to open add schedule, AI suggestion, or all goals.",
        points: [
          "Create goals and tasks directly with Add Schedule.",
          "Generate schedules faster with AI Suggestion.",
          "Review ongoing, completed, and all goals together.",
        ],
        icon: "quick",
      },
    ] satisfies OnboardingSlide[],
    visual: {
      weekdays: ["Mon", "Tue", "Wed"],
      mainGoalProgress: "Project prep 2/4",
      holiday: "Holiday",
      taskProgress: "Organize notes 0/1",
      createTitle: "Add Schedule",
      goalTitle: "Goal title",
      goalExample: "Complete project",
      deadline: "Deadline",
      milestoneExample: "Research",
      dayView: "Day View",
      goalCount: "Goal 1",
      taskCount: "Task 0/1",
      quickTitle: "Quick Add",
      manualCreate: "Add Schedule",
      manualHint: "Create manually",
      aiCreate: "AI Suggestion",
      aiHint: "Get an AI suggestion",
      allGoals: "All Goals",
      allGoalsHint: "Manage all goals",
      ongoing: "Ongoing",
      completed: "Done",
      all: "All",
    },
  },
};

export function AuthPanel({
  isLoading,
  errorMessage,
  noticeMessage,
  language,
  onLanguageChange,
  onLogin,
  onSignup,
}: AuthPanelProps) {
  const [localLanguage, setLocalLanguage] = useState<AuthLanguage>(() => getInitialAuthLanguage());
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [rememberLogin, setRememberLogin] = useState(true);
  const [validationMessage, setValidationMessage] = useState<string | null>(null);
  const [isOnboardingOpen, setIsOnboardingOpen] = useState(false);
  const [activeSlideIndex, setActiveSlideIndex] = useState(0);
  const selectedLanguage = language ?? localLanguage;
  const text = authText[selectedLanguage];
  const onboardingSlides = text.onboardingSlides;
  const activeSlide = onboardingSlides[activeSlideIndex];
  const isLastSlide = activeSlideIndex === onboardingSlides.length - 1;

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);

    const trimmedEmail = email.trim();
    if (!trimmedEmail) {
      setValidationMessage(text.validation.emailRequired);
      return;
    }
    if (!isValidEmail(trimmedEmail)) {
      setValidationMessage(text.validation.emailInvalid);
      return;
    }
    if (!password) {
      setValidationMessage(text.validation.passwordRequired);
      return;
    }

    if (mode === "signup") {
      if (password.length < 8) {
        setValidationMessage(text.validation.passwordTooShort);
        return;
      }
      if (password !== passwordConfirm) {
        setValidationMessage(text.validation.passwordMismatch);
        return;
      }
      await onSignup(trimmedEmail, password);
      switchMode("login");
      return;
    }

    await onLogin(trimmedEmail, password, rememberLogin);
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setPassword("");
    setPasswordConfirm("");
    setValidationMessage(null);
  }

  function handleSignupTabClick() {
    if (mode === "signup") {
      return;
    }
    if (isSignupOnboardingDismissed()) {
      switchMode("signup");
      return;
    }
    setActiveSlideIndex(0);
    setIsOnboardingOpen(true);
  }

  function startSignup() {
    setIsOnboardingOpen(false);
    switchMode("signup");
  }

  function dismissAndStartSignup() {
    localStorage.setItem(ONBOARDING_DISMISSED_KEY, "true");
    startSignup();
  }

  function handleLanguageChange(nextLanguage: AuthLanguage) {
    setLocalLanguage(nextLanguage);
    localStorage.setItem(AUTH_LANGUAGE_KEY, nextLanguage);
    onLanguageChange?.(nextLanguage);
    setValidationMessage(null);
  }

  return (
    <main className="auth-shell">
      <div className="auth-language-toggle" role="group" aria-label={text.languageLabel}>
        <button
          type="button"
          className={selectedLanguage === "ko" ? "active" : ""}
          onClick={() => handleLanguageChange("ko")}
        >
          한국어
        </button>
        <button
          type="button"
          className={selectedLanguage === "en" ? "active" : ""}
          onClick={() => handleLanguageChange("en")}
        >
          English
        </button>
      </div>
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="brand-mark">MileDay</div>
        <p className="auth-description">{text.appDescription}</p>
        <p className="auth-poc-notice">{text.pocNotice}</p>
        <div className="auth-heading">
          <h1 id="auth-title">{mode === "login" ? text.login : text.signup}</h1>
          <div className="auth-tabs" role="group" aria-label={text.authMode}>
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              onClick={() => switchMode("login")}
            >
              {text.login}
            </button>
            <button
              type="button"
              className={mode === "signup" ? "active" : ""}
              onClick={handleSignupTabClick}
            >
              {text.signup}
            </button>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="auth-form" noValidate>
          <label>
            {text.email}
            <input
              type="email"
              autoComplete="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              disabled={isLoading}
              required
            />
          </label>
          <label>
            {text.password}
            <input
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              disabled={isLoading}
              required
            />
          </label>
          {mode === "signup" ? (
            <label>
              {text.passwordConfirm}
              <input
                type="password"
                autoComplete="new-password"
                value={passwordConfirm}
                onChange={(event) => setPasswordConfirm(event.target.value)}
                disabled={isLoading}
                required
              />
            </label>
          ) : (
            <label className="auth-remember">
              <input
                type="checkbox"
                aria-label={text.rememberLogin}
                checked={rememberLogin}
                onChange={(event) => setRememberLogin(event.target.checked)}
                disabled={isLoading}
              />
              <span>
                <strong>{text.rememberLogin}</strong>
                <small>{text.rememberLoginHint}</small>
              </span>
            </label>
          )}
          {noticeMessage ? <p className="notice-text">{noticeMessage}</p> : null}
          {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
          {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
          <button type="submit" className="primary-button" disabled={isLoading}>
            {mode === "login" ? (
              <LogIn size={18} aria-hidden="true" />
            ) : (
              <UserPlus size={18} aria-hidden="true" />
            )}
            {isLoading ? text.processing : mode === "login" ? text.login : text.signup}
          </button>
        </form>
      </section>
      <footer className="app-credit auth-credit" aria-label="App credit">
        <strong>mileday</strong>
        <span>
          made by 노준상 ·{" "}
          <a href="https://github.com/joonsang65/MileDay" target="_blank" rel="noreferrer">
            joonsang65/MileDay
          </a>
        </span>
      </footer>
      {isOnboardingOpen ? (
        <section className="onboarding-panel" aria-label={text.introLabel}>
          <div className="onboarding-visual" data-variant={activeSlide.icon}>
            <span className="onboarding-step">
              {activeSlideIndex + 1} / {onboardingSlides.length}
            </span>
            <OnboardingVisual type={activeSlide.icon} text={text.visual} />
            <div className="onboarding-dots" aria-hidden="true">
              {onboardingSlides.map((slide) => (
                <span key={slide.title} className={slide === activeSlide ? "active" : ""} />
              ))}
            </div>
          </div>
          <div className="onboarding-copy">
            <h2>{activeSlide.title}</h2>
            <p>{activeSlide.description}</p>
            <ul className="onboarding-points">
              {activeSlide.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
          <div className="onboarding-actions">
            <button
              type="button"
              className="ghost-button"
              onClick={() => setActiveSlideIndex((current) => Math.max(0, current - 1))}
              disabled={activeSlideIndex === 0}
            >
              <ChevronLeft size={16} aria-hidden="true" />
              {text.previous}
            </button>
            {isLastSlide ? (
              <>
                <button type="button" className="ghost-button" onClick={startSignup}>
                  {text.startSignup}
                </button>
                <button type="button" className="primary-button" onClick={dismissAndStartSignup}>
                  {text.dismissOnboarding}
                </button>
              </>
            ) : (
              <button
                type="button"
                className="primary-button"
                onClick={() => setActiveSlideIndex((current) => Math.min(onboardingSlides.length - 1, current + 1))}
              >
                {text.next}
                <ChevronRight size={16} aria-hidden="true" />
              </button>
            )}
          </div>
        </section>
      ) : null}
    </main>
  );
}

function isSignupOnboardingDismissed() {
  return localStorage.getItem(ONBOARDING_DISMISSED_KEY) === "true";
}

function isValidEmail(value: string) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value);
}

function OnboardingVisual({
  type,
  text,
}: {
  type: OnboardingSlide["icon"];
  text: (typeof authText)[AuthLanguage]["visual"];
}) {
  if (type === "goal") {
    return (
      <div className="visual-calendar-grid">
        <div className="visual-weekdays">
          {text.weekdays.map((weekday) => (
            <span key={weekday}>{weekday}</span>
          ))}
        </div>
        <div className="visual-days">
          <div className="visual-day-cell muted"><span>13</span></div>
          <div className="visual-day-cell selected">
            <span>14</span>
            <strong>{text.mainGoalProgress}</strong>
            <i />
          </div>
          <div className="visual-day-cell holiday">
            <span>15</span>
            <em>{text.holiday}</em>
            <strong>{text.taskProgress}</strong>
            <i />
          </div>
        </div>
      </div>
    );
  }

  if (type === "milestone") {
    return (
      <div className="visual-create-panel">
        <div className="visual-panel-header">
          <strong>{text.createTitle}</strong>
        </div>
        <div className="visual-manual-goal-row">
          <div className="visual-manual-fields">
            <label>
              <span>{text.goalExample}</span>
            </label>
            <label>
              <span>2026-08-30</span>
            </label>
          </div>
          <div className="visual-color-field" aria-hidden="true">
            <i style={{ background: "#7F9278" }} />
            <i style={{ background: "#55A873" }} />
            <i style={{ background: "#E59A45" }} />
            <i style={{ background: "#8B6FD6" }} />
            <i style={{ background: "#D96868" }} />
            <i style={{ background: "#8A94A3" }} />
          </div>
        </div>
        <div className="visual-milestone-row">
          <span>{text.milestoneExample}</span>
          <span>08-20</span>
        </div>
      </div>
    );
  }

  if (type === "day") {
    return (
      <div className="visual-day-panel">
        <div className="visual-panel-header">
          <strong>{text.dayView}</strong>
          <span className="visual-date-pill">2026-08-15</span>
        </div>
        <div className="visual-day-toolbar">
          <strong>{text.goalCount.split(" ")[0]}</strong>
          <span>{text.goalCount} | {text.taskCount}</span>
          <i><Plus size={14} aria-hidden="true" /></i>
        </div>
        <div className="visual-goal-row">
          <i aria-hidden="true" />
          <div>
            <strong>{text.goalExample}</strong>
            <span>{text.taskCount}</span>
          </div>
        </div>
        <div className="visual-task-row">
          <CheckSquare size={16} aria-hidden="true" />
          <span>{text.milestoneExample}</span>
          <small>08-20</small>
        </div>
      </div>
    );
  }

  return (
    <div className="visual-quick-panel">
      <div className="visual-panel-header">
        <strong>{text.quickTitle}</strong>
      </div>
      <div className="visual-quick-actions">
        <button type="button">
          <CalendarPlus size={20} aria-hidden="true" />
          <span>
            <strong>{text.manualCreate}</strong>
          </span>
        </button>
        <button type="button">
          <Sparkles size={20} aria-hidden="true" />
          <span>
            <strong>{text.aiCreate}</strong>
          </span>
        </button>
        <button type="button">
          <ListTodo size={20} aria-hidden="true" />
          <span>
            <strong>{text.allGoals}</strong>
          </span>
        </button>
      </div>
      <div className="visual-goal-tabs">
        <span>{text.ongoing}</span>
        <span>{text.completed}</span>
        <span>{text.all}</span>
      </div>
    </div>
  );
}
