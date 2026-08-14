import { FormEvent, useState } from "react";
import { ChevronLeft, ChevronRight, LogIn, Plus, Settings, UserPlus } from "lucide-react";

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
export type AuthLanguage = "ko" | "en";

type OnboardingSlide = {
  title: string;
  description: string;
  points: string[];
  icon: "goal" | "milestone" | "day" | "settings";
};

const ONBOARDING_DISMISSED_KEY = "mileday.signup_onboarding_dismissed";
const AUTH_LANGUAGE_KEY = "mileday.auth_language";

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
        title: "달력에서 목표 확인",
        description: "목표와 마감일을 날짜별로 정리해 한눈에 확인하세요.",
        points: [
          "날짜별 목표와 진행 상황을 달력에서 빠르게 확인합니다.",
          "공휴일과 목표 일정을 함께 보며 겹치는 일정을 미리 파악합니다.",
          "색상 표시로 중요한 목표가 있는 날짜를 쉽게 구분합니다.",
        ],
        icon: "goal",
      },
      {
        title: "마일스톤으로 나누기",
        description: "간단한 일정은 목표만 등록하고, 큰 목표는 세부 단계로 나누세요.",
        points: [
          "목표 이름과 마감일을 먼저 정해 전체 방향을 잡습니다.",
          "세부 마일스톤마다 해야 할 일과 날짜를 따로 설정합니다.",
          "간단한 일정은 마일스톤 없이 목표만 등록해도 됩니다.",
        ],
        icon: "milestone",
      },
      {
        title: "하루 보기에서 관리",
        description: "목표와 마일스톤을 하루 보기에서 자세히 관리합니다.",
        points: [
          "선택한 날짜에 예정된 목표와 마일스톤을 한곳에서 확인합니다.",
          "완료 체크와 수정, 삭제 같은 세부 관리는 하루 보기에서 처리합니다.",
          "달력은 월간 흐름만 간단히 보여주어 화면이 복잡해지지 않습니다.",
        ],
        icon: "day",
      },
      {
        title: "내 화면에 맞게 설정",
        description: "개인 맞춤형 설정을 저장해 편하게 사용할 수 있습니다.",
        points: [
          "기본 글자와 일정 글자 크기를 내 화면에 맞게 조절합니다.",
          "창 크기와 위치를 저장해 원하는 자리에 계속 띄워둘 수 있습니다.",
          "자동 실행과 자동 로그인을 설정해 컴퓨터를 켜자마자 바로 시작합니다.",
        ],
        icon: "settings",
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
      settings: "설정",
      baseFontSize: "기본 글자 크기(px)",
      goalFontSize: "목표 글자 크기(px)",
      autoLaunch: "컴퓨터 시작 시 자동 실행",
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
        title: "Check Goals on Calendar",
        description: "Organize goals and deadlines by date so you can see them at a glance.",
        points: [
          "Quickly check goals and progress for each date.",
          "View holidays and goal schedules together to spot conflicts early.",
          "Use color markers to distinguish important goal dates.",
        ],
        icon: "goal",
      },
      {
        title: "Break Into Milestones",
        description: "Split larger goals into steps, or add a simple goal without milestones.",
        points: [
          "Set the goal name and deadline first.",
          "Give each milestone its own task name and date.",
          "Register simple schedules as goals only when you do not need steps.",
        ],
        icon: "milestone",
      },
      {
        title: "Manage the Day View",
        description: "Use the day view to manage goals and milestones for the selected date.",
        points: [
          "See goals and milestones scheduled for the selected date.",
          "Handle completion, editing, and deletion in the day view.",
          "Keep the monthly calendar simple by showing only the overall flow.",
        ],
        icon: "day",
      },
      {
        title: "Fit Your Screen",
        description: "Save window position, size, font sizes, and startup settings for easier use.",
        points: [
          "Adjust base text and schedule text sizes for your screen.",
          "Keep the widget at your preferred position and size.",
          "Launch automatically and sign in automatically when enabled.",
        ],
        icon: "settings",
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
      settings: "Settings",
      baseFontSize: "Base font size (px)",
      goalFontSize: "Goal font size (px)",
      autoLaunch: "Open at computer startup",
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
            <OnboardingVisual type={activeSlide.icon} text={text.visual} />
          </div>
          <div className="onboarding-copy">
            <span>{activeSlideIndex + 1} / {onboardingSlides.length}</span>
            <h2>{activeSlide.title}</h2>
            <p>{activeSlide.description}</p>
            <ul className="onboarding-points">
              {activeSlide.points.map((point) => (
                <li key={point}>{point}</li>
              ))}
            </ul>
          </div>
          <div className="onboarding-dots" aria-hidden="true">
            {onboardingSlides.map((slide) => (
              <span key={slide.title} className={slide === activeSlide ? "active" : ""} />
            ))}
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

function getInitialAuthLanguage(): AuthLanguage {
  return localStorage.getItem(AUTH_LANGUAGE_KEY) === "en" ? "en" : "ko";
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
          <Plus size={16} aria-hidden="true" />
        </div>
        <label>
          {text.goalTitle}
          <span>{text.goalExample}</span>
        </label>
        <label>
          {text.deadline}
          <span>2026-08-30</span>
        </label>
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
          <span>2026-08-15</span>
        </div>
        <div className="visual-summary">
          <span>{text.goalCount}</span>
          <span>{text.taskCount}</span>
        </div>
        <div className="visual-goal-row">
          <i />
          <div>
            <strong>{text.taskProgress}</strong>
            <span>{text.taskCount}</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="visual-settings-panel">
      <div className="visual-panel-header">
        <strong>{text.settings}</strong>
        <Settings size={16} aria-hidden="true" />
      </div>
      <label>
        {text.baseFontSize}
        <span>17</span>
      </label>
      <label>
        {text.goalFontSize}
        <span>19</span>
      </label>
      <div className="visual-toggle-row">
        <i />
        <span>{text.autoLaunch}</span>
      </div>
    </div>
  );
}
