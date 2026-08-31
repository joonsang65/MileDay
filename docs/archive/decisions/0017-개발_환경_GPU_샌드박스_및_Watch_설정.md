# ADR 0017: 개발 환경 Electron GPU Sandbox 크래시 해결 및 Watch 모드 적용

- 날짜: 2026-08-17
- 상태: Accepted
- 관련 영역: Electron / Dev Tooling / Build System / Developer Experience
- 관련 파일:
  - `dev.cmd`
  - `scripts/dev.ps1`
  - `frontend/package.json`
  - `frontend/scripts/dev.mjs`
  - `frontend/node_modules/electron-vite`

---

## 1. 배경 (Context & Problem Statement)

MileDay는 로컬 개발 시 백엔드(FastAPI)와 프론트엔드(Electron/Vite)를 한 번에 띄울 수 있도록 루트 경로에 원클릭 실행 스크립트(`dev.cmd` 및 `scripts/dev.ps1`)를 제공한다.

그러나 개발 환경에서 다음과 같은 치명적인 실행 및 생산성 문제가 발생했다:

### 문제 1: GPU Process 반복 Crash로 인한 앱 실행 불가
- 루트 `dev.cmd`를 실행하면 백엔드 헬스체크(`/health`, `/health/db`)는 정상 통과하지만, 프론트엔드 단계로 넘어가면서 Electron 프로세스가 다음과 같은 에러 로그를 뿜으며 반복 비정상 종료(Crash)되었다.
  ```text
  [GPU Process Crash] [ERROR:gpu_process_host.cc] GPU process exited unexpectedly: exit_code=-1073741819
  ```
- 반면 터미널에서 `npx electron . --disable-gpu-sandbox`로 직접 플래그를 주어 실행할 때는 GPU 크래시 없이 정상적으로 위젯 창이 떴다.

### 문제 2: 코드 수정 시 Main/Preload 자동 반영(Watch) 미작동
- 개발 중 React 컴포넌트나 CSS는 Vite HMR로 즉시 반영되었으나, `electron/main.ts`나 `electron/preload.ts`의 로직(IPC 핸들러, 윈도우 옵션 등)을 수정하면 자동으로 반영되지 않았다.
- 매번 개발 스크립트를 수동으로 껐다 켜야 했으며, 이로 인해 메인 프로세스 버그 수정 시 구 버전 번들이 계속 실행되는 원인이 되었다.

---

## 2. 원인 분석 (Deep Dive Root Cause Analysis)

### 2.1 개발 실행 콜체인 (Execution Call Chain)
전체 실행 흐름은 다음과 같다:
```text
dev.cmd
  └─> powershell scripts/dev.ps1
        ├─> Uvicorn Backend 시작 & /health 대기
        └─> cd frontend && npm run dev
              └─> node scripts/dev.mjs
                    └─> cmd.exe /c electron-vite dev
                          └─> startElectron() (Electron 바이너리 spawn)
```

### 2.2 `electron-vite`의 CLI 인수 전달 메커니즘 (`ELECTRON_CLI_ARGS`)
`electron-vite` 내부 코드(`node_modules/electron-vite/dist/cli.js` 및 `chunks/lib-q6ns0vZr.js`)를 추적 분석한 결과, Electron으로 인수를 넘기는 고유한 계약이 존재함을 확인했다.

1. **CLI 레벨 (`cli.js`)**:
   ```javascript
   if (options['--']) {
     process.env.ELECTRON_CLI_ARGS = JSON.stringify(options['--']);
   }
   ```
   - `electron-vite dev` 명령어 뒤에 `--` 구분자를 두고 인자를 전달해야만 `ELECTRON_CLI_ARGS` 환경 변수에 JSON 배열 형태로 저장된다.
2. **Spawn 레벨 (`lib-q6ns0vZr.js`의 `startElectron`)**:
   ```javascript
   function startElectron(root) {
     ensureElectronEntryFile(root);
     const electronPath = getElectronPath();
     // ELECTRON_CLI_ARGS가 있으면 파싱하여 Electron 아규먼트에 추가
     const args = process.env.ELECTRON_CLI_ARGS ? JSON.parse(process.env.ELECTRON_CLI_ARGS) : [];
     // ...
     const ps = spawn(electronPath, [entry].concat(args), { stdio: 'inherit' });
     return ps;
   }
   ```

