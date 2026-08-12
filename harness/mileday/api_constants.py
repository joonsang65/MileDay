from __future__ import annotations

from pathlib import Path

MILEDAY_API_MODEL_ID = "gemini-3.5-flash-lite"
MILEDAY_MULTITURN_FIXTURE = Path("tests") / "fixtures" / "mileday" / "test_api.json"
MILEDAY_API_SLEEP_SECONDS = 3.0
MILEDAY_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
MILEDAY_API_JUDGE_MODEL = "gemini-3.5-flash"
MILEDAY_MULTITURN_REFERENCE_TIMEZONE = "Asia/Seoul"
MILEDAY_MULTITURN_RUNTIME_OPTIONS = {"thinking_level": "minimal"}
MILEDAY_API_MULTITURN_PROMPT_VERSION = "v12-api"
MILEDAY_MULTITURN_PROMPT_VERSION = MILEDAY_API_MULTITURN_PROMPT_VERSION
