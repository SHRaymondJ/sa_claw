from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"


def _load_dotenv() -> None:
    if not ENV_FILE.exists():
        return

    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


_load_dotenv()


@dataclass(frozen=True)
class ModelSettings:
    provider: str
    base_url: str
    api_key: str
    model_name: str
    wire_api: str
    reasoning_effort: str
    stream: bool
    timeout_seconds: float
    temperature: float
    system_prompt: str

    @property
    def enabled(self) -> bool:
        return self.provider != "mock" and bool(self.api_key)

    @property
    def source_label(self) -> str:
        if self.enabled:
            return f"{self.provider}:{self.model_name}"
        if self.provider != "mock" and not self.api_key:
            return f"mock(no-api-key:{self.provider})"
        return "mock"


@dataclass(frozen=True)
class AppSettings:
    db_path: Path
    frontend_dist: Path
    brand_name: str
    advisor_name: str
    store_name: str


def get_model_settings() -> ModelSettings:
    return ModelSettings(
        provider=os.getenv("MODEL_PROVIDER", "mock").strip().lower() or "mock",
        base_url=os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1").strip(),
        api_key=os.getenv("MODEL_API_KEY", "").strip(),
        model_name=os.getenv("MODEL_NAME", "gpt-4.1-mini").strip() or "gpt-4.1-mini",
        wire_api=os.getenv("MODEL_WIRE_API", "chat_completions").strip().lower() or "chat_completions",
        reasoning_effort=os.getenv("MODEL_REASONING_EFFORT", "medium").strip().lower() or "medium",
        stream=os.getenv("MODEL_STREAM", "false").strip().lower() in {"1", "true", "yes", "on"},
        timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "8")),
        temperature=float(os.getenv("MODEL_TEMPERATURE", "0.4")),
        system_prompt=os.getenv(
            "MODEL_SYSTEM_PROMPT",
            "你是服装零售导购工作台的文案助手，只能基于给定结构化数据输出简洁、可信、可执行的中文建议。",
        ).strip(),
    )


def get_app_settings() -> AppSettings:
    return AppSettings(
        db_path=Path(os.getenv("CRM_DB_PATH", BASE_DIR / "data" / "crm_demo.sqlite3")),
        frontend_dist=BASE_DIR / "frontend" / "dist",
        brand_name=os.getenv("CRM_BRAND_NAME", "缦序"),
        advisor_name=os.getenv("CRM_ADVISOR_NAME", "林顾问"),
        store_name=os.getenv("CRM_STORE_NAME", "上海静安店"),
    )
