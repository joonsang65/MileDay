from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

from pydantic import BaseModel, Field

from harness.schemas import EvaluationError, FailureCategory, RuntimeMetrics


class RuntimeRequest(BaseModel):
    model_tag: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    system: str | None = None
    options: dict[str, object] = Field(default_factory=dict)
    timeout_seconds: int = Field(default=120, gt=0)


class RuntimeChunk(BaseModel):
    text: str = ""
    done: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeResponse(BaseModel):
    model_tag: str
    text: str
    metrics: RuntimeMetrics
    metadata: dict[str, object] = Field(default_factory=dict)
    error: EvaluationError | None = None


class RuntimeAdapter(Protocol):
    def stream(self, request: RuntimeRequest) -> Iterator[RuntimeChunk]:
        """Yield normalized streaming chunks from a runtime."""

    def generate(self, request: RuntimeRequest) -> RuntimeResponse:
        """Return a complete runtime response."""


class RuntimeAdapterError(Exception):
    def __init__(self, category: FailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message

    def to_evaluation_error(self) -> EvaluationError:
        return EvaluationError(category=self.category, message=self.message)

