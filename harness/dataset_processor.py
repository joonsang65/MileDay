from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from harness.config import BASE_DIR
from harness.dataset_registry import DatasetConfig, DatasetRegistry, load_dataset_registry
from harness.schemas import FailureCategory


LABELS = tuple("ABCDEFGHIJ")
DATASET_DIR_NAMES = {
    "kmmlu_pro": "kmmlu-pro",
    "kobalt": "kobalt-700",
    "click": "click",
    "ifeval_ko": "ifeval-ko",
}
KOBALT_CHOICE_PATTERN = re.compile(
    r"(?:^|\n)([A-J]):\s*(.*?)(?=\n[A-J]:|\Z)",
    re.DOTALL,
)


class DatasetProcessingError(ValueError):
    def __init__(self, category: FailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class ProcessedDataset(BaseModel):
    model_config = ConfigDict(frozen=True)

    dataset_key: str
    source_path: Path
    processed_path: Path
    row_count: int = Field(ge=0)


def prepare_all_datasets(
    *,
    registry: DatasetRegistry | None = None,
    registry_path: str | Path | None = None,
    sample_limit: int | None = None,
) -> list[ProcessedDataset]:
    loaded_registry = registry or (
        load_dataset_registry(registry_path)
        if registry_path is not None
        else load_dataset_registry()
    )
    return [
        prepare_dataset(dataset_key, dataset, sample_limit=sample_limit)
        for dataset_key, dataset in loaded_registry.datasets.items()
    ]


def prepare_dataset(
    dataset_key: str,
    dataset: DatasetConfig,
    *,
    sample_limit: int | None = None,
) -> ProcessedDataset:
    if dataset_key == "kmmlu_pro":
        return _prepare_kmmlu_pro(dataset_key, dataset, sample_limit=sample_limit)
    if dataset_key == "kobalt":
        return _prepare_kobalt(dataset_key, dataset, sample_limit=sample_limit)
    if dataset_key == "click":
        return _prepare_click(dataset_key, dataset, sample_limit=sample_limit)
    if dataset_key == "ifeval_ko":
        return _prepare_ifeval_ko(dataset_key, dataset, sample_limit=sample_limit)
    raise DatasetProcessingError(
        FailureCategory.CONFIG_ERROR,
        f"Unsupported dataset key: {dataset_key}",
    )


def _prepare_kmmlu_pro(
    dataset_key: str,
    dataset: DatasetConfig,
    *,
    sample_limit: int | None,
) -> ProcessedDataset:
    source_file = _revision_dir(dataset_key, dataset) / "source" / "data" / "kmmlu_pro.jsonl"
    rows = _read_jsonl(source_file)

    processed_rows = []
    for index, row in enumerate(_limit(rows, sample_limit), start=1):
        choices = _text_list(row, dataset.fields["choices"], index)
        answer = _answer_from_one_based_value(row[dataset.fields["answer"]], len(choices), index)
        processed_rows.append(
            _mcq_row(
                case_id=f"kmmlu-pro-{index}",
                question=_required_text(row, dataset.fields["question"], index),
                choices=choices,
                answer=answer,
                category=_optional_text(row, dataset.fields.get("subject")),
                metadata={
                    "score": row.get(dataset.fields.get("score", "")),
                    "license_name": row.get(dataset.fields.get("license_name", "")),
                    "year": row.get(dataset.fields.get("year", "")),
                    "round": row.get(dataset.fields.get("round", "")),
                    "session": row.get(dataset.fields.get("session", "")),
                },
            )
        )
    return _write_processed(dataset_key, dataset, source_file, processed_rows)


def _prepare_kobalt(
    dataset_key: str,
    dataset: DatasetConfig,
    *,
    sample_limit: int | None,
) -> ProcessedDataset:
    source_file = _revision_dir(dataset_key, dataset) / "source" / "data" / "train.jsonl"
    rows = _read_json_array(source_file)

    processed_rows = []
    for index, row in enumerate(_limit(rows, sample_limit), start=1):
        question_text = _required_text(row, dataset.fields["question"], index)
        choices = _parse_labeled_choices(question_text, index)
        processed_rows.append(
            _mcq_row(
                case_id=_required_text(row, dataset.fields["id"], index),
                question=question_text,
                choices=[choices[label] for label in sorted(choices)],
                answer=_required_text(row, dataset.fields["answer"], index).upper(),
                category=_optional_text(row, dataset.fields.get("category")),
                metadata={
                    "subcategory": row.get(dataset.fields.get("subcategory", "")),
                    "difficulty": row.get(dataset.fields.get("difficulty", "")),
                    "sampling_flag": row.get(dataset.fields.get("sampling_flag", "")),
                },
            )
        )
    return _write_processed(dataset_key, dataset, source_file, processed_rows)


def _prepare_click(
    dataset_key: str,
    dataset: DatasetConfig,
    *,
    sample_limit: int | None,
) -> ProcessedDataset:
    source_dir = _revision_dir(dataset_key, dataset) / "source" / "Dataset"
    source_files = sorted(source_dir.rglob("*.json"))
    if not source_files:
        raise DatasetProcessingError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"CLIcK source files not found under {source_dir}",
        )

    processed_rows: list[dict[str, Any]] = []
    row_index = 0
    for source_file in source_files:
        category_parts = source_file.relative_to(source_dir).parts
        category = category_parts[0] if category_parts else None
        subcategory = category_parts[1] if len(category_parts) > 1 else None
        for row in _read_json_array(source_file):
            row_index += 1
            choices = _text_list(row, dataset.fields["choices"], row_index)
            answer = _answer_from_choice_text(
                _required_text(row, dataset.fields["answer"], row_index),
                choices,
                row_index,
            )
            context = _optional_text(row, dataset.fields.get("context"))
            question = _required_text(row, dataset.fields["question"], row_index)
            if context:
                question = f"Context:\n{context}\n\nQuestion:\n{question}"
            processed_rows.append(
                _mcq_row(
                    case_id=_required_text(row, dataset.fields["id"], row_index),
                    question=question,
                    choices=choices,
                    answer=answer,
                    category=category,
                    metadata={
                        "subcategory": subcategory,
                        "source_file": str(source_file.relative_to(source_dir)),
                    },
                )
            )
            if sample_limit is not None and len(processed_rows) >= sample_limit:
                return _write_processed(dataset_key, dataset, source_dir, processed_rows)
    return _write_processed(dataset_key, dataset, source_dir, processed_rows)


