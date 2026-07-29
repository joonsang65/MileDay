# MileDay Local LLM Harness Guide

이 문서는 MileDay 로컬 LLM 평가 하네스의 현재 진행 상황, 실행 명령어, 코드 구조, 결과 파일, 트러블 슈팅을 정리한다.

## 현재 진행 상황

- Ollama 기반 로컬 모델 실행을 기본 runtime으로 사용한다.
- `configs/models.yaml`의 candidate 모델을 대상으로 MileDay 일정 생성 smoke 평가를 실행할 수 있다.
- MileDay fixture는 `tests/fixtures/mileday/synthetic_schedule.jsonl`에 JSONL 형식으로 관리한다.
- `run-mileday-smoke`는 단일 모델과 쉼표 기반 다중 모델 실행을 모두 지원한다.
- case 선택은 항상 random sampling이며, `--seed`로 재현성을 고정한다.
- 각 모델 run마다 raw output, parsed result, pretty JSON, performance metric, `report.md`를 저장한다.
- 다중 모델 실행 시 batch summary markdown을 자동 생성한다.
- 출력 계약은 `설명문 + fenced JSON`이다.
- JSON은 load 가능한 객체여야 하며, deterministic schedule validation을 통과해야 한다.
- Gemini API key가 설정되어 있으면 LLM-as-Judge로 explanation과 milestones의 일치성을 평가한다.
- batch summary 하단에는 LLM-as-Judge 전체 평가, 모델별 judge 통과율, 평균 score, 실패 원인, 위험 신호, 개선 방안이 추가된다.

## 환경 설정

루트 `.env`에 아래 값을 설정한다.

```env
OLLAMA_BASE_URL=http://localhost:11434

GEMINI_API_KEY=your_gemini_api_key
GEMINI_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta
GEMINI_JUDGE_MODEL=gemini-3.5-flash
MILEDAY_REQUIRE_EXPLANATION_JUDGE=false
```

`GEMINI_API_BASE_URL`은 Gemini API endpoint의 base URL이다. 일반 Google Gemini API를 직접 사용할 때는 기본값을 바꾸지 않아도 된다.

`MILEDAY_REQUIRE_EXPLANATION_JUDGE=false`이면 Gemini judge 실패나 미설정이 전체 평가를 반드시 실패시키지는 않는다. 운영 기준상 judge가 필수라면 `true`로 둔다.

## 기본 명령어

### 사전 점검

```powershell
python -m harness.cli preflight
```

Ollama 상태까지 확인하려면:

```powershell
python -m harness.cli preflight --check-ollama
```

### 모델 목록 확인

```powershell
python -m harness.cli list-models
```

로컬 설치 여부까지 확인하려면:

```powershell
python -m harness.cli list-models --check-installed
```

### 단일 모델 smoke 실행

```powershell
python -m harness.cli run-mileday-smoke `
  --fixture tests\fixtures\mileday\synthetic_schedule.jsonl `
  --model-id candidate-3 `
  --limit 5 `
  --seed 42
```

`--run-id`를 직접 지정할 수도 있다. 단, 직접 지정은 단일 모델 실행에서만 허용한다.

```powershell
python -m harness.cli run-mileday-smoke `
  --fixture tests\fixtures\mileday\synthetic_schedule.jsonl `
  --model-id candidate-3 `
  --run-id candidate-3-manual-5cases `
  --limit 5
```

### 다중 모델 smoke 실행

`--model-id`에 쉼표 문자열을 넣는다.

```powershell
python -m harness.cli run-mileday-smoke `
  --fixture tests\fixtures\mileday\synthetic_schedule.jsonl `
  --model-id candidate-1,candidate-3,candidate-5 `
  --limit 5 `
  --seed 42
```

다중 모델 실행에서는 batch 전체가 같은 sequence를 공유한다.

예:

```text
batch_id=batch-6-5cases
candidate-1 -> candidate-1-6-5cases
candidate-3 -> candidate-3-6-5cases
candidate-5 -> candidate-5-6-5cases
```

하나의 모델이 실패해도 다음 모델 실행은 계속된다.

## Run ID 규칙

자동 run id는 기존 패턴을 유지한다.

```text
{model_id}-{batch_sequence}-{limit}cases
```

예:

```text
candidate-3-6-5cases
candidate-5-6-5cases
```

batch summary는 아래 형식으로 생성된다.

```text
artifacts/runs/batch-{batch_sequence}-{limit}cases-summary.md
```

## Sampling 규칙

`run-mileday-smoke`는 항상 random sampling을 사용한다.

