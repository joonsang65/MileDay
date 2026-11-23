import React from "react";

import { api } from "../api";

export function Login({ onLogin }: { onLogin: () => void }) {
  const [email, setEmail] = React.useState("");
  const [password, setPassword] = React.useState("");
  const [error, setError] = React.useState("");
  const [loading, setLoading] = React.useState(false);

  async function submit(event: React.FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError("");
    try {
      await api.login(email, password);
      onLogin();
    } catch (error) {
      setError(error instanceof Error ? error.message : "로그인할 수 없습니다.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-shell">
      <form className="login-panel" onSubmit={submit}>
        <div>
          <p className="eyebrow">MileDay</p>
          <h1>오늘 일정을 확인하세요</h1>
        </div>
        <label>
          이메일
          <input value={email} type="email" autoComplete="email" onChange={(event) => setEmail(event.target.value)} />
        </label>
        <label>
          비밀번호
          <input value={password} type="password" autoComplete="current-password" onChange={(event) => setPassword(event.target.value)} />
        </label>
        {error ? <p className="error-text">{error}</p> : null}
        <button className="primary-button" disabled={loading}>{loading ? "로그인 중" : "로그인"}</button>
      </form>
    </main>
  );
}
