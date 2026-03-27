from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Literal, Tuple

IntentType = Literal[
    "payment_push_intent",
    "info_extraction_intent",
    "urgency_pressure_intent",
    "authority_impersonation",
    "reward_trap",
    "none",
]


@dataclass(frozen=True)
class IntentResult:
    intent_type: str
    intent_confidence: int  # 0-100
    secondary_intents: Tuple[str, ...] = ()


def _score_payment_push(text: str) -> int:
    t = text.lower()
    score = 0
    patterns = [
        (r"\b(approve|accept|complete)\b.*\b(request|payment|transaction)\b", 35),
        (r"\breceive\s+money\b|\bget\s+money\b|\bto\s+receive\b", 28),
        (r"\bcollect\b.*\b(request|payment)\b|\brequest\s+money\b", 30),
        (r"\bscan\b.*\b(qr|code)\b", 25),
        (r"\bupi\b.*\b(pay|send|approve)\b", 22),
        (r"रिक्वेस्ट\s*(अक्सेप्ट|स्वीकार)|कलेक्ट|भुगतान\s*स्वीकार", 30),
    ]
    for pat, pts in patterns:
        if re.search(pat, t, re.I):
            score += pts
    if re.search(r"\b(pay|payment|send\s+money|transfer)\b", t, re.I):
        score += 10
    return min(100, score)


def _score_info_extraction(text: str) -> int:
    t = text.lower()
    score = 0
    if re.search(r"\botp\b|one[-\s]?time\s+password|ओटीपी", t, re.I):
        score += 45
    if re.search(r"\bupi\s*pin\b|\bmpin\b|\bpin\b.*\b(share|send|tell)\b|पिन", t, re.I):
        score += 45
    if re.search(r"\b(card|cvv|password|net\s*banking)\b.*\b(share|send|tell)\b", t, re.I):
        score += 25
    if re.search(r"\baccount\s+number\b|\bifsc\b", t, re.I):
        score += 15
    return min(100, score)


def _score_urgency(text: str) -> int:
    t = text.lower()
    score = 0
    keys = [
        (r"\burgent\b|\bimmediately\b|\bright\s+now\b|\bwithin\s+\d+", 25),
        (r"\b(blocked|suspended|frozen|closed)\b.*\b(account|upi|number)\b", 30),
        (r"\bact\s+now\b|\basap\b|\bexpire", 20),
        (r"तुरंत|अभी|जल्दी|फौरन|खाता\s*ब्लॉक", 25),
    ]
    for pat, pts in keys:
        if re.search(pat, t, re.I):
            score += pts
    return min(100, score)


def _score_authority(text: str) -> int:
    t = text.lower()
    score = 0
    keys = [
        (r"\b(bank|rbi|npci|police|cyber\s*cell)\b.*\b(team|department|officer)\b", 35),
        (r"\b(verification|support|customer\s*care)\s+team\b", 28),
        (r"\bofficial\b.*\b(notice|message|alert)\b", 18),
        (r"बैंक\s*टीम|आरबीआई|वेरिफिकेशन\s*टीम", 30),
    ]
    for pat, pts in keys:
        if re.search(pat, t, re.I):
            score += pts
    return min(100, score)


def _score_reward_trap(text: str) -> int:
    t = text.lower()
    score = 0
    keys = [
        (r"\b(refund|cash\s*back|cashback|reward|prize|lottery|winner)\b", 28),
        (r"\bbonus\b|\bcredited\b.*\baccount\b", 18),
        (r"रिफंड|कैशबैक|इनाम|लॉटरी", 25),
    ]
    for pat, pts in keys:
        if re.search(pat, t, re.I):
            score += pts
    return min(100, score)


_SCORERS: Dict[str, object] = {
    "payment_push_intent": _score_payment_push,
    "info_extraction_intent": _score_info_extraction,
    "urgency_pressure_intent": _score_urgency,
    "authority_impersonation": _score_authority,
    "reward_trap": _score_reward_trap,
}


def detect_intent(text: str) -> IntentResult:
    """
    Pattern + structure based intent (no ML). Highest-scoring intent wins.
    """
    raw = text or ""
    scores: List[Tuple[str, int]] = []
    for name, fn in _SCORERS.items():
        s = int(fn(raw))  # type: ignore[operator]
        scores.append((name, s))
    scores.sort(key=lambda x: -x[1])
    best_name, best = scores[0]
    secondaries = tuple(n for n, s in scores[1:] if s >= 25)

    if best < 18:
        return IntentResult(intent_type="none", intent_confidence=0, secondary_intents=())

    conf = min(100, best)
    return IntentResult(
        intent_type=best_name,
        intent_confidence=conf,
        secondary_intents=secondaries[:4],
    )


def intent_risk_boost(intent: IntentResult) -> int:
    """Extra rule-score points from intent (capped)."""
    if intent.intent_type == "none":
        return 0
    base = intent.intent_confidence // 6  # up to ~16
    weights = {
        "payment_push_intent": 14,
        "info_extraction_intent": 16,
        "urgency_pressure_intent": 10,
        "authority_impersonation": 8,
        "reward_trap": 9,
    }
    cap = weights.get(intent.intent_type, 8)
    return min(cap, 6 + base)