```text
all_cases = load_mileday_generation_cases(fixture)
rng = random.Random(seed)
cases = rng.sample(all_cases, k=min(limit, len(all_cases)))
```

- `--seed`를 생략하면 기본값은 `42`이다.
- 같은 fixture, 같은 limit, 같은 seed면 같은 case가 선택된다.
- 다른 case 조합을 보고 싶으면 seed를 바꾼다.

예:

```powershell
python -m harness.cli run-mileday-smoke `
  --fixture tests\fixtures\mileday\synthetic_schedule.jsonl `
  --model-id candidate-3,candidate-5 `
  --limit 5 `
  --seed 100
```

## 결과 파일 구조

예:

```text
artifacts/runs/
  candidate-3-6-5cases/
    raw/
      candidate-3__mileday-schedule__synthetic-1.txt
    parsed/
      results.jsonl
      results.pretty.json
    metrics/
      performance.jsonl
    report.md
  batch-6-5cases-summary.md
```

파일 의미:

- `raw/*.txt`: 모델의 원본 응답
- `parsed/results.jsonl`: 머신 처리용 JSONL, 한 줄에 한 결과
- `parsed/results.pretty.json`: 사람이 보기 좋은 pretty JSON 배열
- `metrics/performance.jsonl`: latency, TTFT, throughput, resource sample
- `report.md`: 모델별 개별 실행 리포트
- `batch-*-summary.md`: 다중 모델 batch 요약

## 평가 기준

MileDay smoke 평가는 아래 순서로 진행된다.

```text
Ollama 모델 응답 생성
-> raw output 저장
-> [EXPLANATION] 추출
-> fenced json 추출
-> json.loads()
-> deterministic schedule validation
-> semantic rubric 계산
-> Gemini LLM-as-Judge 평가
-> parsed 결과 저장
-> 개별 report 생성
-> batch summary 생성
```

필수 출력 구조:

~~~text
[EXPLANATION]
사용자에게 보여줄 한국어 설명

[JSON]
```json
{
  "milestones": [
    {
      "title": "string",
      "scheduled_date": "YYYY-MM-DD"
    }
  ]
}
```
~~~

주의: 위 예시를 문서 안에 넣기 위해 code fence가 중첩되어 있다. 실제 모델 응답은 `[JSON]` 아래에 fenced `json` block 하나를 포함해야 한다.

## LLM-as-Judge

case별 judge는 `harness/mileday/explanation_judge.py`의 `GeminiExplanationJudge.evaluate()`에서 수행한다.

판정 대상:

- 설명문이 한국어 사용자에게 보여줄 수 있는 품질인지
- 설명문이 JSON milestones의 제목과 날짜 흐름을 반영하는지
- 설명문과 JSON이 서로 다른 일정을 말하지 않는지

결과는 `parsed_output.explanation_judge`에 저장된다.

예:

```json
{
  "is_aligned": true,
  "score": 0.92,
  "reason": "The explanation matches the milestones.",
  "skipped": false,
  "error": null
}
```

batch summary 품질 요약은 같은 파일의 `GeminiExplanationJudge.summarize_batch_quality()`에서 수행한다.

품질 요약 prompt는 제공된 batch 집계 데이터만 근거로 사용하도록 제한한다. 출력 필드는 아래 세 가지다.

```json
{
  "overall_summary": "한국어 전체 요약",
  "risk_signals": ["위험 신호"],
  "improvement_actions": ["개선 방안"]
}
```

## 코드 구조

핵심 파일:

```text
harness/cli.py
```

- Typer CLI entrypoint
- `run-mileday-smoke`
- 단일/다중 모델 실행
- random sampling
- 자동 run id
- 개별 report와 batch summary 생성
- MileDay 출력 parser/evaluator

```text
harness/results.py
```

- raw output 저장
- `results.jsonl` 저장
- `results.pretty.json` 생성
- performance sample 저장
- resume index 관리

```text
harness/reporting.py
```

- 개별 run의 `report.md` 생성
- status, invalid/failure, metric, raw artifact reference 요약

```text
harness/mileday/constraints.py
```

- JSON shape 검증
- milestone 개수 검증
- required field 검증
- `scheduled_date` 형식과 deadline 검증
- recurrence 제약 검증

```text
harness/mileday/rubric.py
```

- deterministic validation 이후 semantic rubric 계산
- goal alignment, actionability, schedule balance 점수

```text
harness/mileday/explanation_judge.py
```

