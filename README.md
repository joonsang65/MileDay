# MileDay

Windows 데스크톱에서 동작하는 위젯형 목표/일정 관리 플래너 애플리케이션입니다.

---

## 📌 프로젝트 개요

- **형태**: Windows 데스크톱 위젯 (Electron 기반)
- **주요 기능**:
  - 목표(Goal) 및 하위 마일스톤(Milestone) CRUD 관리
  - 월간/주간 캘린더 조회 및 날짜별 상세 일정 관리 (Day View)
  - 오늘 할 일(Today List) 조회 및 완료 토글
  - 사용자 환경 설정 (테마, 글꼴 크기, 시작 요일, 언어 등)
  - Supabase Auth 기반 회원가입/로그인

---

## 🏗️ 아키텍처

```text
Electron + React + TypeScript (Frontend)
         ↓ HTTP / IPC
       FastAPI (Backend)
         ↓
Supabase PostgreSQL / Supabase Auth
```

---

## 🚀 빠른 시작 (개발 환경)

### 1. 사전 요구사항
- **Node.js**: v18+
- **Python**: v3.11+
- **Supabase**: 프로젝트 생성 및 환경 변수 설정

### 2. 한 번에 실행 (권장)
루트 경로에서 제공되는 스크립트를 사용해 백엔드 헬스체크 완료 후 프론트엔드를 자동 실행합니다.

```cmd
.\dev.cmd
```
또는 PowerShell에서:
```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1
```

> **참고**: 개발 환경에서 Electron 실행 시 `--disable-gpu-sandbox` 플래그 및 main/preload watch 모드(`-w`)가 자동으로 적용됩니다.

---

## 📁 디렉터리 구조

- `frontend/`: Electron + React + TypeScript + Vite 기반 위젯 클라이언트
- `backend/`: Python + FastAPI 기반 REST API 서버
- `supabase/`: PostgreSQL 스키마 및 마이그레이션 SQL
- `docs/`: 프로젝트 규칙, API 명세서, 트러블슈팅, 요구사항 문서
- `tests/`: 백엔드 단위/통합 테스트 스위트
- `scripts/`: 개발 및 검증용 자동화 스크립트

---

## 📚 관련 문서

- [Codex 규칙 (`docs/codex_rules.md`)](docs/codex_rules.md)
- [API 명세서 (`docs/api_spec.md`)](docs/api_spec.md)
- [트러블슈팅 기록 (`docs/troubleshooting.md`)](docs/troubleshooting.md)
- [커밋 가이드 (`docs/commit_guide.md`)](docs/commit_guide.md)
