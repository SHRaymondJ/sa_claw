import json
import socket
from urllib import error, request

from app.config import get_model_settings


def _call_chat_completion(user_prompt: str) -> tuple[str, str]:
    settings = get_model_settings()
    if not settings.enabled:
        raise RuntimeError("real model is not enabled")

    if settings.wire_api == "responses":
        endpoint = f"{settings.base_url.rstrip('/')}/responses"
        payload = {
            "model": settings.model_name,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": settings.system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]},
            ],
            "reasoning": {"effort": settings.reasoning_effort},
            "text": {"format": {"type": "text"}},
            "stream": settings.stream,
        }
    else:
        endpoint = f"{settings.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": settings.model_name,
            "temperature": settings.temperature,
            "stream": settings.stream,
            "messages": [
                {"role": "system", "content": settings.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

    http_request = request.Request(
        endpoint,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.api_key}",
            "User-Agent": "Mozilla/5.0",
            "Accept": "text/event-stream" if settings.stream else "application/json",
            "Cache-Control": "no-cache",
        },
        method="POST",
    )

    with request.urlopen(http_request, timeout=settings.timeout_seconds) as response:
        if settings.stream and settings.wire_api == "chat_completions":
            parts: list[str] = []
            for raw_line in response:
                line = raw_line.decode("utf-8").strip()
                if not line.startswith("data: "):
                    continue
                data_line = line[6:]
                if data_line == "[DONE]":
                    break
                chunk = json.loads(data_line)
                content = chunk.get("choices", [{}])[0].get("delta", {}).get("content")
                if content:
                    parts.append(content)
            message = "".join(parts).strip()
            if not message:
                raise ValueError("stream returned empty content")
            return message, settings.source_label

        raw = response.read().decode("utf-8")

    data = json.loads(raw)
    if settings.wire_api == "responses":
        message = data.get("output_text", "")
    else:
        message = data["choices"][0]["message"]["content"]

    if isinstance(message, list):
        parts = [item.get("text", "") for item in message if isinstance(item, dict) and item.get("type") == "text"]
        message = "".join(parts)

    if not isinstance(message, str) or not message.strip():
        raise ValueError("model returned empty content")

    return message.strip(), settings.source_label


def complete_with_fallback(user_prompt: str, fallback_text: str) -> tuple[str, str]:
    settings = get_model_settings()

    if not settings.enabled:
        return fallback_text, settings.source_label

    try:
        return _call_chat_completion(user_prompt)
    except (
        error.URLError,
        error.HTTPError,
        TimeoutError,
        socket.timeout,
        OSError,
        ValueError,
        KeyError,
        json.JSONDecodeError,
    ):
        return fallback_text, f"fallback-{settings.source_label}"


def generate_assistant_brief(intent_label: str, user_message: str, context_summary: str, fallback_text: str) -> tuple[str, str]:
    prompt = (
        "你是一名服装门店导购工作台中的文案助手。"
        "请基于下面的结构化结果，用 2 句中文给导购一个执行摘要。"
        "只说门店执行内容，不要发挥没有提供的数据。\n\n"
        f"任务类型：{intent_label}\n"
        f"用户输入：{user_message}\n"
        f"上下文摘要：{context_summary}"
    )
    return complete_with_fallback(prompt, fallback_text)


def generate_message_draft(customer_name: str, product_names: list[str], tone: str, fallback_text: str) -> tuple[str, str]:
    names = "、".join(product_names[:3])
    prompt = (
        "请写一条门店导购给会员的中文私聊消息。"
        "要求：自然、专业、不过度推销，不超过 90 字。"
        f"对象：{customer_name}，语气：{tone}，涉及商品：{names}。"
    )
    return complete_with_fallback(prompt, fallback_text)
