from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from app.schemas import RuleAnalysis, RuleHit


@dataclass(frozen=True)
class Rule:
    rule_id: str
    title: str
    patterns: Tuple[re.Pattern, ...]
    severity: int  # 0..100
    reason: str


def _pat(s: str) -> re.Pattern:
    return re.compile(s, re.IGNORECASE)

def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip().lower())


# Intent-based scam phrase library (helps catch scams without obvious keywords)
SCAM_PHRASE_LIBRARY: List[str] = [
    "approve the request",
    "approve request",
    "accept request",
    "complete request",
    "confirm payment",
    "refund pending",
    "refund process",
    "verify payment",
    "scan qr to receive",
    "scan to receive",
    "approve to get money",
    "receive money",
    "get money",
    "collect payment",
    "send money urgently",
    # Hindi / Hinglish variants
    "कलेक्ट रिक्वेस्ट",
    "पैसे प्राप्त करने के लिए",
    "भुगतान पुष्टि",
    "रिफंड पेंडिंग",
    "क्यूआर स्कैन",
    "रिक्वेस्ट अक्सेप्ट",
]


RULES: List[Rule] = [
    Rule(
        rule_id="otp_request",
        title="OTP requested or shared",
        patterns=(
            _pat(r"\botp\b"),
            _pat(r"\bone[-\s]?time\s+password\b"),
            _pat(r"ओटीपी|ओ\.टी\.पी"),
        ),
        severity=70,
        reason="Asking for OTP is a strong fraud signal. Legit services never ask you to share OTP.",
    ),
    Rule(
        rule_id="upi_pin_or_mpins",
        title="UPI PIN / mPIN requested",
        patterns=(
            _pat(r"\bupi\s*pin\b"),
            _pat(r"\bmpin\b"),
            _pat(r"\bpin\s*(share|send|tell)\b"),
            _pat(r"पिन|upi\s*पिन|यूपीआई\s*पिन"),
        ),
        severity=70,
        reason="UPI PIN/mPIN should never be shared. Requests for it are almost always fraudulent.",
    ),
    Rule(
        rule_id="urgent_action",
        title="Urgent pressure / threat",
        patterns=(
            _pat(r"\burgent\b"),
            _pat(r"\bimmediately\b"),
            _pat(r"\bwithin\s+\d+\s*(min|mins|minutes|hour|hours)\b"),
            _pat(r"\baccount\s+(blocked|suspended|freeze|frozen)\b"),
            _pat(r"\b(up[i]?\s*)?(will\s+)?(be\s+)?(blocked|closed|deactivated)\b"),
            _pat(r"तुरंत|अभी|जल्दी|फौरन"),
            _pat(r"खाता\s*(ब्लॉक|बंद)|account\s*blocked"),
        ),
        severity=30,
        reason="Scammers create urgency to bypass your judgment (threats like blocked/suspended).",
    ),
    Rule(
        rule_id="suspicious_link",
        title="Suspicious link / click request",
        patterns=(
            _pat(r"\bclick\b"),
            _pat(r"\blink\b"),
            _pat(r"https?://"),
            _pat(r"\bbit\.ly\b|\btinyurl\b|\bgoo\.gl\b|\bt\.co\b"),
            _pat(r"लिंक|क्लिक"),
        ),
        severity=40,
        reason="Messages urging you to click links are commonly used for phishing and malware.",
    ),
    Rule(
        rule_id="upi_collect",
        title="UPI collect request / pay now",
        patterns=(
            _pat(r"\bcollect\b"),
            _pat(r"\brequest\s+money\b"),
            _pat(r"\bpay\s+now\b"),
            _pat(r"\bupi\b"),
            _pat(r"\bscan\b.*\bqr\b|\bqr\b.*\bscan\b"),
            _pat(r"कलेक्ट|रिक्वेस्ट\s*मनी|पे\s*नाउ|भुगतान"),
        ),
        severity=50,
        reason="Fraud often uses collect requests or QR tricks to make you authorize a payment.",
    ),
    Rule(
        rule_id="collect_to_receive",
        title="Tricked to accept collect for receiving money",
        patterns=(
            _pat(r"\bto\s+receive\b"),
            _pat(r"\breceive\s+money\b"),
            _pat(r"\baccept\b.*\bcollect\b"),
            _pat(r"\bcollect\b.*\bto\s+receive\b"),
            _pat(r"\brequest\b.*\bto\s+receive\b"),
            _pat(r"पैसे\s*(प्राप्त|मिलने)\s*के\s*लिए|receive\s*करने\s*के\s*liye"),
            _pat(r"कलेक्ट\s*रिक्वेस्ट\s*अक्सेप्ट|accept\s*collect"),
        ),
        severity=70,
        reason="A collect request is a payment approval. Scammers often claim you must 'accept' to receive money.",
    ),
    Rule(
        rule_id="kyc_update",
        title="KYC / bank verification lure",
        patterns=(
            _pat(r"\bkyc\b"),
            _pat(r"\bupdate\s+kyc\b"),
            _pat(r"\bverify\b.*\baccount\b"),
            _pat(r"\bbank\b.*\bupdate\b"),
            _pat(r"\bkyc\b.*\b(expired|pending|fail|failed)\b"),
        ),
        severity=30,
        reason="Fake KYC/verification requests are common pretexts to steal credentials or money.",
    ),
    Rule(
        rule_id="refund_or_cashback_bait",
        title="Refund / cashback / reward bait",
        patterns=(
            _pat(r"\brefund\b"),
            _pat(r"\bcash\s*back\b|\bcashback\b"),
            _pat(r"\breward\b|\bbonus\b"),
            _pat(r"\bupi\b.*\brefund\b"),
        ),
        severity=40,
        reason="Refund/cashback baits are often used to trick users into approving collect requests or sharing OTP/PIN.",
    ),
    Rule(
        rule_id="remote_access_app",
        title="Remote access / screen sharing app mention",
        patterns=(
            _pat(r"\banydesk\b|\bteamviewer\b|\bquick\s*support\b"),
            _pat(r"\bremote\b.*\baccess\b"),
            _pat(r"\bscreen\s*(share|sharing)\b"),
        ),
        severity=70,
        reason="Remote access/screen sharing apps are commonly used by scammers to take over devices and drain accounts.",
    ),
    Rule(
        rule_id="sim_or_number_block",
        title="SIM/number blocked pretext",
        patterns=(
            _pat(r"\bsim\b.*\b(blocked|suspended|deactivated)\b"),
            _pat(r"\bnumber\b.*\b(blocked|suspended|deactivated)\b"),
            _pat(r"\bport\b.*\bout\b"),
        ),
        severity=25,
        reason="SIM/number block pretexts are used to create panic and push victims into quick actions.",
    ),
    Rule(
        rule_id="payment_approval_trick",
        title="Payment approval trick (approve/accept request)",
        patterns=(
            _pat(r"\b(approve|accept|complete)\b.*\b(request|req)\b"),
            _pat(r"\bconfirm\b.*\b(payment|transaction)\b"),
            _pat(r"रिक्वेस्ट\s*(अक्सेप्ट|एक्सेप्ट|स्वीकार)|approve\s*kar"),
        ),
        severity=70,
        reason="Scammers often ask you to approve/accept a request to trick you into authorizing a payment.",
    ),
    Rule(
        rule_id="receive_money_trick",
        title="Receive-money trick (reverse payment scam)",
        patterns=(
            _pat(r"\b(receive|get)\b.*\bmoney\b"),
            _pat(r"\bcollect\b.*\bpayment\b"),
            _pat(r"पैसे\s*(प्राप्त|मिल|ले)\b"),
        ),
        severity=70,
        reason="Fraudsters use 'receive money' wording to push victims into approving a collect/payment request.",
    ),
    Rule(
        rule_id="refund_scam",
        title="Refund scam (pending/confirm)",
        patterns=(
            _pat(r"\brefund\b.*\b(pending|process|processing)\b"),
            _pat(r"\bconfirm\b.*\brefund\b"),
            _pat(r"रिफंड\s*(पेंडिंग|pending)|रिफंड\s*कन्फर्म"),
        ),
        severity=70,
        reason="Refund scams typically ask you to confirm/approve a request, leading to a payment from your account.",
    ),
    Rule(
        rule_id="qr_receive_trick",
        title="QR trick (scan/approve to receive)",
        patterns=(
            _pat(r"\bscan\b.*\b(qr|code)\b.*\b(receive|get)\b"),
            _pat(r"\bapprove\b.*\bto\s+get\b"),
            _pat(r"स्कैन\s*कर.*(पैसे|receive)|क्यूआर\s*स्कैन"),
        ),
        severity=70,
        reason="Scanning unknown QR codes or approving requests 'to receive' money is a common payment trick.",
    ),
    Rule(
        rule_id="emotional_manipulation",
        title="Emotional manipulation / help request",
        patterns=(
            _pat(r"\bi\s+need\s+help\b"),
            _pat(r"\bsend\s+money\b.*\b(urgent|asap|soon)\b"),
            _pat(r"\bi\s+will\s+return\b|\bpay\s+back\b"),
            _pat(r"मदद\s*चाहिए|पैसे\s*भेज\s*दो|बाद\s*में\s*लौटा"),
        ),
        severity=35,
        reason="Emotional pressure and repayment promises are common social-engineering tactics in scams.",
    ),
    Rule(
        rule_id="fake_authority",
        title="Fake authority (bank/verification team)",
        patterns=(
            _pat(r"\b(bank|verification|support)\s+team\b"),
            _pat(r"\baccount\s+activity\b|\bsuspicious\s+activity\b"),
            _pat(r"बैंक\s*टीम|वेरिफिकेशन\s*टीम|सपोर्ट\s*टीम"),
        ),
        severity=30,
        reason="Scammers often impersonate banks/support teams to gain trust and push actions.",
    ),
]


