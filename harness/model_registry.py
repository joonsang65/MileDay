from __future__ import annotations

import subprocess
from pathlib import Path

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from harness.config import BASE_DIR


DEFAULT_MODEL_REGISTRY_PATH = BASE_DIR / "configs" / "models.yaml"


class ModelCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    runtime: str = Field(min_length=1)
    model_tag: str = Field(min_length=1)
    context_window: int = Field(gt=0)
    quantization: str = Field(min_length=1)
    license_note: str = Field(min_length=1)

    @field_validator("id", "provider", "runtime", "model_tag", "quantization", "license_note")
    @classmethod
    def _strip_non_empty(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must not be blank")
        return stripped


class ModelRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    models: list[ModelCandidate] = Field(min_length=5, max_length=5)

    @model_validator(mode="after")
    def _validate_unique_ids_and_tags(self) -> ModelRegistry:
        ids = [model.id for model in self.models]
        if len(ids) != len(set(ids)):
            raise ValueError("model ids must be unique")

        tags = [model.model_tag for model in self.models]
        if len(tags) != len(set(tags)):
            raise ValueError("model tags must be unique")
        return self


class ModelAvailability(BaseModel):
    model_id: str
    model_tag: str
    installed: bool


def load_model_registry(path: str | Path = DEFAULT_MODEL_REGISTRY_PATH) -> ModelRegistry:
    registry_path = Path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Model registry file not found: {registry_path}")

    raw = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}

    try:
        return ModelRegistry.model_validate(raw)
    except ValidationError:
        raise


def parse_ollama_list(output: str) -> set[str]:
    tags: set[str] = set()
    for line in output.splitlines():
        stripped = line.strip()
        if not stripped or stripped.lower().startswith("name "):
            continue
        tags.add(stripped.split()[0])
    return tags


def get_installed_ollama_tags(timeout_seconds: int = 10) -> set[str]:
    completed = subprocess.run(
        ["ollama", "list"],
        capture_output=True,
        check=True,
        encoding="utf-8",
        timeout=timeout_seconds,
    )
    return parse_ollama_list(completed.stdout)


def check_model_availability(
    registry: ModelRegistry,
    installed_tags: set[str] | None = None,
) -> list[ModelAvailability]:
    tags = installed_tags if installed_tags is not None else get_installed_ollama_tags()
    return [
        ModelAvailability(
            model_id=model.id,
            model_tag=model.model_tag,
            installed=model.model_tag in tags,
        )
        for model in registry.models
    ]

