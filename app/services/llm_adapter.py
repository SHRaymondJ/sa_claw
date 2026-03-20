from __future__ import annotations

import json
import socket
from urllib import error, request

from app.config import get_model_settings


def _call_chat_completion(user_prompt: str, system_prompt_override: str | None = None) -> tuple[str, str]:
    settings = get_model_settings()
    if not settings.enabled:
        raise RuntimeError("real model is not enabled")
    system_prompt = system_prompt_override or settings.system_prompt

    if settings.wire_api == "responses":
        endpoint = f"{settings.base_url.rstrip('/')}/responses"
        payload = {
            "model": settings.model_name,
            "input": [
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
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
                {"role": "system", "content": system_prompt},
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


def complete_with_fallback(
    user_prompt: str,
    fallback_text: str,
    system_prompt_override: str | None = None,
) -> tuple[str, str]:
    settings = get_model_settings()

    if not settings.enabled:
        return fallback_text, settings.source_label

    try:
        return _call_chat_completion(user_prompt, system_prompt_override=system_prompt_override)
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


def generate_assistant_brief(
    intent_label: str,
    user_message: str,
    context_summary: str,
    fallback_text: str,
    *,
    customer_name: str = "",
    conversation_mode: str = "",
    handoff_reason: str = "",
    confirmed_memory: str = "",
    observed_memory: str = "",
) -> tuple[str, str]:
    prompt = (
        "你是一名有 10 年经验的服装门店资深导购。"
        "请基于下面的结构化结果，用自然、像真人沟通的 2 句中文给导购一个执行摘要。"
        "只说门店执行内容，不要发挥没有提供的数据。"
        "如果是客户盘点，要明确说总量和当前只是样本。"
        "如果是客户洞察，要像导购总结，不要像数据库导出。"
        "如果是商品推荐，要说出推荐原因或场景。"
        "避免使用系统口吻，例如“已按数据库整理”。\n\n"
        f"任务类型：{intent_label}\n"
        f"当前模式：{conversation_mode or '未标注'}\n"
        f"当前客户：{customer_name or '未锁定'}\n"
        f"切换原因：{handoff_reason or '无'}\n"
        f"已确认记忆：{confirmed_memory or '无'}\n"
        f"最近观察：{observed_memory or '无'}\n"
        f"用户输入：{user_message}\n"
        f"上下文摘要：{context_summary}"
    )
    return complete_with_fallback(prompt, fallback_text)


def generate_message_draft(
    customer_name: str,
    product_names: list[str],
    tone: str,
    fallback_text: str,
    *,
    conversation_mode: str = "",
    confirmed_memory: str = "",
    observed_memory: str = "",
) -> tuple[str, str]:
    names = "、".join(product_names[:3])
    prompt = (
        "请写一条门店导购给会员的中文私聊消息。"
        "要求：自然、专业、不过度推销，不超过 90 字。"
        "像真人导购在微信里发出的消息，不要出现系统味总结。"
        f"对象：{customer_name}，语气：{tone}，当前模式：{conversation_mode or '沟通整理'}，涉及商品：{names}。"
        f"已确认记忆：{confirmed_memory or '无'}。最近观察：{observed_memory or '无'}。"
    )
    return complete_with_fallback(prompt, fallback_text)


def _extract_json_object(raw_text: str) -> dict | None:
    text = raw_text.strip()
    if text.startswith("```"):
        lines = [line for line in text.splitlines() if not line.startswith("```")]
        text = "\n".join(lines).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        payload = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None

    return payload if isinstance(payload, dict) else None


def classify_sales_intent(message: str, brand_name: str) -> tuple[dict | None, str]:
    fallback = None
    system_prompt = (
        "你是服装零售导购工作台中的语义意图分类器。"
        "你的任务不是聊天，而是把用户输入映射成严格 JSON。"
        "只允许识别本品牌门店导购范围内的问题。"
        "禁止输出 JSON 以外的任何内容。"
    )
    prompt = (
        "请判断下面这句话是否属于服装门店导购工作台支持的问题，并抽取最关键的结构化条件。\n"
        f"品牌：{brand_name}\n"
        f"用户输入：{message}\n\n"
        "返回 JSON，字段必须完整：\n"
        "{\n"
        '  "domain": "sales" | "out_of_scope",\n'
        '  "intent": "product_recommendation" | "customer_filter" | "inventory_lookup" | "task_management" | "message_draft" | "relationship_maintenance" | "unknown",\n'
        '  "customer_context": true | false,\n'
        '  "requested_count": number,\n'
        '  "category_hint": string,\n'
        '  "season_hint": string,\n'
        '  "style_terms": string[],\n'
        '  "query_terms": string[],\n'
        '  "reason": string,\n'
        '  "confidence": "high" | "medium" | "low"\n'
        "}\n"
        "说明：\n"
        "- 如果用户在问本品牌门店商品、客户、库存、任务、话术，domain= sales。\n"
        "- 像“维护一下乔安禾的客户关系”“按照她的喜好推荐维护关系的方式”属于 sales + relationship_maintenance。\n"
        "- 像“找5件适合夏天穿的衣服”属于 sales + product_recommendation。\n"
        "- requested_count 没提就返回 4。\n"
        "- 没有明确 category_hint / season_hint 就返回空字符串。\n"
        "- style_terms / query_terms 没有就返回空数组。"
    )

    raw_text, source = complete_with_fallback(
        prompt,
        fallback_text="{}",
        system_prompt_override=system_prompt,
    )
    payload = _extract_json_object(raw_text)
    return payload or fallback, source
