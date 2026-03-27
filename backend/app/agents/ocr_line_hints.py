from __future__ import annotations

import re
from typing import List, Literal

from pydantic import BaseModel, Field

RiskHint = Literal["high", "medium", "low"]


class OcrLineHint(BaseModel):
    line: str
    risk_level: RiskHint
    tooltip: str


_HIGH_PAT = re.compile(
    r"\b(otp|upi\s*pin|mpin|collect|request\s+money|scan\s+.*qr|approve\s+.*request|"
    r"anydesk|teamviewer|remote\s+access|share\s+.*pin|click\s+.*link|"
    r"ओटीपी|कलेक्ट|पिन|स्कैन)\b",
    re.I,
)
_MED_PAT = re.compile(
    r"\b(urgent|immediately|blocked|suspended|refund|verify|bank\s+team|support\s+team|"
    r"तुरंत|रिफंड|बैंक)\b",
    re.I,
)


def build_ocr_line_hints(extracted_text: str, matched_phrases: List[str]) -> List[OcrLineHint]:
    """Chat-style line risk for OCR output."""
    if not (extracted_text or "").strip():
        return []
    blob = " ".join(matched_phrases).lower()
    out: List[OcrLineHint] = []
    for line in extracted_text.splitlines():
        s = line.strip()
        if not s:
            continue
        low = s.lower()
        tip = ""
        level: RiskHint = "low"
        if _HIGH_PAT.search(low):
            level = "high"
            tip = "Contains a strong scam signal (OTP/PIN, collect, QR, remote access, or link bait)."
        elif _MED_PAT.search(low):
            level = "medium"
            tip = "Contains urgency, refund bait, or impersonation-style wording."
        else:
            for ph in matched_phrases:
                if ph and ph.lower() in low:
                    level = "medium"
                    tip = "Matches a phrase seen in your analysis (rule or learned pattern)."
                    break
        if not tip:
            tip = "No strong keyword hit on this line; still read the full message."
        out.append(OcrLineHint(line=s[:500], risk_level=level, tooltip=tip))
    return out[:80]