def analyze_rules(
    text: str,
    adaptive_weights: Dict[str, float] | None = None,
) -> Tuple[RuleAnalysis, int, List[str]]:
    """
    Returns (rule_analysis, adaptive_score_boost_points, matched_learned_phrases).
    """
    t = text or ""
    tn = _norm(t)
    hits: List[RuleHit] = []
    score = 0
    adaptive_weights = adaptive_weights or {}

    phrase_hits: List[str] = []
    for ph in SCAM_PHRASE_LIBRARY:
        if _norm(ph) and _norm(ph) in tn:
            phrase_hits.append(ph)

    for rule in RULES:
        matched_terms: List[str] = []
        for p in rule.patterns:
            m = p.search(t)
            if m:
                term = (m.group(0) or "").strip()
                if term:
                    matched_terms.append(term)
        if matched_terms:
            # de-dup while preserving order
            dedup: List[str] = []
            seen = set()
            for mt in matched_terms:
                key = mt.lower()
                if key not in seen:
                    seen.add(key)
                    dedup.append(mt[:32])
            hits.append(
                RuleHit(
                    rule_id=rule.rule_id,
                    title=rule.title,
                    severity=rule.severity,
                    reason=rule.reason,
                    matched_terms=dedup[:6],
                )
            )
            # Weighted scoring: critical (+50..70), medium (+20..40), weak (+10..)
            score = min(100, score + int(rule.severity))

    # Additional heuristics
    if re.search(r"\b\d{4,6}\b", t) and re.search(r"\botp\b", t, re.I):
        score = min(100, score + 10)
    if re.search(r"\bupi\b", t, re.I) and re.search(r"\bpin\b", t, re.I):
        score = min(100, score + 15)
    # Synergy boosts: combinations that are especially risky
    if re.search(r"https?://", t) and re.search(r"\b(otp|upi\s*pin|mpin)\b", t, re.I):
        score = min(100, score + 12)
    if re.search(r"\bcollect\b|\brequest\s+money\b", t, re.I) and re.search(r"\b(receive\s+money|to\s+receive)\b", t, re.I):
        score = min(100, score + 12)
    if re.search(r"\banydesk\b|\bteamviewer\b|\bremote\b.*\baccess\b", t, re.I) and re.search(r"\b(bank|upi|kyc|refund|support)\b", t, re.I):
        score = min(100, score + 10)

    # Phrase library adds strong intent signal
    if phrase_hits:
        score = min(100, score + min(35, 12 + 6 * len(phrase_hits)))
        hits.append(
            RuleHit(
                rule_id="phrase_library",
                title="Known scam phrase matched",
                severity=55,
                reason="Message matches a known scam phrase pattern library.",
                matched_terms=[ph[:32] for ph in phrase_hits[:6]],
            )
        )

    # Combination logic (intent + behavior)
    signals = len([h for h in hits if h.rule_id not in ("phrase_library",)])
    if signals >= 2:
        score = min(100, score + min(25, 8 * (signals - 1)))
    if re.search(r"\b(approve|accept|complete)\b", t, re.I) and re.search(r"\b(request|req)\b", t, re.I) and re.search(r"\b(money|payment|upi)\b", t, re.I):
        score = min(100, score + 20)

    # Adaptive learning: phrases from user-reported false negatives
    adaptive_boost = 0
    matched_adaptive: List[str] = []
    for phrase, weight in sorted(adaptive_weights.items(), key=lambda x: -x[1])[:200]:
        pn = _norm(phrase)
        if not pn or len(pn) < 4:
            continue
        if pn in tn:
            boost = min(12, max(3, int(float(weight) * 1.2)))
            adaptive_boost += boost
            matched_adaptive.append(phrase[:64])
    adaptive_boost = min(25, adaptive_boost)
    dedup_ad: List[str] = []
    if adaptive_boost > 0:
        score = min(100, score + adaptive_boost)
        seen_a = set()
        for m in matched_adaptive:
            k = m.lower()
            if k not in seen_a:
                seen_a.add(k)
                dedup_ad.append(m)
        hits.append(
            RuleHit(
                rule_id="adaptive_feedback",
                title="Learned pattern (user feedback)",
                severity=min(100, adaptive_boost * 3),
                reason="Detected pattern from real-world feedback",
                matched_terms=dedup_ad[:8],
            )
        )

    return RuleAnalysis(score=score, hits=hits), adaptive_boost, dedup_ad

