# Artifacts

`artifacts/`는 harness 실행 결과를 저장하는 로컬 산출물 디렉터리입니다. 모델 원문 응답, 파싱 결과, 성능 지표, 개별 리포트, batch summary가 이곳에 쌓입니다.

이 디렉터리는 제품 런타임 데이터가 아니라 평가 실행 증거입니다. Supabase DB, FastAPI backend, Electron frontend가 직접 참조하지 않습니다.

## 구조

```text
artifacts/
  runs/
    <run-id>/
      config.snapshot.yaml
      raw/
      parsed/
      metrics/
      report.md
    <batch-id>-summary.md
    <batch-id>-datasets/
```

| 경로 | 설명 |
|---|---|
| `runs/<run-id>/config.snapshot.yaml` | 실행 당시 모델, 데이터셋, timeout, mode 등 설정 snapshot |
| `runs/<run-id>/raw/` | 모델이 실제로 반환한 원문 응답 |
| `runs/<run-id>/parsed/` | parser와 scorer를 통과한 구조화 결과 |
| `runs/<run-id>/metrics/` | latency, throughput, resource sample 같은 성능 측정값 |
| `runs/<run-id>/report.md` | 단일 모델 run의 한국어 Markdown 리포트 |
| `runs/<batch-id>-summary.md` | 여러 모델을 함께 실행한 batch 요약 |
| `runs/<batch-id>-datasets/` | batch 내 모델들이 공유한 sampled dataset snapshot |

## 주요 파일

### `raw/*.txt`

모델의 원문 응답입니다. parser error, 비정상 언어 출력, fenced JSON 누락 같은 문제를 확인할 때 가장 먼저 봅니다.

예:

```powershell
rg -n "```json|</think>|ERROR" artifacts\runs\<run-id>\raw
```

### `parsed/results.json`

현재 benchmark 결과를 사람이 읽기 쉬운 JSON 배열로 저장하는 파일입니다. 이전 smoke 실행 기록에는 `results.jsonl`, `results.pretty.json`이 남아 있을 수 있습니다.

결과 해석 기준:

| 상태 | 의미 |
|---|---|
| `passed` | 평가 기준을 통과한 정상 결과 |
| `invalid` | 모델 응답은 있었지만 parser, schema, format, constraint 기준을 만족하지 못한 결과 |
| `failed` | runtime, timeout, dependency, 코드 오류 등 실행 자체가 실패한 결과 |
| `skipped` | 설정 또는 외부 의존성 문제로 평가 일부를 의도적으로 생략한 결과 |

### `metrics/performance.jsonl`

성능 측정값은 append-only JSONL로 저장됩니다. 각 줄은 하나의 case 실행에 대한 metric sample입니다.

자주 보는 필드:

| 필드 | 의미 |
|---|---|
| `latency_ms` | 요청 시작부터 응답 완료까지 걸린 시간 |
| `ttft_ms` | 첫 토큰까지 걸린 시간. runtime이 제공하지 않으면 비어 있을 수 있음 |
| `tokens_per_second` | 추론 처리량 |
| `phase` | `cold_measured`, `warm_measured` 등 측정 phase |

`cold`는 모델 초기 호출 비용이 섞일 수 있고, `warm`은 이미 모델이 로드된 뒤의 반복 호출 조건에 가깝습니다.

## Run ID 규칙

현재 harness는 명령별로 다음 패턴을 사용합니다.

| 명령 | 예시 |
|---|---|
| `run-mileday-smoke` | `candidate-3-5-5cases` |
| `run-benchmark` | `candidate-3-benchmark-1-50cases` |
| `run-third-benchmark` | `candidate-3-third-benchmark-2` |
| batch summary | `benchmark-batch-1-50cases-summary.md`, `third-benchmark-batch-1-summary.md` |

같은 run id를 재사용하면 기존 artifact와 섞일 수 있으므로 새 평가에는 새 sequence를 사용하는 편이 안전합니다.

## 트러블슈팅

### Parser error 원인 확인

```powershell
rg -n "PARSER_ERROR|invalid|json" artifacts\runs\<run-id>\parsed
```

그다음 같은 case id의 `raw/*.txt`를 열어 실제 출력 구조를 확인합니다.

### 특정 비정상 문구가 어느 모델에서 나왔는지 찾기

```powershell
rg -n "검색할 문구" artifacts\runs
```

### Gemini judge skipped 확인

`parsed/results.json`에서 `explanation_judge.skipped` 또는 `error.category`를 확인합니다. `.env`에 `GEMINI_API_KEY`가 없거나, `GEMINI_JUDGE_MODEL`이 실제 API에서 지원되지 않으면 skipped 또는 external dependency error가 발생할 수 있습니다.

## 관리 기준

- `artifacts/`는 재생성 가능한 평가 산출물입니다.
- 중요한 평가 리포트는 삭제하기 전에 대응되는 실행 명령, 모델, 데이터셋, seed, limit을 별도로 기록합니다.
- 모델 원문 응답에는 프롬프트나 민감 정보가 포함될 수 있으므로 외부 공유 전 내용을 확인합니다.
- 장기 보관할 결론은 `docs/decisions/` 또는 별도 평가 리포트 문서로 옮깁니다.
