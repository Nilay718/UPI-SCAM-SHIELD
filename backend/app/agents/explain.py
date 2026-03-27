from __future__ import annotations

from typing import List

from app.schemas import LLMAnalysis, RuleAnalysis


def build_explanation(rule: RuleAnalysis, llm: LLMAnalysis) -> List[str]:
    """
    Produces user-facing explanations in short bullet-like sentences.
    Keep deterministic and easy to understand; include LLM reasons when available.
    """
    reasons: List[str] = []

    for hit in rule.hits:
        reasons.append(hit.reason)

    if llm.available and llm.reasons:
        for r in llm.reasons:
            if r and r not in reasons:
                reasons.append(r)

    if not reasons:
        reasons.append("No strong scam patterns detected in the provided text.")

    return reasons[:10]

