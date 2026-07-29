from __future__ import annotations

import csv
import importlib.util
import json
import sys
from collections import defaultdict
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from harness.config import BASE_DIR
from harness.schemas import FailureCategory


BENCHMARK_ID = "ifeval-ko"
DEFAULT_DATASET_ID = "ifeval-ko-local"
OFFICIAL_EVALUATOR_MODULE = "lm_eval.tasks.ifeval_ko.utils"
DEFAULT_OFFICIAL_SOURCE_ROOT = (
    BASE_DIR
    / "datasets"
    / "ifeval-ko"
    / "54199e3801116897697babf341865741dcd06fc8"
    / "source"
)


class IFEvalKoDatasetError(ValueError):
    def __init__(self, category: FailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class IFEvalKoFieldMapping(BaseModel):
    model_config = ConfigDict(frozen=True)

    case_id: str = "case_id"
    prompt: str = "prompt"
    instruction_ids: str = "instruction_ids"
    kwargs: str = "kwargs"
    benchmark_id: str | None = "benchmark_id"
    dataset_id: str | None = "dataset_id"
    metadata: dict[str, str] = Field(default_factory=dict)

    @field_validator("case_id", "prompt", "instruction_ids", "kwargs")
    @classmethod
    def _validate_required_field_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("mapped field names must not be blank")
        return stripped


class OfficialEvaluatorStatus(BaseModel):
    available: bool
    module: str = OFFICIAL_EVALUATOR_MODULE
    source_root: Path | None = None
    category: FailureCategory | None = None
    message: str | None = None


class IFEvalKoCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str = BENCHMARK_ID
    dataset_id: str = DEFAULT_DATASET_ID
    case_id: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    instruction_ids: list[str] = Field(min_length=1)
    kwargs: list[dict[str, Any]]
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("instruction_ids")
    @classmethod
    def _validate_instruction_ids(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("instruction_ids must not contain blank values")
        return normalized

    @model_validator(mode="after")
    def _validate_kwargs_length(self) -> IFEvalKoCase:
        if len(self.kwargs) != len(self.instruction_ids):
            raise ValueError("kwargs length must match instruction_ids length")
        return self

    def build_prompt(self) -> str:
        return self.prompt

    def to_official_doc(self) -> dict[str, Any]:
        return {
            "key": int(self.case_id) if self.case_id.isdigit() else self.case_id,
            "instruction_id_list": self.instruction_ids,
            "prompt": self.prompt,
            "kwargs": self.kwargs,
        }

    def score_response(
        self,
        raw_output: str,
        *,
        source_root: str | Path | None = None,
    ) -> IFEvalKoCaseResult:
        return score_ifeval_ko_response(self, raw_output, source_root=source_root)


class IFEvalKoInstructionResult(BaseModel):
    instruction_id: str
    strict_followed: bool
    loose_followed: bool


class IFEvalKoCaseResult(BaseModel):
    benchmark_id: str
    dataset_id: str
    case_id: str
    raw_output: str
    instruction_results: list[IFEvalKoInstructionResult]
    prompt_level_strict: bool
    prompt_level_loose: bool
    is_invalid: bool = False
    invalid_reason: str | None = None


class IFEvalKoAggregate(BaseModel):
    total: int
    invalid: int
    prompt_level_strict_accuracy: float
    prompt_level_loose_accuracy: float
    inst_level_strict_accuracy: float
    inst_level_loose_accuracy: float
    invalid_rate: float


class IFEvalKoAggregateReport(BaseModel):
    overall: IFEvalKoAggregate
    by_benchmark: dict[str, IFEvalKoAggregate]


def check_official_evaluator_available(
    source_root: str | Path | None = None,
) -> OfficialEvaluatorStatus:
    if importlib.util.find_spec("lm_eval") is None:
        return OfficialEvaluatorStatus(
            available=False,
            category=FailureCategory.EXTERNAL_DEPENDENCY,
            message="lm_eval is required for the official IFEval-Ko evaluator.",
        )
    resolved_source_root = _resolve_official_source_root(source_root)
    if resolved_source_root is not None:
        _attach_official_task_source(resolved_source_root)
    if _find_official_evaluator_spec() is None:
        return OfficialEvaluatorStatus(
            available=False,
            category=FailureCategory.EXTERNAL_DEPENDENCY,
            message=f"{OFFICIAL_EVALUATOR_MODULE} is required for official evaluation.",
        )
    return OfficialEvaluatorStatus(available=True, source_root=resolved_source_root)


def load_ifeval_ko_cases(
    source_path: str | Path,
    *,
    dataset_id: str = DEFAULT_DATASET_ID,
    mapping: IFEvalKoFieldMapping | None = None,
) -> list[IFEvalKoCase]:
    path = Path(source_path)
    field_mapping = mapping or IFEvalKoFieldMapping()
    rows = _load_rows(path)
    return [
        _normalize_row(row, dataset_id=dataset_id, mapping=field_mapping, row_number=index)
        for index, row in enumerate(rows, start=1)
    ]


def score_ifeval_ko_responses(
    cases: Iterable[IFEvalKoCase],
    raw_outputs_by_case_id: dict[str, str],
    *,
    source_root: str | Path | None = None,
) -> IFEvalKoAggregateReport:
    results = [
        score_ifeval_ko_response(
            case,
            raw_outputs_by_case_id.get(case.case_id, ""),
            source_root=source_root,
        )
        for case in cases
    ]
    return aggregate_ifeval_ko_results(results)


def score_ifeval_ko_response(
    case: IFEvalKoCase,
    raw_output: str,
    *,
    source_root: str | Path | None = None,
) -> IFEvalKoCaseResult:
    process_results = _load_official_process_results(source_root=source_root)
    try:
        official_result = process_results(case.to_official_doc(), [raw_output])
    except (KeyError, TypeError, ValueError) as exc:
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Official IFEval-Ko evaluator rejected case {case.case_id}: {exc}",
        ) from exc
    instruction_results = _instruction_results_from_official(
        case.instruction_ids,
        official_result,
    )
    return IFEvalKoCaseResult(
        benchmark_id=case.benchmark_id,
        dataset_id=case.dataset_id,
        case_id=case.case_id,
        raw_output=raw_output,
        instruction_results=instruction_results,
        prompt_level_strict=bool(official_result["prompt_level_strict_acc"]),
        prompt_level_loose=bool(official_result["prompt_level_loose_acc"]),
    )


def aggregate_ifeval_ko_results(
    results: Iterable[IFEvalKoCaseResult],
) -> IFEvalKoAggregateReport:
    items = list(results)
    by_benchmark: dict[str, list[IFEvalKoCaseResult]] = defaultdict(list)
    for item in items:
        by_benchmark[item.benchmark_id].append(item)
    return IFEvalKoAggregateReport(
        overall=_aggregate(items),
        by_benchmark={
            benchmark_id: _aggregate(group)
            for benchmark_id, group in sorted(by_benchmark.items())
        },
    )


def _load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.exists() or not path.is_file():
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"IFEval-Ko dataset file does not exist or is not readable: {path}",
        )
    if path.suffix.lower() == ".jsonl":
        return _load_jsonl(path)
    if path.suffix.lower() == ".csv":
        return _load_csv(path)
    raise IFEvalKoDatasetError(
        FailureCategory.DATASET_UNAVAILABLE,
        f"Unsupported IFEval-Ko dataset file extension: {path.suffix}",
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise IFEvalKoDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"Invalid JSONL at line {line_number}: {exc.msg}",
            ) from exc
        if not isinstance(row, dict):
            raise IFEvalKoDatasetError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"JSONL line {line_number} must be an object.",
            )
        rows.append(row)
    return rows


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def _normalize_row(
    row: dict[str, Any],
    *,
    dataset_id: str,
    mapping: IFEvalKoFieldMapping,
    row_number: int,
) -> IFEvalKoCase:
    _reject_unsupported_shape(row, mapping=mapping, row_number=row_number)
    mapped_dataset_id = (
        _optional_text(row, mapping.dataset_id)
        if mapping.dataset_id is not None
        else None
    )
    benchmark_id = (
        _optional_text(row, mapping.benchmark_id)
        if mapping.benchmark_id is not None
        else None
    )
    metadata = {
        name: row[field_name]
        for name, field_name in mapping.metadata.items()
        if field_name in row and row[field_name] not in (None, "")
    }

    try:
        return IFEvalKoCase(
            benchmark_id=benchmark_id or BENCHMARK_ID,
            dataset_id=mapped_dataset_id or dataset_id,
            case_id=_required_text(row, mapping.case_id, row_number),
            prompt=_required_text(row, mapping.prompt, row_number),
            instruction_ids=_required_list(row, mapping.instruction_ids, row_number, str),
            kwargs=_required_kwargs(row, mapping.kwargs, row_number),
            metadata=metadata,
        )
    except ValueError as exc:
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Invalid IFEval-Ko row {row_number}: {exc}",
        ) from exc