def _prepare_ifeval_ko(
    dataset_key: str,
    dataset: DatasetConfig,
    *,
    sample_limit: int | None,
) -> ProcessedDataset:
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise DatasetProcessingError(
            FailureCategory.EXTERNAL_DEPENDENCY,
            "pyarrow is required to process IFEval-Ko parquet files.",
        ) from exc

    source_file = (
        _revision_dir(dataset_key, dataset)
        / "source"
        / "data"
        / "train-00000-of-00001.parquet"
    )
    if not source_file.exists():
        raise DatasetProcessingError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"Source file not found: {source_file}",
        )
    loaded = pq.read_table(source_file).to_pylist()
    processed_rows = []
    for index, row in enumerate(_limit((dict(item) for item in loaded), sample_limit), start=1):
        processed_rows.append(
            {
                "benchmark_id": "ifeval-ko",
                "dataset_id": dataset.dataset_id,
                "case_id": str(row[dataset.fields["id"]]),
                "prompt": row[dataset.fields["prompt"]],
                "instruction_ids": row[dataset.fields["instruction_ids"]],
                "kwargs": row[dataset.fields["kwargs"]],
            }
        )
    return _write_processed(dataset_key, dataset, source_file, processed_rows)


def _revision_dir(dataset_key: str, dataset: DatasetConfig) -> Path:
    dirname = DATASET_DIR_NAMES[dataset_key]
    return BASE_DIR / "datasets" / dirname / dataset.revision


def _processed_file(dataset_key: str, dataset: DatasetConfig) -> Path:
    return _revision_dir(dataset_key, dataset) / "processed" / "data.jsonl"


def _write_processed(
    dataset_key: str,
    dataset: DatasetConfig,
    source_path: Path,
    rows: list[dict[str, Any]],
) -> ProcessedDataset:
    if not rows:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"No rows produced for {dataset_key}",
        )
    output_path = _processed_file(dataset_key, dataset)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    return ProcessedDataset(
        dataset_key=dataset_key,
        source_path=source_path,
        processed_path=output_path,
        row_count=len(rows),
    )