- Gemini API 기반 explanation judge
- batch quality summary judge
- Gemini structured JSON response parsing

```text
configs/models.yaml
```

- candidate 모델 id, Ollama tag, context window, quantization, license note

```text
tests/fixtures/mileday/synthetic_schedule.jsonl
```

- MileDay 일정 생성 smoke fixture

## 자주 쓰는 실행 예시

candidate-3과 candidate-5를 5건 평가:

```powershell
python -m harness.cli run-mileday-smoke `
  --fixture tests\fixtures\mileday\synthetic_schedule.jsonl `
  --model-id candidate-3,candidate-5 `
  --limit 5
```

seed를 바꿔 다른 case 조합 평가:

```powershell
python -m harness.cli run-mileday-smoke `
  --fixture tests\fixtures\mileday\synthetic_schedule.jsonl `
  --model-id candidate-3,candidate-5 `
  --limit 5 `
  --seed 2026
```

단일 모델을 수동 run id로 평가:

```powershell
python -m harness.cli run-mileday-smoke `
  --fixture tests\fixtures\mileday\synthetic_schedule.jsonl `
  --model-id candidate-3 `
  --run-id candidate-3-debug `
  --limit 5
```

## 트러블 슈팅

### `Gemini explanation judge was skipped because GEMINI_API_KEY is not configured.`

원인:

- 실행 당시 `.env`에 `GEMINI_API_KEY`가 없었다.
- 또는 과거 run 결과를 보고 있다.

확인:

```powershell
python -c "from harness.config import load_settings; s=load_settings(); print(bool(s.gemini_api_key))"
```

해결:

- `.env`에 `GEMINI_API_KEY`를 넣는다.
- 기존 결과는 자동 갱신되지 않으므로 새 run id로 다시 실행한다.

### Gemini 400 Bad Request

원인 후보:

- `GEMINI_JUDGE_MODEL`이 실제 API에서 지원되지 않는다.
- Gemini structured output schema가 API 형식과 맞지 않는다.
- API key의 프로젝트 또는 quota 정책 문제일 수 있다.

현재 구현은 `responseMimeType=application/json`과 `responseSchema`를 사용한다. 400이 발생하면 response body 일부를 `explanation_judge.error.message`에 저장한다.

### Ollama HTTP 404

원인:

- `configs/models.yaml`의 `model_tag`가 로컬 Ollama에 설치되어 있지 않다.
- 모델 tag가 잘못되었다.

확인:

```powershell
ollama list
python -m harness.cli list-models --check-installed
```

해결:

```powershell
ollama pull <model_tag>
```

또는 `configs/models.yaml`의 tag를 실제 설치된 tag로 수정한다.

### 같은 run id로 재실행했는데 결과가 바뀌지 않음

원인:

- `ResultStore.resume_index()`가 이미 완료된 case를 건너뛴다.

해결:

- 새 run id를 사용한다.
- 자동 run id를 쓰면 기존 sequence 다음 번호로 생성된다.

### `results.jsonl`이 한 줄이라 보기 어려움

정상이다. JSONL은 머신 처리용이다.

사람이 읽을 때는 아래 파일을 본다.

```text
parsed/results.pretty.json
```

### invalid가 많은 경우

주요 원인:

- `[EXPLANATION]` 또는 `[JSON]` 섹션 누락
- fenced `json` block 누락
- JSON load 실패
- required field 누락
- milestone 개수 초과/부족
- deadline 이후 날짜 생성
- weekly recurrence가 정확히 7일 간격이 아님

확인 순서:

1. `raw/*.txt`에서 모델 출력 구조 확인
2. `parsed/results.pretty.json`의 `error.message` 확인
3. `parsed_output.validation.failures` 확인
4. 필요하면 prompt 또는 fixture 제약을 조정

### batch summary에 LLM-as-Judge 전체 평가가 없음

원인:

- 이전 버전에서 생성된 과거 summary 파일이다.

해결:

- 새 batch를 실행한다.
- 또는 같은 run들의 결과를 바탕으로 summary 재생성 helper를 별도 추가해야 한다.

현재 CLI는 smoke 실행 흐름에서 batch summary를 생성한다.

## 검증 명령어

harness 전체 테스트:

```powershell
pytest tests\harness
```

관련 핵심 테스트:

```powershell
pytest tests\harness\test_cli.py
pytest tests\harness\test_results.py
pytest tests\harness\mileday\test_explanation_judge.py
pytest tests\harness\mileday\test_constraints.py
```

현재 기준으로 하네스 테스트는 `137 passed` 상태까지 확인했다.