def _reject_unsupported_shape(
    row: dict[str, Any], *, mapping: IFEvalKoFieldMapping, row_number: int
) -> None:
    required_fields = [mapping.case_id, mapping.prompt, mapping.instruction_ids, mapping.kwargs]
    missing_fields = [field_name for field_name in required_fields if field_name not in row]
    if missing_fields:
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            "IFEval-Ko row "
            f"{row_number} is not a supported mapped instruction-following row; "
            f"missing mapped fields: {', '.join(missing_fields)}.",
        )


def _required_text(row: dict[str, Any], field_name: str, row_number: int) -> str:
    value = row[field_name]
    if value is None or str(value).strip() == "":
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"IFEval-Ko row {row_number} has blank mapped field '{field_name}'.",
        )
    return str(value).strip()


def _optional_text(row: dict[str, Any], field_name: str | None) -> str | None:
    if field_name is None or field_name not in row:
        return None
    value = row[field_name]
    text = str(value).strip() if value is not None else ""
    return text or None


def _required_list(
    row: dict[str, Any],
    field_name: str,
    row_number: int,
    item_type: type,
) -> list[Any]:
    value = _decode_jsonish(row[field_name], field_name=field_name, row_number=row_number)
    if not isinstance(value, list) or not value:
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"IFEval-Ko row {row_number} field '{field_name}' must be a non-empty list.",
        )
    if not all(isinstance(item, item_type) for item in value):
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"IFEval-Ko row {row_number} field '{field_name}' has invalid item types.",
        )
    return value


