from __future__ import annotations

import json
from functools import lru_cache
from os import getenv
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator


BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / getenv("HARNESS_ENV_FILE", ".env"))


class HarnessSettings(BaseModel):
    """Configuration shared by offline harness commands."""

    model_config = ConfigDict(extra="forbid")

    project_root: Path = Field(default=BASE_DIR)
    artifacts_dir: Path = Field(default=Path("artifacts"))
    runs_dir: Path = Field(default=Path("artifacts") / "runs")
    datasets_dir: Path = Field(default=Path("datasets"))
    default_timeout_seconds: int = Field(default=120, ge=1)
    ollama_base_url: str = Field(default="http://localhost:11434")

    @field_validator("project_root", "artifacts_dir", "runs_dir", "datasets_dir", mode="before")
    @classmethod
    def _coerce_path(cls, value: str | Path) -> Path:
        return Path(value)

    def model_post_init(self, __context: object) -> None:
        self.project_root = self.project_root.resolve()
        self.artifacts_dir = self._resolve_from_root(self.artifacts_dir)
        self.runs_dir = self._resolve_from_root(self.runs_dir)
        self.datasets_dir = self._resolve_from_root(self.datasets_dir)

    def _resolve_from_root(self, path: Path) -> Path:
        return path if path.is_absolute() else self.project_root / path


def _settings_from_env() -> dict[str, Any]:
    mapping = {
        "artifacts_dir": getenv("HARNESS_ARTIFACTS_DIR"),
        "runs_dir": getenv("HARNESS_RUNS_DIR"),
        "datasets_dir": getenv("HARNESS_DATASETS_DIR"),
        "default_timeout_seconds": getenv("HARNESS_DEFAULT_TIMEOUT_SECONDS"),
        "ollama_base_url": getenv("OLLAMA_BASE_URL"),
    }
    return {key: value for key, value in mapping.items() if value not in (None, "")}


def load_settings(config_path: str | Path | None = None) -> HarnessSettings:
    """Load harness settings from defaults, optional JSON config, and env overrides."""

    data: dict[str, Any] = {}
    if config_path is not None:
        path = Path(config_path)
        if not path.exists():
            raise FileNotFoundError(f"Harness config file not found: {path}")
        if path.suffix.lower() != ".json":
            raise ValueError("Harness config files must use .json for EVAL-001.")
        data.update(json.loads(path.read_text(encoding="utf-8")))

    data.update(_settings_from_env())
    try:
        return HarnessSettings(**data)
    except ValidationError:
        raise


@lru_cache
def get_settings() -> HarnessSettings:
    return load_settings()

