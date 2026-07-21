import json

import pytest

from harness.config import HarnessSettings, load_settings


def test_default_settings_resolve_paths_to_project_root():
    settings = HarnessSettings()

    assert settings.project_root.name == "MileDay"
    assert settings.artifacts_dir == settings.project_root / "artifacts"
    assert settings.runs_dir == settings.project_root / "artifacts" / "runs"
    assert settings.datasets_dir == settings.project_root / "datasets"


def test_load_settings_accepts_json_config(tmp_path):
    config_path = tmp_path / "harness.json"
    config_path.write_text(
        json.dumps(
            {
                "artifacts_dir": "out",
                "runs_dir": "out/runs",
                "datasets_dir": "fixtures",
                "default_timeout_seconds": 30,
                "ollama_base_url": "http://127.0.0.1:11434",
            }
        ),
        encoding="utf-8",
    )

    settings = load_settings(config_path)

    assert settings.artifacts_dir == settings.project_root / "out"
    assert settings.runs_dir == settings.project_root / "out" / "runs"
    assert settings.datasets_dir == settings.project_root / "fixtures"
    assert settings.default_timeout_seconds == 30
    assert settings.ollama_base_url == "http://127.0.0.1:11434"


def test_load_settings_rejects_non_json_config(tmp_path):
    config_path = tmp_path / "harness.yaml"
    config_path.write_text("artifacts_dir: out", encoding="utf-8")

    with pytest.raises(ValueError, match=".json"):
        load_settings(config_path)

