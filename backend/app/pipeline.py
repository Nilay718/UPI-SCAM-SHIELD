from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.agents.decision import merge_decision
from app.agents.explain import build_explanation
from app.agents.explanation_generator import generate_explanation
from app.agents.intent_layer import IntentResult, detect_intent, intent_risk_boost
from app.agents.context_layer import apply_user_context
from app.agents.llm import (
    call_openrouter,
    call_openrouter_enrich_explanation,
    call_openrouter_intent,
)
from app.agents.ocr_line_hints import build_ocr_line_hints
from app.agents.risk import risk_level_from_score
from app.agents.rules import analyze_rules
from app.feedback_db import get_adaptive_phrases, insert_analysis_log
from app.schemas import (
    AdaptiveOut,
    AnalyzeResponseV2,
    AnalyzeResponseVerbose,
    FinalDecisionOut,
    IntentOut,
    InternalEvidence,
    OcrLineHintOut,
    PersonalizationOut,
    RuleAnalysis,
    RuleHit,
)


def _risk_actions(risk: str) -> list[str]:
    if risk == "HIGH":
        return [
            "Stop interacting with the sender immediately.",
            "Do not approve any collect request or scan unknown QR codes.",
            "If money was debited, contact your bank/UPI app support immediately.",
            "Report the incident on the National Cyber Crime Portal (cybercrime.gov.in).",
            "If you shared OTP/UPI PIN, secure your accounts and contact your bank right away.",
        ]
    if risk == "MEDIUM":
        return [
            "Do not share OTP/UPI PIN or banking credentials.",
            "Verify the message via the official app/website (not via links in the message).",
            "Do not approve collect requests unless you intend to pay.",
            "If unsure, call the official support number from your bank/UPI app.",
        ]
    return [
        "No strong scam signals detected, but stay cautious.",
        "Avoid clicking unknown links and never share OTP/UPI PIN.",
        "Verify sender details if the message asks for any action.",
    ]


def _merge_actions(risk: str, llm_actions: list[str] | None) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for a in _risk_actions(risk):
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    for a in (llm_actions or [])[:10]:
        a = str(a).strip()
        if a and a not in seen:
            seen.add(a)
            out.append(a)
    return out[:10]


def _summary_from_reasons(risk: str, reasons: list[str]) -> str:
    blob = " ".join(reasons or []).lower()
    if "otp" in blob or "ओटीपी" in blob:
        return "This message likely attempts credential theft by requesting OTP."
    if "upi pin" in blob or "mpin" in blob or "पिन" in blob:
        return "This message likely attempts to steal your UPI PIN/mPIN to authorize a payment."
    if "collect request" in blob or "collect" in blob or "कलेक्ट" in blob:
        return "This message appears to use a payment approval (collect) trick to make you pay instead of receive money."
    if "remote access" in blob or "anydesk" in blob or "teamviewer" in blob:
        return "This message appears to be an account takeover attempt using remote access / screen sharing."
    if "refund" in blob:
        return "This message appears to be a refund scam designed to make you approve a payment request."
    if risk == "HIGH":
        return "This message shows strong scam strategies (intent + behavioral patterns) and is high risk."
    if risk == "MEDIUM":
        return "This message shows suspicious intent and should be verified via official channels."
    return "This message appears generally safe, with no strong scam indicators detected."


def _merge_llm_intent(
    local: IntentResult,
    llm_t: Optional[Tuple[str, int, str]],
) -> IntentResult:
    if not llm_t:
        return local
    it, conf, _ = llm_t
    if it == "none" and conf < 40:
        return local
    if conf > local.intent_confidence + 10 or (it != "none" and local.intent_type == "none"):
        return IntentResult(
            intent_type=it,
            intent_confidence=min(100, conf),
            secondary_intents=local.secondary_intents,
        )
    if local.intent_confidence >= conf:
        return local
    return IntentResult(
        intent_type=it,
        intent_confidence=min(100, conf),
        secondary_intents=local.secondary_intents,
    )


