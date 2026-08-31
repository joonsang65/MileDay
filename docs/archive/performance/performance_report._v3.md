# MileDay 성능 개선 보고서 v3

> 작성일: 2026-08-14  
> 기준 문서: `docs/performance_report._v2.md`  
> 목표: API 5xx 비율 0.5% 미만, Playwright E2E 성공률 99% 이상  
> 측정 환경: Electron 개발 서버 + 로컬 FastAPI + 원격 Supabase + Playwright 성능 harness

---

## 1. 요약

v2 이후 남은 핵심 문제는 API 5xx 비율이었다. v2 측정에서는 전체 API 5xx 비율이 7.91%였고, TTL/fallback 적용 후에도 3.14%로 목표인 0.5% 미만에 도달하지 못했다.

실패 패턴을 확인한 결과 `/settings`와 `/calendar/month`가 같은 iteration에서 거의 동시에 502를 반환했다. 두 endpoint는 서로 다른 서비스 로직을 사용하지만 공통으로 `require_current_user_id -> AuthService.get_user()` 인증 경로를 거친다. 따라서 남은 5xx의 핵심 원인은 endpoint 내부 조회보다 Supabase Auth 토큰 검증 호출의 순간적 실패로 판단했다.

v3에서는 정상 요청에는 지연을 추가하지 않고, Supabase Auth 호출이 transient 오류로 실패할 때만 100ms backoff 후 재시도하도록 수정했다. 또한 성능 검증 로그에는 raw 5xx와 재시도 후에도 복구되지 않은 5xx를 구분하는 `api_summary`를 추가했다.

최신 측정 결과 전체 API 5xx 비율은 0.41%로 내려갔고, E2E 성공률은 99.2%로 유지됐다.

---

## 2. 수정 내용

### 2.1 Auth 검증 100ms backoff

변경 파일: `backend/app/services/auth_service.py`

Supabase Auth 호출을 `_run_auth_operation()`으로 감싸고, retryable 오류에 대해서만 재시도한다.

```text
Auth 호출
-> 성공: 즉시 반환
-> transient 실패: 100ms 대기
-> Supabase auth client 캐시 초기화
-> 재시도
-> 두 번째 transient 실패: 300ms 대기 후 마지막 재시도
```

적용 대상:

| 메서드 | 적용 |
|---|---|
| `signup` | 적용 |
| `login` | 적용 |
| `get_user` | 적용 |
| `logout` | 적용 |

정상 요청에는 sleep을 넣지 않았다. 따라서 일반 UX에는 고정 지연이 추가되지 않고, 외부 Auth/네트워크가 흔들릴 때만 복구 비용을 지불한다.

### 2.2 Supabase auth client 재생성

변경 파일: `backend/app/core/supabase.py`

`reset_supabase_client()`를 추가했다. Auth retry 전에 일반 Supabase client 캐시를 비워, 깨진 HTTP 연결을 재사용할 가능성을 줄인다.

### 2.3 조회 API 안정성 보강

v3 측정 전 반영된 조회 안정성 변경도 유지했다.

| 변경 | 목적 |
|---|---|
| `/settings` 사용자별 60초 TTL | 설정 조회 호출 수 감소 |
| `/calendar/month` 최근 성공값 fallback | 조회 실패 시 사용자-facing 5xx 완화 |
| DB 조회 retry wrapper | Supabase DB transient 오류 복구 |
| 프론트 설정 캐시 재사용 | 달력 갱신 시 `/settings` 중복 호출 감소 |

### 2.4 검증 로그 기준 보완

변경 파일: `tests/performance/perf_lib.mjs`

각 iteration 로그에 `api_summary`를 추가했다.

```json
{
  "total_calls": 0,
  "raw_5xx": 0,
  "recovered_5xx": 0,
  "unrecovered_5xx": 0
}
```

같은 method + URL 요청이 5xx 이후 재시도되어 최종적으로 2xx/3xx를 반환하면 `recovered_5xx`로 분류한다. 최종 상태도 5xx인 경우만 `unrecovered_5xx`로 본다.

---

## 3. v3 측정 결과

측정 로그:

```text
logs/perf/goal-create-20260814-153925-KST.jsonl
logs/perf/settings-update-20260814-154007-KST.jsonl
logs/perf/milestone-create-20260814-154042-KST.jsonl
logs/perf/milestone-toggle-20260814-154205-KST.jsonl
logs/perf/date-select-20260814-154334-KST.jsonl
```

| 플로우 | 성공률 | 평균 | P95 | 최대 | API 호출 | raw 5xx | unrecovered 5xx |
|---|---:|---:|---:|---:|---:|---:|---:|
| 목표 생성 후 UI 표시 | 100.0% | 828.74ms | 839.18ms | 841.61ms | 48 | 0 | 0 |
| 설정 변경 후 달력 반영 | 100.0% | 666.65ms | 1,195.51ms | 1,216.65ms | 48 | 0 | 0 |
| 마일스톤 생성 후 UI 표시 | 100.0% | 2,206.73ms | 2,636.34ms | 3,010.21ms | 125 | 0 | 0 |
| 마일스톤 토글 시각 반응 | 96.0% | 52.69ms | 64.51ms | 65.44ms | 25 | 1 | 1 |
| 날짜 선택 후 하루 보기 표시 | 100.0% | 67.08ms | 97.38ms | 100.01ms | 0 | 0 | 0 |

v1, v2, v3 latency 비교:

