import { FormEvent, useState } from "react";
import { LogIn, UserPlus } from "lucide-react";

type AuthPanelProps = {
  isLoading: boolean;
  errorMessage?: string | null;
  noticeMessage?: string | null;
  onLogin: (email: string, password: string) => Promise<void>;
  onSignup: (email: string, password: string) => Promise<void>;
};

type AuthMode = "login" | "signup";

export function AuthPanel({
  isLoading,
  errorMessage,
  noticeMessage,
  onLogin,
  onSignup,
}: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [validationMessage, setValidationMessage] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setValidationMessage(null);

    if (!email.trim()) {
      setValidationMessage("이메일을 입력해 주세요.");
      return;
    }
    if (!password) {
      setValidationMessage("비밀번호를 입력해 주세요.");
      return;
    }

    if (mode === "signup") {
      if (password.length < 8) {
        setValidationMessage("비밀번호는 8자 이상이어야 합니다.");
        return;
      }
      if (password !== passwordConfirm) {
        setValidationMessage("비밀번호 확인이 일치하지 않습니다.");
        return;
      }
      await onSignup(email.trim(), password);
      setMode("login");
      setPassword("");
      setPasswordConfirm("");
      return;
    }

    await onLogin(email.trim(), password);
  }

  function switchMode(nextMode: AuthMode) {
    setMode(nextMode);
    setPassword("");
    setPasswordConfirm("");
    setValidationMessage(null);
  }

  return (
    <main className="auth-shell">
      <section className="auth-panel" aria-labelledby="auth-title">
        <div className="brand-mark">MileDay</div>
        <div className="auth-heading">
          <h1 id="auth-title">{mode === "login" ? "로그인" : "회원가입"}</h1>
          <div className="auth-tabs" role="group" aria-label="인증 방식">
            <button
              type="button"
              className={mode === "login" ? "active" : ""}
              onClick={() => switchMode("login")}
            >
              로그인
            </button>
            <button
              type="button"
              className={mode === "signup" ? "active" : ""}
              onClick={() => switchMode("signup")}
            >
              회원가입
            </button>
          </div>
        </div>
        <form onSubmit={handleSubmit} className="auth-form">
          <label>
            이메일
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
            비밀번호
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
              비밀번호 확인
              <input
                type="password"
                autoComplete="new-password"
                value={passwordConfirm}
                onChange={(event) => setPasswordConfirm(event.target.value)}
                disabled={isLoading}
                required
              />
            </label>
          ) : null}
          {noticeMessage ? <p className="notice-text">{noticeMessage}</p> : null}
          {validationMessage ? <p className="error-text">{validationMessage}</p> : null}
          {errorMessage ? <p className="error-text">{errorMessage}</p> : null}
          <button type="submit" className="primary-button" disabled={isLoading}>
            {mode === "login" ? (
              <LogIn size={18} aria-hidden="true" />
            ) : (
              <UserPlus size={18} aria-hidden="true" />
            )}
            {isLoading ? "처리 중" : mode === "login" ? "로그인" : "회원가입"}
          </button>
        </form>
      </section>
    </main>
  );
}
