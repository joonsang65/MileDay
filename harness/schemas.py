from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ResultStatus(StrEnum):
    PASSED = "passed"
    FAILED = "failed"
    INVALID = "invalid"
    SKIPPED = "skipped"


class FailureCategory(StrEnum):
    CODE_ERROR = "CODE_ERROR"
    TEST_FAILURE = "TEST_FAILURE"
    CONFIG_ERROR = "CONFIG_ERROR"
    MODEL_NOT_INSTALLED = "MODEL_NOT_INSTALLED"
    OLLAMA_UNAVAILABLE = "OLLAMA_UNAVAILABLE"
    DATASET_UNAVAILABLE = "DATASET_UNAVAILABLE"
    DATASET_SCHEMA_CHANGED = "DATASET_SCHEMA_CHANGED"
    PARSER_ERROR = "PARSER_ERROR"
    TIMEOUT = "TIMEOUT"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    EXTERNAL_DEPENDENCY = "EXTERNAL_DEPENDENCY"
    NOT_EXECUTED = "NOT_EXECUTED"


class RuntimeMetrics(BaseModel):
    ttft_ms: int | None = Field(default=None, ge=0)
    latency_ms: int | None = Field(default=None, ge=0)
    tokens_per_second: float | None = Field(default=None, ge=0)


class EvaluationError(BaseModel):
    category: FailureCategory
    message: str


class RequestResult(BaseModel):
    run_id: str
    model_id: str
    dataset_id: str
    case_id: str
    status: ResultStatus
    raw_output_path: Path | None = None
    parsed_output: dict[str, Any] = Field(default_factory=dict)
    metrics: RuntimeMetrics = Field(default_factory=RuntimeMetrics)
    error: EvaluationError | None = None

