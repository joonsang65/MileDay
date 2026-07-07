# MileDay Backend Tests

## 테스트 범위

- M1 앱 부트스트랩: FastAPI app, health check, router 등록
- 환경 설정: `.env` 로드, CORS origin 파싱, 로그 경로 정규화, Supabase 설정 여부
- 요청 문맥: `X-Request-ID` 생성/전달, 요청별 logging context 격리
- 공통 오류 응답: custom exception, validation error, HTTPException, unhandled exception
- 민감 정보 보호: password, token, Authorization, email, ai_prompt masking
- API 명세용 라우터: auth, goals, milestones, calendar, settings placeholder 응답
- Supabase client factory: 일반 client, admin client, 설정 누락 오류
- DB migration: 핵심 테이블, FK cascade, updated_at trigger, milestone 소유자 검증 trigger, RLS policy 존재 여부

## 기본 테스트 실행

기본 테스트는 실제 Supabase 네트워크를 호출하지 않는다. `integration` marker가 붙은 테스트는 기본 실행에서 제외된다.

```bash
pytest
```

## 커버리지 확인

`pytest.ini`에 90% 실패 기준이 들어 있다.

```bash
pytest --cov=backend/app --cov-report=term-missing --cov-fail-under=90
```

## 실제 Supabase 통합 테스트

같은 Supabase 프로젝트를 사용할 때는 별도 test 테이블을 만들지 않는다. 운영과 같은 `goals`, `milestones`, `user_settings` 테이블을 사용하되 테스트 전용 auth user의 `user_id`로만 데이터를 생성한다.

통합 테스트는 명시적으로 실행한다.

```bash
pytest -m integration
```

필수 환경 변수:

```env
ENABLE_INTEGRATION_TESTS=true
SUPABASE_URL=...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
INTEGRATION_TEST_EMAIL=test+integration@example.com
INTEGRATION_TEST_PASSWORD=...
INTEGRATION_TEST_USER_ID=...
INTEGRATION_TEST_TITLE_PREFIX=[TEST]
```

## 통합 테스트 안전 규칙

- `INTEGRATION_TEST_EMAIL`은 test 전용 계정이어야 한다.
- `INTEGRATION_TEST_TITLE_PREFIX`는 `[TEST`로 시작해야 한다.
- cleanup은 반드시 `user_id = INTEGRATION_TEST_USER_ID` 조건으로만 실행한다.
- `truncate` 또는 조건 없는 `delete` 금지.
- service role key는 통합 테스트 cleanup과 seed에만 사용한다.
- 실제 개인 계정 user_id로 통합 테스트 실행 금지.

## 테스트 의존성

```bash
pip install -r requirements.txt
```
