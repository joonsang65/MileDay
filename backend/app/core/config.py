from functools import lru_cache
from os import getenv
from pathlib import Path
from uuid import UUID

from dotenv import load_dotenv
from pydantic import BaseModel, Field


BASE_DIR = Path(__file__).resolve().parents[3]
# 프로젝트 루트 기준 .env 로드
load_dotenv(BASE_DIR / getenv("ENV_FILE", ".env"))


def env_bool(name: str, default: bool = False) -> bool:
    value = getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Settings(BaseModel):
    # 서버 실행 환경
    env: str = Field(default_factory=lambda: getenv("ENV", "development"))
    app_name: str = Field(default_factory=lambda: getenv("APP_NAME", "MileDay"))
    api_host: str = Field(default_factory=lambda: getenv("API_HOST", "127.0.0.1"))
    api_port: int = Field(default_factory=lambda: int(getenv("API_PORT", "8000")))

    # Supabase 접근 정보는 backend 환경 변수 전용
    supabase_url: str | None = Field(default_factory=lambda: getenv("SUPABASE_URL"))
    supabase_anon_key: str | None = Field(default_factory=lambda: getenv("SUPABASE_ANON_KEY"))
    supabase_service_role_key: str | None = Field(
        default_factory=lambda: getenv("SUPABASE_SERVICE_ROLE_KEY")
    )
    supabase_db_url: str | None = Field(default_factory=lambda: getenv("SUPABASE_DB_URL"))

    # 한국 공휴일 API 설정. 키가 없으면 캘린더는 주말 기준으로만 동작한다.
    holiday_api_service_key: str | None = Field(
        default_factory=lambda: getenv("HOLIDAY_API_SERVICE_KEY")
    )
    holiday_api_base_url: str = Field(
        default_factory=lambda: getenv(
            "HOLIDAY_API_BASE_URL",
            "https://apis.data.go.kr/B090041/openapi/service/SpcdeInfoService/getHoliDeInfo",
        )
    )

    # 같은 Supabase 프로젝트를 쓰는 통합 테스트 안전장치
    integration_tests_enabled: bool = Field(
        default_factory=lambda: env_bool("ENABLE_INTEGRATION_TESTS")
    )
    integration_test_email: str | None = Field(
        default_factory=lambda: getenv("INTEGRATION_TEST_EMAIL")
    )
    integration_test_password: str | None = Field(
        default_factory=lambda: getenv("INTEGRATION_TEST_PASSWORD")
    )
    integration_test_user_id: str | None = Field(
        default_factory=lambda: getenv("INTEGRATION_TEST_USER_ID")
    )
    integration_test_title_prefix: str = Field(
        default_factory=lambda: getenv("INTEGRATION_TEST_TITLE_PREFIX", "[TEST]")
    )

    # 로컬 파일 로그와 보존 기간
    log_level: str = Field(default_factory=lambda: getenv("LOG_LEVEL", "INFO"))
    log_dir: Path = Field(default_factory=lambda: Path(getenv("LOG_DIR", "logs")))
    log_retention_days: int = Field(
        default_factory=lambda: int(getenv("LOG_RETENTION_DAYS", "7"))
    )

    cors_origins: list[str] = Field(default_factory=list)

    def model_post_init(self, __context: object) -> None:
        # 쉼표 구분 origin 문자열을 FastAPI CORS 목록으로 정규화
        raw_origins = getenv(
            "CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000",
        )
        self.cors_origins = [
            origin.strip() for origin in raw_origins.split(",") if origin.strip()
        ]
        # 상대 로그 경로는 프로젝트 루트 아래로 고정
        self.log_dir = (
            self.log_dir
            if self.log_dir.is_absolute()
            else BASE_DIR / self.log_dir
        )
        if self.integration_tests_enabled:
            self._validate_integration_test_safety()

    @property
    def is_supabase_configured(self) -> bool:
        # health/db에서 secret 존재 여부 대신 구성 여부만 사용
        return bool(self.supabase_url and self.supabase_anon_key)

    def _validate_integration_test_safety(self) -> None:
        missing = [
            name
            for name, value in {
                "INTEGRATION_TEST_EMAIL": self.integration_test_email,
                "INTEGRATION_TEST_PASSWORD": self.integration_test_password,
                "INTEGRATION_TEST_USER_ID": self.integration_test_user_id,
                "INTEGRATION_TEST_TITLE_PREFIX": self.integration_test_title_prefix,
                "SUPABASE_SERVICE_ROLE_KEY": self.supabase_service_role_key,
            }.items()
            if not value
        ]
        if missing:
            raise ValueError(
                "Integration tests require safe test-only settings: "
                + ", ".join(missing)
            )

        local_part = self.integration_test_email.split("@", 1)[0]
        if not local_part.startswith("test"):
            raise ValueError("INTEGRATION_TEST_EMAIL must be a test-only account.")
        if not self.integration_test_title_prefix.startswith("[TEST"):
            raise ValueError("INTEGRATION_TEST_TITLE_PREFIX must start with [TEST.")
        UUID(self.integration_test_user_id)


@lru_cache
def get_settings() -> Settings:
    # 프로세스 전역 설정 객체 단일화
    return Settings()
