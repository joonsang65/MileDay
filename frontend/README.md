# MileDay Frontend

MileDay의 Windows 데스크톱 위젯 프론트엔드 애플리케이션입니다.

---

## 🛠️ 기술 스택

- **Core**: Electron, React 18, TypeScript
- **Build / Tooling**: Vite, electron-vite
- **State Management**: Zustand
- **Date Utility**: date-fns
- **Styling**: Tailwind CSS / Vanilla CSS

---

## 🚀 개발 및 실행

### 패키지 설치
```bash
npm install
```

### 개발 모드 실행
```bash
npm run dev
```
> `electron-vite dev -w -- --disable-gpu-sandbox` 명령을 통해 Renderer HMR 및 Main/Preload 자동 재시작(watch)과 GPU sandbox 비활성화가 적용되어 실행됩니다.

### 빌드 및 검증
```bash
npm run lint     # ESLint 검증
npm test         # Vitest 유닛 테스트 실행
npm run build    # TypeScript 검증 및 electron-vite 빌드
```

### Windows 설치 파일 패키징
```bash
npm run dist     # NSIS Windows 설치 프로그램 (.exe) 생성
```

---

## 📂 주요 디렉터리 구조

- `electron/`: Electron Main Process (`main.ts`), Preload (`preload.ts`), 윈도우 생성 옵션 (`windowOptions.ts`)
- `src/components/`: 캘린더, 날짜 상세 (Day View), 목표/마일스톤 생성 및 편집 패널, 설정 패널
- `src/store/`: Zustand 기반 UI 상태 및 전역 데이터 스토어
- `src/api/`: FastAPI 백엔드 통신용 클라이언트 및 타입 정의
- `scripts/`: 개발 실행(`dev.mjs`) 및 패키징 검증 스크립트