### 2.3 Watch 모드 플래그(`-w`)의 부재
`electron-vite`는 기본적으로 Main과 Preload 스크립트에 대해 1회성 빌드만 수행하고 감시(Watch)를 켜지 않는다. `-w` 또는 `--watch` 옵션이 명시되어야만 Rollup/Vite의 watch 플러그인이 활성화되어, 파일 변경 시 자동으로 기존 Electron 프로세스를 `kill()`하고 `startElectron()`을 재호출한다.

---

## 3. 해결 방향 및 아키텍처 결정 (Architecture Decisions)

```mermaid
flowchart LR
    A[npm run dev] --> B[frontend/scripts/dev.mjs]
    B --> C["electron-vite dev -w -- --disable-gpu-sandbox"]
    C --> D[Vite Dev Server 기동 & Main/Preload 컴파일]
    D --> E[ELECTRON_CLI_ARGS = '[\"--disable-gpu-sandbox\"]' 설정]
    E --> F["startElectron(electron . --disable-gpu-sandbox)"]
    F --> G[GPU Crash 없이 위젯 정상 실행]
    
    H[Main/Preload 소스 코드 수정] --> I[watchHook 감지]
    I --> J[기존 Electron 프로세스 kill]
    J --> K[신규 번들 컴파일 후 Electron 자동 재시작]
```

### 결정 원칙: 최소 침습적 변경 (Minimal Invasive Change)
- `dev.cmd`나 `scripts/dev.ps1`과 같은 루트 오케스트레이션 스크립트를 불필요하게 수정하지 않는다.
- 프론트엔드 패키지 전용 런처인 `frontend/scripts/dev.mjs`에서만 정확한 인수를 넘겨 문제를 단일 지점에서 해결한다.

---

## 4. 상세 구현 내용 (Implementation Details)

### 4.1 `frontend/scripts/dev.mjs` 수정
`electron-vite dev` 호출 시 `-w`와 `-- --disable-gpu-sandbox`를 명시적으로 결합했다.

```javascript
// frontend/scripts/dev.mjs
import { spawn } from "node:child_process";

const env = { ...process.env };
delete env.ELECTRON_RUN_AS_NODE;

const command = process.platform === "win32" ? "cmd.exe" : "electron-vite";
const args =
  process.platform === "win32"
    ? ["/d", "/s", "/c", "electron-vite dev -w -- --disable-gpu-sandbox"]
    : ["dev", "-w", "--", "--disable-gpu-sandbox"];

const child = spawn(command, args, {
  stdio: "inherit",
  env,
});

child.on("exit", (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
    return;
  }
  process.exit(code ?? 0);
});
```

---

## 5. 변경 대상별 리로드 매트릭스 (Reload Matrix)

| 변경 대상 파일 | 동작 방식 | Electron 프로세스 재시작 여부 | 반영 속도 |
|---|---|---|---|
| **React 컴포넌트** (`src/components/*.tsx`) | Vite HMR (Hot Module Replacement) | ❌ 재시작 없음 (앱 상태 유지) | 즉각 반영 (< 100ms) |
| **스타일시트** (`src/styles.css`) | CSS HMR | ❌ 재시작 없음 | 즉각 반영 (< 50ms) |
| **Electron Main** (`electron/main.ts`) | `-w` Watch Hook -> Rebuild & Restart | ⭕ 자동으로 프로세스 재시작 | 자동 리로드 (~ 1s) |
| **Electron Preload** (`electron/preload.ts`) | `-w` Watch Hook -> Full Page Reload | ❌ Electron 유지, 렌더러만 리로드 | 자동 리로드 (~ 500ms) |

---

## 6. 검증 및 결과 (Validation & Impact)

1. **GPU 안정성 검증**:
   - `dev.cmd` 실행 시 GPU 크래시 로그가 완전히 사라지고, 최소 윈도우 크기로 위젯 창이 즉각 정상 렌더링됨을 확인.
2. **핫 리로드 & Watch 검증**:
   - `electron/main.ts`의 IPC 핸들러 코드를 수정했을 때 터미널에 `restarting electron app...` 로그가 출력되며 최신 로직이 즉시 적용됨을 확인.
3. **개발 생산성 향상**:
   - 수동 프로세스 종료 및 재실행 작업이 불필요해져 기능 개발 및 버그 수정 반복 주기가 대폭 단축됨.
