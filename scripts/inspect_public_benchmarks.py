from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from datasets import get_dataset_config_names, get_dataset_split_names, load_dataset
from huggingface_hub import HfApi


DATASETS = [
    {
        "key": "kmmlu_pro",
        "dataset_id": "LGAI-EXAONE/KMMLU-Pro",
        "source_url": "https://huggingface.co/datasets/LGAI-EXAONE/KMMLU-Pro",
        "official_repository": "https://github.com/LG-AI-EXAONE/KMMLU-Pro",
    },
    {
        "key": "kobalt_700",
        "dataset_id": "snunlp/KoBALT-700",
        "source_url": "https://huggingface.co/datasets/snunlp/KoBALT-700",
        "official_repository": "https://github.com/snunlp/KoBALT",
    },
    {
        "key": "click",
        "dataset_id": "EunsuKim/CLIcK",
        "source_url": "https://huggingface.co/datasets/EunsuKim/CLIcK",
        "official_repository": "https://github.com/rladmstn1714/CLIcK",
    },
    {
        "key": "ifeval_ko",
        "dataset_id": "allganize/IFEval-Ko",
        "source_url": "https://huggingface.co/datasets/allganize/IFEval-Ko",
        "official_repository": "https://github.com/EleutherAI/lm-evaluation-harness",
    },
]


def _json_safe(value: Any) -> Any:
    try:
        json.dumps(value, ensure_ascii=False)
    except TypeError:
        return repr(value)
    return value


def _card_license(card_data: Any) -> str:
    if card_data is None:
        return "unknown"
    license_value = getattr(card_data, "license", None)
    if license_value is None and isinstance(card_data, dict):
        license_value = card_data.get("license")
    if isinstance(license_value, list):
        return ",".join(str(item) for item in license_value)
    if license_value:
        return str(license_value)
    return "unknown"


def inspect_dataset(entry: dict[str, str]) -> dict[str, Any]:
    dataset_id = entry["dataset_id"]
    result: dict[str, Any] = {
        "key": entry["key"],
        "dataset_id": dataset_id,
        "source_url": entry["source_url"],
        "official_repository": entry["official_repository"],
        "inspected_at": datetime.now(timezone.utc).isoformat(),
    }

    api = HfApi()
    info = api.dataset_info(dataset_id)
    result["revision"] = info.sha
    result["license"] = _card_license(info.card_data)
    result["gated"] = getattr(info, "gated", None)

    configs = get_dataset_config_names(dataset_id, revision=info.sha)
    result["configs"] = configs
    result["splits"] = {}

    for config in configs:
        split_names = get_dataset_split_names(dataset_id, config, revision=info.sha)
        result["splits"][config] = {}
        for split_name in split_names:
            dataset = load_dataset(
                dataset_id,
                config,
                split=split_name,
                revision=info.sha,
                streaming=False,
            )
            result["splits"][config][split_name] = {
                "rows": len(dataset),
                "columns": list(dataset.column_names),
                "features": _json_safe(dataset.features.to_dict()),
                "sample": _json_safe(dataset[0]) if len(dataset) else None,
            }

    return result


def main() -> None:
    output: list[dict[str, Any]] = []
    for entry in DATASETS:
        try:
            output.append({"status": "ok", **inspect_dataset(entry)})
        except Exception as exc:
            output.append(
                {
                    "status": "error",
                    "key": entry["key"],
                    "dataset_id": entry["dataset_id"],
                    "source_url": entry["source_url"],
                    "official_repository": entry["official_repository"],
                    "error_type": type(exc).__name__,
                    "error_message": str(exc),
                }
            )
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
