# MileDay Backend Tests

MileDay 백엔드의 테스트 스위트 및 실행 가이드입니다.

---

## 🧪 테스트 범위

- **앱 부트스트랩**: FastAPI app 초기화, health check (`/health`, `/health/db`), router 등록 검증
- **환경 설정 & 로깅**: `.env` 로드, CORS origin 파싱, `X-Request-ID` 요청 추적, 민감 정보 마스킹
- **오류 처리**: Custom Exception, Validation Error, 글로벌 핸들러 및 일관된 Error Response 검증
- **비즈니스 로직**: Auth, Goals, Milestones, Calendar, Settings 서비스 및 저장소 테스트
- **DB 마이그레이션**: 테이블 스키마, FK cascade, RLS 정책, 트리거 유효성 검증

---

## 🚀 테스트 실행 방법

### 1. 단위 / 로컬 테스트 실행
기본 테스트는 외부 Supabase 네트워크 호출 없이 모킹 및 로컬 환경에서 실행됩니다:

```bash
pytest
```

### 2. 커버리지 리포트 확인
`pytest.ini`에 커버리지 90% 이상 기준이 설정되어 있습니다:

```bash
pytest --cov=backend/app --cov-report=term-missing --cov-fail-under=90
```

### 3. Supabase 실제 통합 테스트
실제 원격 Supabase와 연동하는 통합 테스트는 `integration` 마커를 통해 분리되어 있습니다:

```bash
pytest -m integration
```

> **주의 사항**:
> - `ENABLE_INTEGRATION_TESTS=true` 및 테스트용 계정 환경 변수(`TEST_EMAIL`, `TEST_USER_ID` 등)가 필요합니다.
> - 테스트 데이터는 `[TEST]` prefix를 사용하며, 테스트 완료 후 해당 user_id의 데이터만 안전하게 cleanup됩니다.