| 플로우 | v1 성공률 | v1 평균 | v1 P95 | v2 성공률 | v2 평균 | v2 P95 | v3 성공률 | v3 평균 | v3 P95 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 목표 생성 후 UI 표시 | 84.0% | 3,736.32ms | 4,964.87ms | 100.0% | 829.86ms | 840.45ms | 100.0% | 828.74ms | 839.18ms |
| 마일스톤 생성 후 UI 표시 | 92.0% | 5,278.90ms | 8,023.03ms | 100.0% | 1,888.74ms | 2,028.41ms | 100.0% | 2,206.73ms | 2,636.34ms |
| 마일스톤 토글 시각 반응 | 96.0% | 5,946.05ms | 8,028.67ms | 96.0% | 62.51ms | 75.77ms | 96.0% | 52.69ms | 64.51ms |
| 설정 변경 후 달력 반영 | 100.0% | 1,020.23ms | 1,331.89ms | 100.0% | 841.33ms | 977.24ms | 100.0% | 666.65ms | 1,195.51ms |
| 날짜 선택 후 하루 보기 표시 | 84.0% | 3,404.35ms | 4,893.93ms | 100.0% | 65.36ms | 98.28ms | 100.0% | 67.08ms | 97.38ms |

v1 대비 v3 latency 개선:

| 플로우 | v1 P95 | v3 P95 | P95 변화 | 판단 |
|---|---:|---:|---:|---|
| 목표 생성 후 UI 표시 | 4,964.87ms | 839.18ms | 83.10% 감소 | 대폭 개선 |
| 마일스톤 생성 후 UI 표시 | 8,023.03ms | 2,636.34ms | 67.14% 감소 | 개선, v2보다 일부 상승 |
| 마일스톤 토글 시각 반응 | 8,028.67ms | 64.51ms | 99.20% 감소 | 대폭 개선 |
| 설정 변경 후 달력 반영 | 1,331.89ms | 1,195.51ms | 10.24% 감소 | 개선 폭 제한적 |
| 날짜 선택 후 하루 보기 표시 | 4,893.93ms | 97.38ms | 98.01% 감소 | 대폭 개선 |

v2 대비 v3 변화:

| 플로우 | v2 P95 | v3 P95 | 변화 | 해석 |
|---|---:|---:|---:|---|
| 목표 생성 후 UI 표시 | 840.45ms | 839.18ms | 0.15% 감소 | 거의 동일 |
| 마일스톤 생성 후 UI 표시 | 2,028.41ms | 2,636.34ms | 29.97% 증가 | Auth/외부 서비스 복구 비용과 reload 경로 영향 |
| 마일스톤 토글 시각 반응 | 75.77ms | 64.51ms | 14.86% 감소 | 시각 반응 개선 |
| 설정 변경 후 달력 반영 | 977.24ms | 1,195.51ms | 22.34% 증가 | backoff 발동 iteration 영향 |
| 날짜 선택 후 하루 보기 표시 | 98.28ms | 97.38ms | 0.92% 감소 | 거의 동일 |

전체 집계:

| 지표 | v1 | v2 | v3 | 상태 |
|---|---:|---:|---:|---|
| E2E 성공률 | 91.2% | 99.2% | 99.2% | 목표 달성 |
| API 호출 수 | 823 | 316 | 246 | 지속 감소 |
| raw API 5xx | 36 | 25 | 1 | 대폭 감소 |
| raw API 5xx 비율 | 4.37% | 7.91% | 0.41% | 목표 달성 |
| unrecovered API 5xx | 별도 집계 없음 | 별도 집계 없음 | 1 | 목표 달성 |
| unrecovered API 5xx 비율 | 별도 집계 없음 | 별도 집계 없음 | 0.41% | 목표 달성 |

---

## 4. 해석

v3에서 `/settings`, `/calendar/month`의 동시 502 패턴은 사라졌다. 이는 endpoint 내부 조회보다 인증 검증 경로의 순간적 실패가 주요 원인이었다는 판단과 맞다.

남은 5xx 1건은 마일스톤 토글 플로우의 사전 데이터 준비 단계에서 발생한 `POST /goals` 실패다. 이 실패는 Auth 검증이나 조회 API가 아니라 쓰기 API의 `RemoteProtocolError`이며, 중복 생성 위험 때문에 자동 재시도를 적용하지 않은 영역이다.

API 5xx 목표는 달성했지만, 마일스톤 생성 P95는 v2 대비 상승했다. backoff가 실제로 발동한 iteration에서는 외부 서비스 복구 비용이 latency에 반영될 수 있다. MVP 사용자 테스트 기준으로는 5xx 노출 감소가 더 중요하지만, 다음 단계에서는 쓰기 API의 idempotency key 기반 재시도 또는 테스트 데이터 준비 경로 분리가 필요하다.

---

## 5. 검증

백엔드:

```text
pytest
99 passed, 1 deselected
coverage 94.33%
```

프론트엔드:

```text
npm test
37 passed
```

빌드:

```text
npm run build
통과
```

---

## 6. 현재 판단

MVP 사용자 테스트를 막던 API 5xx 비율 목표는 달성했다. v3 기준 전체 API 5xx 비율은 0.41%이며, 전체 E2E 성공률은 99.2%다.

다음으로 남은 개선 후보는 쓰기 API의 간헐적 `RemoteProtocolError`다. 다만 쓰기 요청은 중복 생성 위험이 있으므로 단순 자동 재시도 대신 idempotency key를 설계한 뒤 적용하는 것이 맞다.
