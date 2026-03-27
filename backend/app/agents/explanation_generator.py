from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from app.schemas import ExplanationBlock, FinalDecisionOut, ScamVerdict

if TYPE_CHECKING:
    from app.agents.intent_layer import IntentResult


def _headline(risk: str, is_scam: ScamVerdict) -> str:
    if risk == "HIGH" or is_scam == "YES":
        return "🚨 Scam Detected"
    if risk == "MEDIUM":
        return "⚠️ Suspicious Message"
    return "✅ Likely Safe"


def _golden_rule(risk: str) -> str:
    if risk == "HIGH":
        return "If you’re asked to approve a request or share OTP/PIN, stop immediately."
    if risk == "MEDIUM":
        return "When in doubt, verify using the official app—never through a message link."
    return "Stay alert: never share OTP/UPI PIN and avoid unknown links."


def _detect_tricks(text_blob: str) -> List[str]:
    b = (text_blob or "").lower()
    tricks: List[str] = []

    def add(name: str) -> None:
        if name not in tricks:
            tricks.append(name)

    if any(x in b for x in ["collect", "request money", "approve request", "accept request"]):
        add("Payment approval trick (collect/request)")
    if any(x in b for x in ["qr", "scan", "scan to receive"]):
        add("QR reverse payment trick")
    if any(x in b for x in ["otp", "one-time password", "ओटीपी"]):
        add("OTP harvesting")
    if any(x in b for x in ["upi pin", "mpin", "पिन"]):
        add("UPI PIN theft")
    if any(x in b for x in ["anydesk", "teamviewer", "remote access", "screen share"]):
        add("Remote access takeover")
    if "refund" in b:
        add("Refund scam")
    if any(x in b for x in ["bank team", "verification team", "account activity", "support team"]):
        add("Fake authority / impersonation")
    if any(x in b for x in ["urgent", "immediately", "right now", "as soon as possible", "तुरंत", "अभी"]):
        add("Urgency pressure")

    return tricks[:3]


def _intent_education(intent: Optional["IntentResult"], blob: str) -> tuple[str, str, str]:
    """scammer_wants, if_you_act, why_people_fooled — plain language defaults."""
    if not intent or intent.intent_type == "none":
        return (
            "Get you to do something quickly—tap a link, approve a request, or share a secret.",
            "You could lose money from your account or give someone control of your UPI/bank access.",
            "The message often sounds official or urgent, so people act before double-checking.",
        )
    it = intent.intent_type
    if it == "payment_push_intent":
        return (
            "Make you approve a payment, collect request, or scan a QR so money goes out of your account.",
            "Money can leave your account in seconds—often while you think you are “receiving” or “verifying”.",
            "Words like “receive money” or “accept request” sound safe, but they can mean you are paying.",
        )
    if it == "info_extraction_intent":
        return (
            "Get your OTP, UPI PIN, or banking details so they can approve transfers as you.",
            "They can empty linked accounts or lock you out while you still have the phone in your hand.",
            "People believe “the bank” or “support” must need these details—but real banks never ask on chat.",
        )
    if it == "urgency_pressure_intent":
        return (
            "Panic you with “blocked account” or “act now” so you skip normal safety checks.",
            "You rush into the wrong click or approval and only realise after money is gone.",
            "Fear shuts down thinking—exactly what scammers want in that moment.",
        )
    if it == "authority_impersonation":
        return (
            "Pretend to be bank, RBI, police, or support so you obey without questioning.",
            "You follow fake instructions and hand over access or approve a fake “verification” payment.",
            "Uniform tone and official words feel trustworthy even when the number or link is fake.",
        )
    if it == "reward_trap":
        return (
            "Use refund, cashback, or prize bait so you “confirm” something that actually pays them.",
            "The “reward” never arrives; instead your account gets debited or details get stolen.",
            "Everyone likes free money—scammers exploit that hope with a believable story.",
        )
    return (
        "Push you into an action that benefits the scammer, not you.",
        "You could lose money or control of your account.",
        "The story is designed to feel normal until it is too late.",
    )