def _combined_confidence(
    rule_score: int,
    intent_conf: int,
    adaptive_boost: int,
    context_score: int,
    llm_conf_pct: Optional[int],
) -> int:
    adaptive_norm = min(100, int(adaptive_boost) * 4)
    base = (
        0.50 * max(0, min(100, rule_score))
        + 0.20 * max(0, min(100, intent_conf))
        + 0.20 * adaptive_norm
        + 0.10 * max(0, min(100, context_score))
    )
    c = int(round(base))
    if llm_conf_pct is not None:
        c = int(round(0.75 * c + 0.25 * max(0, min(100, llm_conf_pct))))
    return max(0, min(100, c))


def _attach_intent_hit(rule: RuleAnalysis, intent: IntentResult, boost: int) -> RuleAnalysis:
    if intent.intent_type == "none" or boost <= 0:
        return RuleAnalysis(score=min(100, rule.score + boost), hits=list(rule.hits))
    hit = RuleHit(
        rule_id="intent_layer",
        title=f"Detected intent: {intent.intent_type}",
        severity=min(45, intent.intent_confidence // 2 + 5),
        reason="Message intent suggests attempt to trigger a payment or sensitive action.",
        matched_terms=[intent.intent_type],
    )
    return RuleAnalysis(score=min(100, rule.score + boost), hits=[hit] + list(rule.hits))


async def _run_pipeline(
    text: str,
    *,
    extracted_text: Optional[str],
    sender_type: str,
    transaction_context: str,
    user_type: str,
) -> Dict[str, Any]:
    input_text = (text or "").strip()

    local_intent = detect_intent(input_text)
    llm_intent_row = await call_openrouter_intent(input_text)
    merged_intent = _merge_llm_intent(local_intent, llm_intent_row)

    adaptive_map = get_adaptive_phrases()
    rule_base, adaptive_boost, matched_learned = analyze_rules(input_text, adaptive_map)

    iboost = intent_risk_boost(merged_intent)
    rule_with_intent = _attach_intent_hit(rule_base, merged_intent, iboost)

    llm = await call_openrouter(input_text)
    decision = merge_decision(rule_with_intent, llm)

    ctx = apply_user_context(
        decision.risk_score,
        input_text,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )
    personalized_score = ctx.personalized_risk_score
    risk_level = risk_level_from_score(personalized_score)
    is_scam_bool = risk_level == "HIGH" or (
        llm.available and llm.is_scam is True and (llm.confidence or 0) >= 0.65
    )

    if not decision.reasons:
        decision.reasons = build_explanation(rule_with_intent, llm)

    model_used = llm.model_used if llm.available and llm.model_used else ("rules-only" if not llm.available else None)

    llm_conf_pct = int(round((llm.confidence or 0) * 100)) if llm.available and llm.confidence is not None else None

    conf = _combined_confidence(
        rule_score=rule_with_intent.score,
        intent_conf=merged_intent.intent_confidence if merged_intent.intent_type != "none" else 0,
        adaptive_boost=adaptive_boost,
        context_score=ctx.context_score,
        llm_conf_pct=llm_conf_pct,
    )

    actions_list = _merge_actions(risk_level, llm.suggested_actions if llm.available else None)
    summary = _summary_from_reasons(risk_level, decision.reasons[:10])

    fd = FinalDecisionOut(
        risk=risk_level,
        is_scam="YES" if is_scam_bool else "NO",
        confidence=conf,
        reason=decision.reasons[:10],
        summary=summary,
        actions=actions_list,
    )

    explanation = generate_explanation(fd, input_text, intent=merged_intent)

    enrich = await call_openrouter_enrich_explanation(
        input_text,
        {
            "risk": risk_level,
            "is_scam": fd.is_scam,
            "summary": summary,
            "intent": merged_intent.intent_type,
        },
    )
    if enrich:
        explanation = explanation.model_copy(
            update={
                "scammer_wants": enrich.get("scammer_wants") or explanation.scammer_wants,
                "if_you_act": enrich.get("if_you_act") or explanation.if_you_act,
                "why_people_fooled": enrich.get("why_people_fooled") or explanation.why_people_fooled,
            }
        )

    if adaptive_boost > 0 and matched_learned:
        explanation = explanation.model_copy(
            update={
                "learning_note": "This pattern was learned from real user-reported scam cases.",
                "learning_matched_phrases": matched_learned[:15],
            }
        )

    explanation = explanation.model_copy(
        update={
            "confidence_note": (
                "Confidence is based on combined rule detection, intent analysis, and learned patterns. "
                f"Overall: {conf}%."
            )
        }
    )

    matched_for_ocr: List[str] = []
    for h in rule_with_intent.hits:
        matched_for_ocr.extend(h.matched_terms or [])
    matched_for_ocr.extend(matched_learned)
    ocr_hints = build_ocr_line_hints(extracted_text or "", matched_for_ocr)
    ocr_out = [OcrLineHintOut(line=x.line, risk_level=x.risk_level, tooltip=x.tooltip) for x in ocr_hints]

    log_id = insert_analysis_log(
        message_text=input_text,
        extracted_text=extracted_text,
        predicted_is_scam=is_scam_bool,
        predicted_risk_level=risk_level,
        predicted_confidence=conf,
    )

    intent_out = IntentOut(
        intent_type=merged_intent.intent_type,
        intent_confidence=merged_intent.intent_confidence,
    )
    adaptive_out = AdaptiveOut(
        adaptive_score_boost=min(100, adaptive_boost),
        matched_learned_phrases=matched_learned[:20],
    )
    pers_out = PersonalizationOut(
        personalized_risk_score=personalized_score,
        context_score=ctx.context_score,
        context_reason=ctx.context_reason,
        why_risky_for_you=ctx.why_risky_for_you,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )

    return {
        "input": input_text,
        "extracted_text": extracted_text,
        "model_used": model_used,
        "final_decision": fd,
        "explanation": explanation,
        "analysis_log_id": log_id,
        "intent": intent_out,
        "adaptive": adaptive_out,
        "personalization": pers_out,
        "ocr_line_hints": ocr_out if extracted_text else [],
        "internal": InternalEvidence(
            rule_score=rule_with_intent.score,
            rule_hits=rule_with_intent.hits[:10],
            ai_available=bool(llm.available),
            ai_note="AI enabled." if llm.available else (llm.error or "AI unavailable (running in safe mode)."),
            base_rule_score_before_context=decision.risk_score,
            adaptive_score_boost=min(100, adaptive_boost),
            intent_boost_applied=iboost,
            intent=intent_out,
        ),
    }


async def analyze_text(
    text: str,
    *,
    extracted_text: str | None = None,
    sender_type: str = "unknown",
    transaction_context: str = "expected",
    user_type: str = "general",
) -> AnalyzeResponseV2:
    r = await _run_pipeline(
        text,
        extracted_text=extracted_text,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )
    hints = r["ocr_line_hints"]
    return AnalyzeResponseV2(
        input=r["input"],
        extracted_text=r["extracted_text"],
        model_used=r["model_used"],
        final_decision=r["final_decision"],
        explanation=r["explanation"],
        analysis_log_id=r["analysis_log_id"],
        intent=r["intent"],
        adaptive=r["adaptive"],
        personalization=r["personalization"],
        ocr_line_hints=hints if hints else None,
    )


async def analyze_text_verbose(
    text: str,
    *,
    extracted_text: str | None = None,
    sender_type: str = "unknown",
    transaction_context: str = "expected",
    user_type: str = "general",
) -> AnalyzeResponseVerbose:
    r = await _run_pipeline(
        text,
        extracted_text=extracted_text,
        sender_type=sender_type,
        transaction_context=transaction_context,
        user_type=user_type,
    )
    hints = r["ocr_line_hints"]
    return AnalyzeResponseVerbose(
        input=r["input"],
        extracted_text=r["extracted_text"],
        model_used=r["model_used"],
        final_decision=r["final_decision"],
        explanation=r["explanation"],
        analysis_log_id=r["analysis_log_id"],
        intent=r["intent"],
        adaptive=r["adaptive"],
        personalization=r["personalization"],
        ocr_line_hints=hints if hints else None,
        internal=r["internal"],
    )
