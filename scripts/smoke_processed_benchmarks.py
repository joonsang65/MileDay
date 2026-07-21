from __future__ import annotations

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BASE_DIR))

from harness.benchmarks.click_adapter import CLIcKFieldMapping, load_click_cases
from harness.benchmarks.kmmlu_pro import KMMLUProFieldMapping, load_kmmlu_pro_cases
from harness.benchmarks.kobalt_700 import KoBALT700FieldMapping, load_kobalt_700_cases
from harness.dataset_registry import load_dataset_registry


DATASET_DIR_NAMES = {
    "kmmlu_pro": "kmmlu-pro",
    "kobalt": "kobalt-700",
    "click": "click",
    "ifeval_ko": "ifeval-ko",
}
CHOICE_LABELS = tuple("ABCDEFGHIJ")


def _processed_path(dataset_key: str, revision: str) -> Path:
    return (
        BASE_DIR
        / "datasets"
        / DATASET_DIR_NAMES[dataset_key]
        / revision
        / "processed"
        / "data.jsonl"
    )


def _choice_mapping(path: Path) -> dict[str, str]:
    first_row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
    mapping = {}
    for label in CHOICE_LABELS:
        field_name = f"choice_{label.lower()}"
        if field_name in first_row:
            mapping[label] = field_name
    return mapping


def _count_jsonl(path: Path) -> int:
    return len([line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()])


def main() -> None:
    registry = load_dataset_registry()
    results = []

    kmmlu_path = _processed_path("kmmlu_pro", registry.datasets["kmmlu_pro"].revision)
    kmmlu_cases = load_kmmlu_pro_cases(
        kmmlu_path,
        dataset_id=registry.datasets["kmmlu_pro"].dataset_id,
        mapping=KMMLUProFieldMapping(
            choices=_choice_mapping(kmmlu_path),
            category="category",
            metadata={"metadata": "metadata"},
        ),
    )
    results.append({"dataset": "kmmlu_pro", "cases": len(kmmlu_cases)})

    kobalt_path = _processed_path("kobalt", registry.datasets["kobalt"].revision)
    kobalt_cases = load_kobalt_700_cases(
        kobalt_path,
        dataset_id=registry.datasets["kobalt"].dataset_id,
        mapping=KoBALT700FieldMapping(
            choices=_choice_mapping(kobalt_path),
            category="category",
            metadata={"metadata": "metadata"},
        ),
    )
    results.append({"dataset": "kobalt", "cases": len(kobalt_cases)})

    click_path = _processed_path("click", registry.datasets["click"].revision)
    click_cases = load_click_cases(
        click_path,
        dataset_id=registry.datasets["click"].dataset_id,
        mapping=CLIcKFieldMapping(
            choices=_choice_mapping(click_path),
            category="category",
            metadata={"metadata": "metadata"},
        ),
    )
    results.append({"dataset": "click", "cases": len(click_cases)})

    ifeval_path = _processed_path("ifeval_ko", registry.datasets["ifeval_ko"].revision)
    results.append({"dataset": "ifeval_ko", "cases": _count_jsonl(ifeval_path)})

    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