def _required_kwargs(row: dict[str, Any], field_name: str, row_number: int) -> list[dict[str, Any]]:
    value = _decode_jsonish(row[field_name], field_name=field_name, row_number=row_number)
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"IFEval-Ko row {row_number} field '{field_name}' must be a list of objects.",
        )
    return value


def _decode_jsonish(value: Any, *, field_name: str, row_number: int) -> Any:
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if not stripped:
        return value
    if stripped[0] not in "[{":
        return value
    try:
        return json.loads(stripped)
    except json.JSONDecodeError as exc:
        raise IFEvalKoDatasetError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"IFEval-Ko row {row_number} field '{field_name}' contains invalid JSON.",
        ) from exc


def _load_official_process_results(
    *,
    source_root: str | Path | None,
) -> Callable[[dict[str, Any], list[str]], dict[str, Any]]:
    status = check_official_evaluator_available(source_root=source_root)
    if not status.available:
        raise IFEvalKoDatasetError(
            status.category or FailureCategory.EXTERNAL_DEPENDENCY,
            status.message or "Official IFEval-Ko evaluator is unavailable.",
        )
    module = __import__(OFFICIAL_EVALUATOR_MODULE, fromlist=["process_results"])
    process_results = getattr(module, "process_results", None)
    if process_results is None:
        raise IFEvalKoDatasetError(
            FailureCategory.EXTERNAL_DEPENDENCY,
            f"{OFFICIAL_EVALUATOR_MODULE}.process_results is not available.",
        )
    return process_results


def _resolve_official_source_root(source_root: str | Path | None) -> Path | None:
    if source_root is not None:
        return Path(source_root)
    if _find_official_evaluator_spec() is not None:
        return None
    if DEFAULT_OFFICIAL_SOURCE_ROOT.exists():
        return DEFAULT_OFFICIAL_SOURCE_ROOT
    return None


def _attach_official_task_source(source_root: Path) -> None:
    task_dir = source_root / "ifeval_ko"
    if not task_dir.exists():
        return
    import lm_eval.tasks

    source_text = str(source_root.resolve())
    if source_text not in lm_eval.tasks.__path__:
        lm_eval.tasks.__path__.append(source_text)
    for module_name in tuple(sys.modules):
        if module_name.startswith("lm_eval.tasks.ifeval_ko"):
            sys.modules.pop(module_name)


def _find_official_evaluator_spec():
    try:
        return importlib.util.find_spec(OFFICIAL_EVALUATOR_MODULE)
    except ModuleNotFoundError:
        return None


def _instruction_results_from_official(
    instruction_ids: list[str],
    official_result: dict[str, Any],
) -> list[IFEvalKoInstructionResult]:
    strict_values = _required_bool_list(
        official_result,
        "inst_level_strict_acc",
        expected_length=len(instruction_ids),
    )
    loose_values = _required_bool_list(
        official_result,
        "inst_level_loose_acc",
        expected_length=len(instruction_ids),
    )
    return [
        IFEvalKoInstructionResult(
            instruction_id=instruction_id,
            strict_followed=strict,
            loose_followed=loose,
        )
        for instruction_id, strict, loose in zip(
            instruction_ids,
            strict_values,
            loose_values,
            strict=True,
        )
    ]


def _required_bool_list(
    official_result: dict[str, Any],
    key: str,
    *,
    expected_length: int,
) -> list[bool]:
    value = official_result.get(key)
    if not isinstance(value, list) or len(value) != expected_length:
        raise IFEvalKoDatasetError(
            FailureCategory.PARSER_ERROR,
            f"Official IFEval-Ko result field {key!r} is invalid.",
        )
    return [bool(item) for item in value]


def _aggregate(results: list[IFEvalKoCaseResult]) -> IFEvalKoAggregate:
    total = len(results)
    invalid = sum(1 for result in results if result.is_invalid)
    instruction_results = [
        instruction
        for result in results
        if not result.is_invalid
        for instruction in result.instruction_results
    ]
    return IFEvalKoAggregate(
        total=total,
        invalid=invalid,
        prompt_level_strict_accuracy=(
            sum(1 for result in results if result.prompt_level_strict) / total
            if total
            else 0.0
        ),
        prompt_level_loose_accuracy=(
            sum(1 for result in results if result.prompt_level_loose) / total
            if total
            else 0.0
        ),
        inst_level_strict_accuracy=(
            sum(1 for result in instruction_results if result.strict_followed)
            / len(instruction_results)
            if instruction_results
            else 0.0
        ),
        inst_level_loose_accuracy=(
            sum(1 for result in instruction_results if result.loose_followed)
            / len(instruction_results)
            if instruction_results
            else 0.0
        ),
        invalid_rate=invalid / total if total else 0.0,
    )
