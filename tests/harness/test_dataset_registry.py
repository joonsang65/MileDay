import pytest
import yaml
from pydantic import ValidationError

from harness.dataset_registry import load_dataset_registry


def test_load_dataset_registry_reads_configured_datasets():
    registry = load_dataset_registry()

    assert set(registry.datasets) == {"kmmlu_pro", "kobalt", "click", "ifeval_ko"}
    assert registry.datasets["kobalt"].fields["question"] == "Question"


def test_load_dataset_registry_rejects_blank_field_mapping(tmp_path):
    registry_path = tmp_path / "datasets.yaml"
    registry_path.write_text(
        yaml.safe_dump(
            {
                "datasets": {
                    "bad": {
                        "dataset_id": "dataset/id",
                        "source_url": "https://example.test",
                        "official_repository": "https://example.test/repo",
                        "revision": "abc",
                        "config": "default",
                        "split": "train",
                        "license": "unknown",
                        "commercial_use_verified": False,
                        "fields": {"question": ""},
                    }
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValidationError):
        load_dataset_registry(registry_path)
