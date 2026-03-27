from __future__ import annotations

from app.schemas import RiskLevel, RuleAnalysis


def risk_level_from_score(score: int) -> RiskLevel:
    # Updated bands for v2 scoring:
    # LOW: 0–30, MEDIUM: 31–60, HIGH: 61+
    if score >= 61:
        return "HIGH"
    if score >= 31:
        return "MEDIUM"
    return "LOW"


def score_from_rules(rule: RuleAnalysis) -> int:
    return int(max(0, min(100, rule.score)))