def _mcq_row(
    *,
    case_id: str,
    question: str,
    choices: list[str],
    answer: str,
    category: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    if len(choices) < 2 or len(choices) > len(LABELS):
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"MCQ choice count must be 2-{len(LABELS)} for case {case_id}.",
        )
    labeled_choices = {
        f"choice_{LABELS[index].lower()}": choice
        for index, choice in enumerate(choices)
    }
    answer_label = answer.strip().upper()
    if answer_label not in LABELS[: len(choices)]:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Answer {answer!r} does not match available choices for case {case_id}.",
        )
    return {
        "case_id": case_id,
        "question": question,
        **labeled_choices,
        "answer": answer_label,
        "category": category,
        "metadata": {
            key: value
            for key, value in metadata.items()
            if value not in (None, "")
        },
    }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise DatasetProcessingError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"Source file not found: {path}",
        )
    rows: list[dict[str, Any]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise DatasetProcessingError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"Invalid JSONL at {path}:{line_number}: {exc.msg}",
            ) from exc
        if not isinstance(row, dict):
            raise DatasetProcessingError(
                FailureCategory.DATASET_SCHEMA_CHANGED,
                f"JSONL row must be an object at {path}:{line_number}",
            )
        rows.append(row)
    return rows


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise DatasetProcessingError(
            FailureCategory.DATASET_UNAVAILABLE,
            f"Source file not found: {path}",
        )
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Invalid JSON at {path}: {exc.msg}",
        ) from exc
    if not isinstance(raw, list) or not all(isinstance(row, dict) for row in raw):
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Expected JSON array of objects: {path}",
        )
    return raw


def _limit(rows: Iterable[dict[str, Any]], sample_limit: int | None) -> Iterable[dict[str, Any]]:
    if sample_limit is None:
        yield from rows
        return
    if sample_limit <= 0:
        raise DatasetProcessingError(
            FailureCategory.CONFIG_ERROR,
            "sample_limit must be positive when provided.",
        )
    for index, row in enumerate(rows):
        if index >= sample_limit:
            return
        yield row


def _required_text(row: dict[str, Any], field_name: str, row_number: int) -> str:
    if field_name not in row:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} is missing field {field_name!r}.",
        )
    value = row[field_name]
    if value is None or str(value).strip() == "":
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} has blank field {field_name!r}.",
        )
    return str(value).strip()


def _optional_text(row: dict[str, Any], field_name: str | None) -> str | None:
    if field_name is None or field_name not in row:
        return None
    value = row[field_name]
    text = str(value).strip() if value is not None else ""
    return text or None


def _text_list(row: dict[str, Any], field_name: str, row_number: int) -> list[str]:
    if field_name not in row:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} is missing list field {field_name!r}.",
        )
    value = row[field_name]
    if not isinstance(value, list):
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} field {field_name!r} must be a list.",
        )
    choices = [str(item).strip() for item in value if str(item).strip()]
    if len(choices) != len(value):
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} field {field_name!r} contains blank choices.",
        )
    return choices


def _answer_from_one_based_value(value: Any, choice_count: int, row_number: int) -> str:
    text = str(value).strip().upper()
    if text in LABELS:
        return text
    try:
        numeric_answer = int(text)
    except ValueError as exc:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} answer {value!r} is not a label or 1-based index.",
        ) from exc
    if numeric_answer < 1 or numeric_answer > choice_count:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} answer index {numeric_answer} is out of range.",
        )
    return LABELS[numeric_answer - 1]


def _answer_from_choice_text(answer_text: str, choices: list[str], row_number: int) -> str:
    normalized_answer = answer_text.strip()
    for index, choice in enumerate(choices):
        if choice.strip() == normalized_answer:
            return LABELS[index]
    if normalized_answer.upper() in LABELS[: len(choices)]:
        return normalized_answer.upper()
    raise DatasetProcessingError(
        FailureCategory.DATASET_SCHEMA_CHANGED,
        f"Row {row_number} answer does not match any choice text.",
    )


def _parse_labeled_choices(question_text: str, row_number: int) -> dict[str, str]:
    choices = {
        match.group(1): match.group(2).strip()
        for match in KOBALT_CHOICE_PATTERN.finditer(question_text)
    }
    if len(choices) < 2:
        raise DatasetProcessingError(
            FailureCategory.DATASET_SCHEMA_CHANGED,
            f"Row {row_number} does not contain parseable A-J choices.",
        )
    return choices
