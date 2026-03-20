from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic

from fastapi import HTTPException

from app.config import AppSettings


@dataclass(frozen=True)
class RequestActor:
    advisor_id: str
    store_id: str


_RATE_LIMITS: dict[str, deque[float]] = {}
_RATE_LIMIT_LOCK = Lock()


def build_request_actor(
    settings: AppSettings,
    *,
    advisor_id: str | None,
    store_id: str | None,
    require_identity: bool,
) -> RequestActor:
    cleaned_advisor_id = (advisor_id or "").strip()
    cleaned_store_id = (store_id or "").strip()

    if require_identity and (not cleaned_advisor_id or not cleaned_store_id):
        raise HTTPException(status_code=401, detail="missing advisor identity")

    if not cleaned_advisor_id:
        cleaned_advisor_id = settings.advisor_id
    if not cleaned_store_id:
        cleaned_store_id = settings.store_id

    if cleaned_store_id != settings.store_id:
        raise HTTPException(status_code=403, detail="store mismatch")

    return RequestActor(advisor_id=cleaned_advisor_id, store_id=cleaned_store_id)


def enforce_rate_limit(bucket: str, key: str, *, limit: int, window_seconds: int) -> None:
    now = monotonic()
    cache_key = f"{bucket}:{key}"
    with _RATE_LIMIT_LOCK:
        timestamps = _RATE_LIMITS.setdefault(cache_key, deque())
        while timestamps and now - timestamps[0] > window_seconds:
            timestamps.popleft()
        if len(timestamps) >= limit:
            raise HTTPException(status_code=429, detail="rate limit exceeded")
        timestamps.append(now)
