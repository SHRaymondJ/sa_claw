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
    advisor_id: str
    advisor_name: str
    store_id: str
    store_name: str
    default_result_count: int
    max_result_count: int
    customer_sample_limit: int
    relationship_product_limit: int
    product_tag_limit: int
    workflow_note_limit: int
    memory_brief_limit: int
    chat_rate_limit: int
    chat_rate_window_seconds: int
    mutation_rate_limit: int
    mutation_rate_window_seconds: int
    quick_prompts: tuple[str, ...]


def _get_int_env(name: str, default: int, *, minimum: int = 1, maximum: int = 12) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return max(minimum, min(value, maximum))


def _parse_prompt_list(raw: str, defaults: tuple[str, ...]) -> tuple[str, ...]:
    if not raw.strip():
        return defaults

    parts = [raw]
    for separator in ("||", "\n"):
        if separator in raw:
            parts = raw.split(separator)
            break

    cleaned = tuple(item.strip() for item in parts if item.strip())
    return cleaned or defaults


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
            "你是拥有 10 年经验的服装零售资深导购，只能基于给定结构化数据输出自然、可信、可执行的中文建议，"
            "优先帮助导购完成客户维护、商品推荐、库存判断和跟进动作，不编造数据库外事实。",
        ).strip(),
    )


def get_app_settings() -> AppSettings:
    return AppSettings(
        db_path=Path(os.getenv("CRM_DB_PATH", BASE_DIR / "data" / "crm_demo.sqlite3")),
        frontend_dist=BASE_DIR / "frontend" / "dist",
        brand_name=os.getenv("CRM_BRAND_NAME", ""),
        advisor_id=os.getenv("CRM_ADVISOR_ID", "advisor-default"),
        advisor_name=os.getenv("CRM_ADVISOR_NAME", ""),
        store_id=os.getenv("CRM_STORE_ID", "store-default"),
        store_name=os.getenv("CRM_STORE_NAME", ""),
        default_result_count=_get_int_env("CRM_DEFAULT_RESULT_COUNT", 4, minimum=1, maximum=8),
        max_result_count=_get_int_env("CRM_MAX_RESULT_COUNT", 8, minimum=1, maximum=12),
        customer_sample_limit=_get_int_env("CRM_CUSTOMER_SAMPLE_LIMIT", 4, minimum=1, maximum=12),
        relationship_product_limit=_get_int_env("CRM_RELATIONSHIP_PRODUCT_LIMIT", 3, minimum=1, maximum=8),
        product_tag_limit=_get_int_env("CRM_PRODUCT_TAG_LIMIT", 4, minimum=1, maximum=8),
        workflow_note_limit=_get_int_env("CRM_WORKFLOW_NOTE_LIMIT", 4, minimum=1, maximum=8),
        memory_brief_limit=_get_int_env("CRM_MEMORY_BRIEF_LIMIT", 4, minimum=1, maximum=8),
        chat_rate_limit=_get_int_env("CRM_CHAT_RATE_LIMIT", 120, minimum=1, maximum=1000),
        chat_rate_window_seconds=_get_int_env("CRM_CHAT_RATE_WINDOW_SECONDS", 60, minimum=1, maximum=3600),
        mutation_rate_limit=_get_int_env("CRM_MUTATION_RATE_LIMIT", 60, minimum=1, maximum=1000),
        mutation_rate_window_seconds=_get_int_env("CRM_MUTATION_RATE_WINDOW_SECONDS", 60, minimum=1, maximum=3600),
        quick_prompts=_parse_prompt_list(os.getenv("CRM_QUICK_PROMPTS", ""), ()),
    )
