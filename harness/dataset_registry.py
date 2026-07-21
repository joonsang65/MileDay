from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from harness.config import BASE_DIR


DEFAULT_DATASET_REGISTRY_PATH = BASE_DIR / "configs" / "datasets.yaml"


class DatasetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    dataset_id: str = Field(min_length=1)
    source_url: str = Field(min_length=1)
    official_repository: str = Field(min_length=1)
    revision: str = Field(min_length=1)
    config: str = Field(min_length=1)
    split: str = Field(min_length=1)
    license: str = Field(min_length=1)
    commercial_use_verified: bool
    fields: dict[str, str] = Field(min_length=1)

    @field_validator(
        "dataset_id",
        "source_url",
        "official_repository",
        "revision",
        "config",
        "split",
        "license",
    )
    @classmethod
    def _strip_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("field must not be blank")
        return stripped

    @field_validator("fields")
    @classmethod
    def _validate_fields(cls, value: dict[str, str]) -> dict[str, str]:
        normalized: dict[str, str] = {}
        for key, field_name in value.items():
            stripped_key = key.strip()
            stripped_field = field_name.strip()
            if not stripped_key or not stripped_field:
                raise ValueError("field mapping keys and values must not be blank")
            normalized[stripped_key] = stripped_field
        return normalized


class DatasetRegistry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    datasets: dict[str, DatasetConfig] = Field(min_length=1)


def load_dataset_registry(
    path: str | Path = DEFAULT_DATASET_REGISTRY_PATH,
) -> DatasetRegistry:
    registry_path = Path(path)
    if not registry_path.exists():
        raise FileNotFoundError(f"Dataset registry file not found: {registry_path}")

    raw: Any = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    if raw is None:
        raw = {}

    try:
        return DatasetRegistry.model_validate(raw)
    except ValidationError:
        raise
