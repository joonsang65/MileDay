from __future__ import annotations

import json
from pathlib import Path

from services.settings_service import DEFAULT_SETTINGS


def test_frontend_default_user_settings_match_backend_defaults() -> None:
    frontend_defaults_path = (
        Path(__file__).resolve().parents[1]
        / "frontend"
        / "src"
        / "config"
        / "defaultUserSettings.json"
    )

    frontend_defaults = json.loads(frontend_defaults_path.read_text(encoding="utf-8"))

    assert frontend_defaults == DEFAULT_SETTINGS
