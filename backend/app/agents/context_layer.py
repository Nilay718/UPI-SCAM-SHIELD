from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class ContextResult:
    """User-context adjustment for risk."""

    delta: int  # added to base risk score before clamp
    personalized_risk_score: int
    context_score: int  # 0-100 for confidence blend
    context_reason: str
    why_risky_for_you: str = ""


def _payment_related(text: str) -> bool:
    t = (text or "").lower()
    return bool(
        re.search(
            r"\b(upi|paytm|gpay|phonepe|qr|collect|otp|pin|refund|transfer|payment|money)\b",
            t,
            re.I,
        )
    )


def apply_user_context(
    base_risk_score: int,
    text: str,
    *,
    sender_type: str = "unknown",
    transaction_context: str = "expected",
    user_type: str = "general",
) -> ContextResult:
    """
    sender_type: unknown | known
    transaction_context: expected | unexpected
    user_type: general | elderly | new_user
    """
    st = (sender_type or "unknown").lower().strip()
    tc = (transaction_context or "expected").lower().strip()
    ut = (user_type or "general").lower().strip()

    delta = 0
    reasons: list[str] = []

    if st == "unknown":
        delta += 8
        reasons.append("Unknown sender increases suspicion.")
    elif st == "known":
        delta -= 5
        reasons.append("Known contact slightly lowers baseline risk (still verify payment asks).")

    pay = _payment_related(text)
    if tc == "unexpected" and pay:
        delta += 15
        reasons.append("Unexpected payment-related request increases risk significantly.")
    elif tc == "unexpected":
        delta += 6
        reasons.append("Unexpected context adds some risk.")

    if ut == "elderly":
        delta += 5
        reasons.append("Higher caution for users who are often targeted by scams.")
    elif ut == "new_user":
        delta += 4
        reasons.append("New UPI users are more likely to misunderstand collect/QR tricks.")

    # Triple combo: unknown + unexpected payment ask — strongest everyday risk signal
    if st == "unknown" and tc == "unexpected" and pay:
        delta += 8
        reasons.append(
            "Unexpected payment-related message from an unknown sender is a high-risk combination."
        )

    personalized = max(0, min(100, int(base_risk_score) + delta))

    # context_score 0-100 for confidence formula (neutral ~50, higher when context raises alarm)
    context_score = max(0, min(100, 50 + delta * 2))

    reason = " ".join(reasons) if reasons else "No strong context modifiers applied."

    why = _why_risky_for_you(st, tc, pay, ut)

    return ContextResult(
        delta=delta,
        personalized_risk_score=personalized,
        context_score=context_score,
        context_reason=reason,
        why_risky_for_you=why,
    )


def _why_risky_for_you(
    sender_type: str,
    transaction_context: str,
    payment_related: bool,
    user_type: str,
) -> str:
    """Short, personal explanation — not generic boilerplate."""
    st = (sender_type or "unknown").lower().strip()
    tc = (transaction_context or "expected").lower().strip()
    ut = (user_type or "general").lower().strip()

    if tc == "unexpected" and payment_related:
        if st == "unknown":
            return (
                "This is risky for you because you were not expecting any payment-related message from this sender, "
                "and you cannot be sure who is really on the other side."
            )
        return (
            "This is risky for you because you were not expecting a payment request right now—even familiar contacts "
            "can be impersonated or hacked."
        )

    if tc == "unexpected":
        if st == "unknown":
            return (
                "This is risky for you because the message came out of the blue from someone you do not clearly know, "
                "which makes it easier to rush the wrong action."
            )
        return (
            "This is risky for you because it was unexpected—surprise is often used to stop you from thinking clearly."
        )

    if st == "unknown":
        return (
            "This is risky for you because you cannot verify the sender’s identity from a short message alone—"
            "that is exactly what scammers exploit."
        )

    if st == "known":
        return (
            "This is still worth a careful look for you: even trusted chats can be taken over, and scams often "
            "hide inside normal-looking conversations."
        )

    if ut == "elderly":
        return "This may be extra risky for you because scammers often push harder when they sense someone may need more time to verify."

    if ut == "new_user":
        return "This may be extra risky for you if you are newer to UPI—collect and QR tricks are easier to misunderstand at first."

    return "For your situation, treat any money or OTP step as sensitive until you verify through the official app."
