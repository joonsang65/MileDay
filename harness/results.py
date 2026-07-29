from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from harness.performance.monitor import PerformanceSample
from harness.schemas import FailureCategory, RequestResult


INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\s]+')


class ResultStoreError(ValueError):
    def __init__(self, category: FailureCategory, message: str) -> None:
        super().__init__(message)
        self.category = category
        self.message = message


class ResultStore:
    def __init__(self, runs_dir: str | Path = Path("artifacts") / "runs") -> None:
        self.runs_dir = Path(runs_dir)

    def run_dir(self, run_id: str) -> Path:
        return self.runs_dir / _safe_part(run_id)

    def write_config_snapshot(self, run_id: str, config: dict[str, Any]) -> Path:
        path = self.run_dir(run_id) / "config.snapshot.yaml"
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists():
            return path
        path.write_text(_to_simple_yaml(config), encoding="utf-8", newline="\n")
        return path

    def raw_output_path(self, run_id: str, model_id: str, dataset_id: str, case_id: str) -> Path:
        filename = "__".join(_safe_part(part) for part in (model_id, dataset_id, case_id))
        return self.run_dir(run_id) / "raw" / f"{filename}.txt"

    def write_raw_output(
        self,
        run_id: str,
        model_id: str,
        dataset_id: str,
        case_id: str,
        raw_output: str,
    ) -> Path:
        path = self.raw_output_path(run_id, model_id, dataset_id, case_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw_output, encoding="utf-8", newline="\n")
        return path

    def append_request_result(self, result: RequestResult) -> Path:
        if result.raw_output_path is not None and not Path(result.raw_output_path).exists():
            raise ResultStoreError(
                FailureCategory.CODE_ERROR,
                f"Request result references missing raw output: {result.raw_output_path}",
            )
        path = self.run_dir(result.run_id) / "parsed" / "results.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as file:
            file.write(json.dumps(result.model_dump(mode="json"), sort_keys=True) + "\n")
        self.write_pretty_request_results(result.run_id)
        return path

    def write_pretty_request_results(self, run_id: str) -> Path:
        path = self.run_dir(run_id) / "parsed" / "results.pretty.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        payload = [result.model_dump(mode="json") for result in self.load_request_results(run_id)]
        path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        return path

    def store_request_result(
        self,
        result: RequestResult,
        *,
        raw_output: str | None = None,
    ) -> RequestResult:
        stored = result
        if raw_output is not None:
            raw_path = self.write_raw_output(
                result.run_id,
                result.model_id,
                result.dataset_id,
                result.case_id,
                raw_output,
            )
            stored = result.model_copy(update={"raw_output_path": raw_path})
        self.append_request_result(stored)
        return stored

    def append_performance_samples(
        self,
        run_id: str,
        samples: list[PerformanceSample | dict[str, Any]],
        *,
        phase: str | None = None,
    ) -> Path:
        path = self.run_dir(run_id) / "metrics" / "performance.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8", newline="\n") as file:
            for sample in samples:
                payload = sample.model_dump(mode="json") if isinstance(sample, PerformanceSample) else dict(sample)
                if phase is not None:
                    payload["phase"] = phase
                file.write(json.dumps(payload, sort_keys=True) + "\n")
        return path

    def load_request_results(self, run_id: str) -> list[RequestResult]:
        path = self.run_dir(run_id) / "parsed" / "results.jsonl"
        if not path.exists():
            return []
        results: list[RequestResult] = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            if not line.strip():
                continue
            try:
                results.append(RequestResult.model_validate_json(line))
            except ValueError as exc:
                raise ResultStoreError(
                    FailureCategory.PARSER_ERROR,
                    f"Invalid stored request result at line {line_number}: {exc}",
                ) from exc
        return results

    def resume_index(self, run_id: str) -> dict[tuple[str, str, str, str], RequestResult]:
        return {
            (result.run_id, result.model_id, result.dataset_id, result.case_id): result
            for result in self.load_request_results(run_id)
        }

    def is_completed(self, run_id: str, model_id: str, dataset_id: str, case_id: str) -> bool:
        result = self.resume_index(run_id).get((run_id, model_id, dataset_id, case_id))
        return result is not None and result.status.value in {"passed", "failed", "invalid", "skipped"}


def _safe_part(value: str) -> str:
    cleaned = INVALID_FILENAME_CHARS.sub("-", value.strip()).strip(".-")
    return cleaned or "blank"


def _to_simple_yaml(data: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {json.dumps(value, sort_keys=True)}" for key, value in sorted(data.items())) + "\n"
