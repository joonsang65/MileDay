import pytest
import yaml
from pydantic import ValidationError

from harness.model_registry import (
    check_model_availability,
    load_model_registry,
    parse_ollama_list,
)


def _model(index: int, **overrides):
    data = {
        "id": f"candidate-{index}",
        "provider": "ollama",
        "runtime": "ollama",
        "model_tag": f"local-model-{index}:latest",
        "context_window": 4096,
        "quantization": "q4_k_m",
        "license_note": "Review license before evaluation.",
    }
    data.update(overrides)
    return data


def _write_registry(path, models):
    path.write_text(yaml.safe_dump({"models": models}, sort_keys=False), encoding="utf-8")


def test_load_model_registry_requires_five_models(tmp_path):
    registry_path = tmp_path / "models.yaml"
    _write_registry(registry_path, [_model(1), _model(2), _model(3), _model(4)])

    with pytest.raises(ValidationError, match="List should have at least 5 items"):
        load_model_registry(registry_path)


def test_load_model_registry_rejects_missing_required_field(tmp_path):
    registry_path = tmp_path / "models.yaml"
    models = [_model(index) for index in range(1, 6)]
    del models[0]["license_note"]
    _write_registry(registry_path, models)

    with pytest.raises(ValidationError, match="license_note"):
        load_model_registry(registry_path)


def test_load_model_registry_rejects_duplicate_model_tags(tmp_path):
    registry_path = tmp_path / "models.yaml"
    models = [_model(index) for index in range(1, 6)]
    models[1]["model_tag"] = models[0]["model_tag"]
    _write_registry(registry_path, models)

    with pytest.raises(ValidationError, match="model tags must be unique"):
        load_model_registry(registry_path)


def test_default_model_registry_loads_five_configured_candidates():
    registry = load_model_registry()

    assert len(registry.models) == 5
    assert [model.id for model in registry.models] == [
        "candidate-1",
        "candidate-2",
        "candidate-3",
        "candidate-4",
        "candidate-5",
    ]


def test_parse_ollama_list_reads_model_tags():
    output = """NAME                    ID              SIZE      MODIFIED
llama3.1:8b             abc123          4.9 GB    2 days ago
qwen2.5:7b              def456          4.7 GB    1 week ago
"""

    assert parse_ollama_list(output) == {"llama3.1:8b", "qwen2.5:7b"}


def test_check_model_availability_never_substitutes_missing_models():
    registry = load_model_registry()
    installed_tags = {registry.models[0].model_tag}

    availability = check_model_availability(registry, installed_tags=installed_tags)

    assert availability[0].installed is True
    assert [item.installed for item in availability[1:]] == [False, False, False, False]
    assert [item.model_tag for item in availability] == [
        model.model_tag for model in registry.models
    ]

