from __future__ import annotations

from typing import List, Tuple

from app.schemas import FinalDecision, LLMAnalysis, RuleAnalysis
from app.agents.risk import risk_level_from_score, score_from_rules


def merge_decision(rule: RuleAnalysis, llm: LLMAnalysis) -> FinalDecision:
    rule_score = score_from_rules(rule)
    risk_score = rule_score

    # If LLM available and confident, blend into score.
    if llm.available and llm.is_scam is not None:
        conf = llm.confidence if llm.confidence is not None else 0.6
        # Map scam prediction to score impact
        llm_score = int((80 if llm.is_scam else 20) * conf + (80 if llm.is_scam else 20) * (1 - conf) * 0.2)
        # Weighted merge: keep rules primary (explainability), LLM secondary
        risk_score = int(round(0.7 * rule_score + 0.3 * llm_score))

    risk_score = max(0, min(100, risk_score))
    risk_level = risk_level_from_score(risk_score)

    # Determine is_scam: high risk OR strong llm signal
    is_scam = risk_level == "HIGH" or (llm.available and llm.is_scam is True and (llm.confidence or 0.6) >= 0.65)

    reasons: List[str] = []
    for hit in rule.hits[:6]:
        reasons.append(hit.reason)
    for r in (llm.reasons or [])[:6]:
        if r and r not in reasons:
            reasons.append(r)

    suggested: List[str] = []
    # Always include safety basics
    suggested.extend(
        [
            "Do not share OTP/UPI PIN or banking credentials.",
            "Do not click suspicious links; verify via official app/website.",
            "If money was debited, contact your bank/UPI app support immediately.",
        ]
    )
    for a in (llm.suggested_actions or [])[:6]:
        if a and a not in suggested:
            suggested.append(a)

    return FinalDecision(
        risk_level=risk_level,
        is_scam=is_scam,
        risk_score=risk_score,
        reasons=reasons[:10],
        suggested_actions=suggested[:10],
    )

