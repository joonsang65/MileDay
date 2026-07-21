from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml
from datasets import get_dataset_config_names, get_dataset_split_names, load_dataset
from huggingface_hub import HfApi, list_repo_files, snapshot_download


BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "configs" / "datasets.yaml"
DATASETS_DIR = BASE_DIR / "datasets"
PROCESSED_SCHEMA_VERSION = "1.0.0"
FIELD_MAPPING_VERSION = "1.0.0"


DATASET_PATHS = {
    "kmmlu_pro": "kmmlu-pro",
    "kobalt": "kobalt-700",
    "click": "click",
    "ifeval_ko": "ifeval-ko",
}


def _load_config() -> dict[str, Any]:
    return yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError:
        return repr(value)
    return value


def _inspect_dataset(dataset: dict[str, Any]) -> dict[str, Any]:
    dataset_id = dataset["dataset_id"]
    revision = dataset["revision"]
    configs = get_dataset_config_names(dataset_id, revision=revision)
    splits: dict[str, dict[str, int]] = {}
    source_schema: dict[str, dict[str, Any]] = {}

    for config in configs:
        split_names = get_dataset_split_names(dataset_id, config, revision=revision)
        splits[config] = {}
        for split_name in split_names:
            loaded = load_dataset(
                dataset_id,
                config,
                split=split_name,
                revision=revision,
                streaming=False,
            )
            splits[config][split_name] = len(loaded)
            if config == dataset["config"] and split_name == dataset["split"]:
                source_schema = _json_safe(loaded.features.to_dict())

    return {
        "configs": configs,
        "splits": splits,
        "source_schema": source_schema,
    }


def _write_manifest(
    *,
    key: str,
    dataset: dict[str, Any],
    revision_dir: Path,
    source_path: Path,
    repo_files: list[str],
    inspection: dict[str, Any],
) -> Path:
    manifest = {
        "dataset_key": key,
        "dataset_id": dataset["dataset_id"],
        "source_url": dataset["source_url"],
        "official_repository": dataset["official_repository"],
        "revision": dataset["revision"],
        "downloaded_at": datetime.now(timezone.utc).isoformat(),
        "access": "gated" if key == "kmmlu_pro" else "public",
        "license": dataset["license"],
        "commercial_use_verified": bool(dataset["commercial_use_verified"]),
        "configs": inspection["configs"],
        "selected_config": dataset["config"],
        "selected_split": dataset["split"],
        "splits": inspection["splits"],
        "source_schema": inspection["source_schema"],
        "source_path": str(source_path.relative_to(BASE_DIR)),
        "repo_files": repo_files,
        "processed_schema_version": PROCESSED_SCHEMA_VERSION,
        "field_mapping_version": FIELD_MAPPING_VERSION,
    }
    manifest_path = revision_dir / "dataset_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def main() -> None:
    config = _load_config()
    api = HfApi()
    results: list[dict[str, str]] = []

    for key, dataset in config["datasets"].items():
        dataset_id = dataset["dataset_id"]
        revision = dataset["revision"]

        info = api.dataset_info(dataset_id, revision=revision)
        if info.sha != revision:
            raise RuntimeError(
                f"Resolved revision mismatch for {dataset_id}: expected {revision}, got {info.sha}"
            )

        revision_dir = DATASETS_DIR / DATASET_PATHS[key] / revision
        source_dir = revision_dir / "source"
        revision_dir.mkdir(parents=True, exist_ok=True)

        source_path = Path(
            snapshot_download(
                repo_id=dataset_id,
                repo_type="dataset",
                revision=revision,
                local_dir=source_dir,
            )
        )
        repo_files = list_repo_files(dataset_id, repo_type="dataset", revision=revision)
        inspection = _inspect_dataset(dataset)
        manifest_path = _write_manifest(
            key=key,
            dataset=dataset,
            revision_dir=revision_dir,
            source_path=source_path,
            repo_files=repo_files,
            inspection=inspection,
        )
        results.append(
            {
                "dataset": key,
                "source": str(source_path.relative_to(BASE_DIR)),
                "manifest": str(manifest_path.relative_to(BASE_DIR)),
            }
        )

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