def generate_explanation(
    final_decision: FinalDecisionOut,
    message: str,
    *,
    intent: Optional["IntentResult"] = None,
) -> ExplanationBlock:
    risk = final_decision.risk
    is_scam = final_decision.is_scam
    confidence = final_decision.confidence
    reasons = final_decision.reason or []
    actions = final_decision.actions or []

    headline = _headline(risk, is_scam)
    one_line_verdict = f"Verdict: {is_scam} • Risk: {risk} • Confidence: {confidence}%"

    tricks = _detect_tricks(" ".join([message] + reasons))
    blob = " ".join([message] + reasons).lower()
    scammer_wants, if_you_act, why_people_fooled = _intent_education(intent, blob)

    # Make explanations specific (avoid generic phrasing)
    danger_for_you = ""
    golden = _golden_rule(risk)

    if any(x in blob for x in ["qr", "scan", "क्यूआर", "स्कैन"]):
        danger_for_you = "You may think you are receiving money, but scanning a QR can actually send money out of your account."
        golden = "🔥 Golden Rule: QR scan = money goes OUT, not IN."
    elif any(x in blob for x in ["collect", "request money", "approve request", "accept request", "कलेक्ट", "रिक्वेस्ट"]):
        danger_for_you = "You may think you are accepting a 'receive' request, but a collect/request is you approving a payment."
        golden = "🔥 Golden Rule: Collect request = you PAY."
    elif any(x in blob for x in ["otp", "one-time password", "ओटीपी"]):
        danger_for_you = "Sharing an OTP can let scammers log in or approve transactions in your name."
        golden = "🔥 Golden Rule: OTP is for YOU only—never share it."
    elif any(x in blob for x in ["upi pin", "mpin", "पिन"]):
        danger_for_you = "Sharing UPI PIN/mPIN gives full control to authorize payments from your account."
        golden = "🔥 Golden Rule: UPI PIN stays secret—always."
    elif any(x in blob for x in ["anydesk", "teamviewer", "remote access", "screen share"]):
        danger_for_you = "Remote access apps can give scammers control of your phone and let them initiate payments."
        golden = "🔥 Golden Rule: Never install remote access apps for 'support'."
    elif "refund" in blob:
        danger_for_you = "Refund scams often make you 'confirm' something that actually debits money from your account."
        golden = "🔥 Golden Rule: Refunds come to you—you don’t approve a payment to get a refund."
    elif any(x in blob for x in ["bank team", "verification team", "support team", "account activity", "बैंक टीम", "वेरिफिकेशन"]):
        danger_for_you = "Impersonation messages build trust so you follow instructions without verifying the source."
        golden = "🔥 Golden Rule: Trust the official app, not the message."

    if risk == "HIGH" or is_scam == "YES":
        summary = "This looks like a real UPI scam pattern designed to make you approve a payment or hand over a secret (OTP/PIN)."
        detailed = [
            "Why it works: scammers rely on confusion—'receive money' and 'verification' language makes the action feel safe.",
            "Hidden intent: get you to approve a request / scan a QR / share OTP-PIN so money goes out of your account.",
            "What people misunderstand: a collect request is not 'receiving'—it is a payment approval.",
        ]
    elif risk == "MEDIUM":
        summary = "This message is suspicious and may be social engineering (trying to push you into an unnecessary action)."
        detailed = [
            "Why it works: a slight sense of urgency or authority makes people act fast instead of verifying.",
            "If it asks you to approve/confirm something, it may lead to an unintended debit.",
            "Verify only through official channels (bank/UPI app), not via links or unknown numbers.",
        ]
    else:
        summary = "This message appears generally safe. Still, stay cautious with links and any request to approve something."
        detailed = [
            "No strong scam strategies were detected in the text you provided.",
            "However, scams can be context-dependent—verify if the message asks for any unusual action.",
            "Never share OTP/UPI PIN and do not approve requests unless you intend to pay.",
        ]

    if risk == "HIGH":
        confidence_note = f"Confidence: {confidence}% (based on strong scam pattern match)"
    elif risk == "MEDIUM":
        confidence_note = f"Confidence: {confidence}% (based on multiple suspicious signals)"
    else:
        confidence_note = f"Confidence: {confidence}% (based on low-risk pattern match)"

    # Convert actions into short, clear steps
    action_steps = []
    for a in actions[:6]:
        a = str(a).strip()
        if a:
            action_steps.append(a)

    # Use reasons to enrich detailed analysis without repeating verbatim
    # Keep one short grounding line
    if reasons:
        detailed.insert(0, "Key signals match known UPI scam strategies.")
    if intent and intent.intent_type != "none":
        detailed.insert(
            min(1, len(detailed)),
            f"We read the message’s goal as “{intent.intent_type.replace('_', ' ')}”—not just random words.",
        )

    return ExplanationBlock(
        headline=headline,
        one_line_verdict=one_line_verdict,
        danger_for_you=danger_for_you,
        summary=summary,
        scammer_wants=scammer_wants,
        if_you_act=if_you_act,
        why_people_fooled=why_people_fooled,
        detailed_analysis=detailed[:8],
        common_trick=tricks if tricks else ["General social-engineering attempt"],
        action_steps=action_steps,
        golden_rule=golden,
        confidence_note=confidence_note,
    )

