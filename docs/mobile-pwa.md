# MileDay 모바일 PWA

MileDay 모바일 PWA는 기존 MileDay 계정과 데이터를 그대로 사용하는 읽기 전용 모바일 companion 앱이다.

## 전체 구조

```text
mobile-pwa React/Vite
  -> 기존 Render FastAPI
  -> 기존 Supabase Auth와 MileDay 테이블

Web Push
  -> FastAPI push endpoint
  -> push_subscriptions / notification_settings / notification_delivery_log
  -> 브라우저 Push Service
  -> iOS 또는 Android에 설치된 PWA
```

이 PWA는 일정을 생성, 수정, 삭제하지 않는다. 기존 인증이 적용된 Calendar API를 통해 `goals.deadline`과 `milestones.scheduled_date` 데이터를 읽어 화면에 보여준다.

## 프론트엔드

- 소스 위치: `mobile-pwa/`
- 사용 기술: React, TypeScript, Vite
- 주요 화면: Today, Calendar, Settings
- PWA 파일: `mobile-pwa/public/manifest.webmanifest`, `mobile-pwa/public/service-worker.js`
- 디자인 토큰: 기존 `frontend/src/styles.css`의 MileDay 색상 값을 재사용한다.

로컬 실행:

```powershell
cd mobile-pwa
npm install
npm run dev
```

빌드:

```powershell
cd mobile-pwa
npm run build
```

운영 호스트는 PWA를 SPA로 서빙해야 한다. `/today`, `/calendar`, `/settings` 같은 route는 모두 `index.html`로 fallback되어야 한다.

## 백엔드 변경 사항

추가된 endpoint:

```text
GET  /push/config
POST /push/subscribe
POST /push/unsubscribe
POST /push/test
GET  /push/settings
PATCH /push/settings
```

기존 auth dependency가 Supabase access token을 계속 검증한다. 프론트엔드에는 `VAPID_PUBLIC_KEY`만 전달하고, VAPID private key는 백엔드 환경 변수에만 둔다.

## Supabase 변경 사항

Migration 파일:

```text
supabase/migrations/202609300001_add_mobile_push_notifications.sql
```

추가 테이블:

- `push_subscriptions`
- `notification_settings`
- `notification_delivery_log`

모든 신규 테이블에는 RLS를 활성화했다. 사용자-facing 정책은 인증된 사용자가 자기 subscription과 notification settings row에만 접근하도록 제한한다. 스케줄러 조회와 delivery log 기록은 기존 백엔드 service role client를 사용한다.

매일 같은 사용자에게 같은 알림이 중복 발송되지 않도록 아래 unique constraint로 막는다.

```text
unique(user_id, delivery_date, notification_type)
```

## 환경 변수

Backend / Render:

```text
VAPID_PUBLIC_KEY=
VAPID_PRIVATE_KEY=
VAPID_CLAIMS_EMAIL=
NOTIFICATION_SCHEDULER_ENABLED=false
NOTIFICATION_SCHEDULER_INTERVAL_SECONDS=60
SUPABASE_URL=
SUPABASE_SERVICE_ROLE_KEY=
CORS_ORIGINS=https://your-pwa-host.example
```

Frontend PWA:

```text
VITE_API_BASE_URL=
VITE_VAPID_PUBLIC_KEY=
```

VAPID key 생성:

```powershell
npx web-push generate-vapid-keys
```

실제 VAPID key와 Supabase service role key는 Git에 commit하지 않는다.

## Scheduler

스케줄러는 기존 FastAPI process 안에서 실행되며, `NOTIFICATION_SCHEDULER_ENABLED=true`일 때만 동작한다.

각 사용자 설정에 대해 사용자의 `timezone` 기준 현재 시간이 `notification_time`과 일치하는지 확인한다. 알림 시간이 되면 먼저 해당 local date에 일정이 있는지, 그리고 push subscription이 하나 이상 있는지 확인한다. 그 다음 delivery log row를 생성하고 Web Push를 보낸다. 다른 worker가 이미 같은 row를 만들었다면 발송을 건너뛴다.

이 구조는 Render가 여러 worker로 실행되더라도 중복 발송 가능성을 낮춘다. 현재 repository에는 Render service 정의 파일이 없으므로, 실제 Render start command, worker 수, plan, sleep 여부는 Render Dashboard에서 직접 확인해야 한다.

## 실제 기기 설치 및 테스트

iPhone:

1. Safari에서 배포된 PWA URL에 접속한다.
2. 공유 버튼을 누른다.
3. 홈 화면에 추가한다.
4. 설치된 앱을 실행한다.
5. 기존 MileDay 계정으로 로그인한다.
6. Settings 화면에서 알림 권한을 허용한다.
7. 앱을 닫은 뒤 실제 Web Push 알림을 받는지 확인한다.

Android:

1. Chrome에서 배포된 PWA URL에 접속한다.
2. 앱 설치 또는 홈 화면에 추가를 선택한다.
3. 설치된 앱을 실행한다.
4. 기존 MileDay 계정으로 로그인한다.
5. Settings 화면에서 알림 권한을 허용한다.
6. 앱을 닫은 뒤 실제 Web Push 알림을 받는지 확인한다.

## 사용자가 직접 해야 하는 배포 작업

- Supabase migration을 적용한다. `supabase db push` 또는 Supabase SQL Editor를 사용할 수 있다.
- 운영용 VAPID key를 생성한다.
- Render에 백엔드 환경 변수를 등록한다.
- PWA 호스트에 프론트엔드 환경 변수를 등록한다.
- 배포된 PWA origin을 백엔드 `CORS_ORIGINS`에 포함한다.
- 네트워크 사용이 가능한 환경에서 `cd mobile-pwa && npm install && npm run build`를 실행한다.
- Render start command, worker 수, service plan, sleep 여부를 확인한다.
- DB migration과 VAPID 설정이 끝난 뒤 `NOTIFICATION_SCHEDULER_ENABLED=true`를 켠다.
- 실제 iPhone과 Android에서 Push 알림을 테스트한다.

## 검증 상태

로컬 백엔드 검증:

```powershell
pytest -q
python -m compileall backend\app
```

모바일 PWA 소스 검증:

```powershell
cd mobile-pwa
npm install
npm run build
```

현재 작업 환경에서는 `mobile-pwa` dependency 설치가 수행되지 않았기 때문에, 전체 Vite bundle은 아직 이 환경에서 증명되지 않았다. TypeScript 검사는 이미 설치되어 있던 `frontend` dependency tree를 임시로 참조해 통과했지만, 최종 PWA build는 `mobile-pwa/node_modules`가 준비된 뒤 위 명령으로 다시 확인해야 한다.

## 알려진 제한 사항

- 첫 모바일 버전은 online-first로 동작한다. Service Worker는 앱 shell과 기본 asset cache에만 사용한다.
- iOS Web Push는 iOS 16.4 이상과 홈 화면에 설치된 PWA가 필요하다.
- Render service가 sleep 상태라면 FastAPI process 안의 scheduler가 정확한 시간에 실행되지 않을 수 있다.
- 이번 버전은 일정 생성, 일정 수정, 일정 삭제, AI 일정 생성, Calendar 연동, App Store 배포, Capacitor, Expo, React Native를 지원하지 않는다.
