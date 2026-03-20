from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass(frozen=True)
class KnowledgeBrief:
    topic: str
    content: str
    source: str
    score: int


def retrieve_knowledge_briefs(
    connection,
    *,
    message: str,
    workflow_name: str,
    focus_customer: dict | None = None,
    limit: int = 3,
) -> list[KnowledgeBrief]:
    rows = connection.execute(
        """
        SELECT topic, trigger_terms, content, source
        FROM knowledge_documents
        WHERE active = 1
        """
    ).fetchall()

    haystack_parts = [message, workflow_name]
    if focus_customer:
        haystack_parts.extend(
            [
                str(focus_customer.get("profile", "")),
                str(focus_customer.get("reason", "")),
                str(focus_customer.get("next_action", "")),
            ]
        )
    haystack = " ".join(part for part in haystack_parts if part)

    ranked: list[KnowledgeBrief] = []
    for row in rows:
        terms = json.loads(row["trigger_terms"])
        score = 0
        if row["topic"] == workflow_name:
            score += 12
        for term in terms:
            if term and term in haystack:
                score += 5
        if workflow_name == "relationship_maintenance" and row["topic"] == "service_boundary":
            score -= 3
        if score <= 0:
            continue
        ranked.append(
            KnowledgeBrief(
                topic=str(row["topic"]),
                content=str(row["content"]),
                source=str(row["source"]),
                score=score,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    deduped: list[KnowledgeBrief] = []
    seen_contents: set[str] = set()
    for item in ranked:
        if item.content in seen_contents:
            continue
        seen_contents.add(item.content)
        deduped.append(item)
        if len(deduped) >= limit:
            break
    return deduped
