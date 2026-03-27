from __future__ import annotations

import json
from typing import Any, Dict, Optional, Tuple

import httpx

from app.schemas import LLMAnalysis
from app.settings import settings


SYSTEM_PROMPT = """You are a fraud detection assistant specialized in Indian UPI/payment scams.
Return ONLY valid JSON with keys:
- is_scam: boolean
- confidence: number 0..1
- reasons: array of short strings
- suggested_actions: array of short strings

Be conservative: mark is_scam=true when there are strong scam signals (OTP requests, urgent threats, suspicious links, collect requests).
Do not include any markdown.
"""

INTENT_SYSTEM_PROMPT = """You classify the PRIMARY intent of a message related to Indian UPI/payment scams.
Return ONLY valid JSON:
{"intent_type":"payment_push_intent|info_extraction_intent|urgency_pressure_intent|authority_impersonation|reward_trap|none","intent_confidence":0-100}
Use intent_confidence as integer 0-100. Pick exactly one intent_type.
"""

ENRICH_SYSTEM_PROMPT = """You improve scam education text for Indian users. Return ONLY valid JSON with keys:
- scammer_wants: one short sentence, plain language
- if_you_act: one short sentence what happens if they comply
- why_people_fooled: one short sentence psychology
No markdown. Keep each under 200 characters."""


def _safe_json_extract(text: str) -> Optional[Dict[str, Any]]:
    """
    Tries to parse JSON even if the model returns extra text.
    Strategy: find the first '{' and last '}' and parse that substring.
    """
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    snippet = text[start : end + 1]
    try:
        return json.loads(snippet)
    except Exception:
        return None


async def call_openrouter(text: str) -> LLMAnalysis:
    api_key = settings.openrouter_api_key
    if not api_key:
        return LLMAnalysis(available=False, error="AI unavailable (running in safe mode).")

    base_url = settings.openrouter_base_url.rstrip("/")
    url = f"{base_url}/chat/completions"

    last_err: Optional[str] = None
    for model in settings.openrouter_model_list:
        try:
            payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Message to analyze:\n{text}"},
                ],
                "temperature": 0.1,
            }

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }

            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.post(url, headers=headers, json=payload)
                if resp.status_code >= 400:
                    last_err = f"{model}: HTTP {resp.status_code} {resp.text[:300]}"
                    continue

                data = resp.json()
                content = (
                    data.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                )
                parsed = _safe_json_extract(content)
                if not isinstance(parsed, dict):
                    last_err = f"{model}: Could not parse JSON response"
                    continue

                is_scam = parsed.get("is_scam")
                conf = parsed.get("confidence")
                reasons = parsed.get("reasons") or []
                actions = parsed.get("suggested_actions") or []

                if not isinstance(is_scam, bool):
                    last_err = f"{model}: JSON missing boolean is_scam"
                    continue

                try:
                    conf_f = float(conf) if conf is not None else None
                    if conf_f is not None:
                        conf_f = max(0.0, min(1.0, conf_f))
                except Exception:
                    conf_f = None

                return LLMAnalysis(
                    available=True,
                    model_used=model,
                    is_scam=is_scam,
                    confidence=conf_f,
                    reasons=[str(x) for x in reasons][:8],
                    suggested_actions=[str(x) for x in actions][:8],
                    raw={"raw_content": content},
                )

        except Exception as e:
            last_err = f"{model}: {type(e).__name__}: {str(e)[:200]}"
            continue

    return LLMAnalysis(available=False, error=last_err or "OpenRouter call failed for all models.")


_VALID_INTENTS = frozenset(
    {
        "payment_push_intent",
        "info_extraction_intent",
        "urgency_pressure_intent",
        "authority_impersonation",
        "reward_trap",
        "none",
    }
)


async def call_openrouter_intent(text: str) -> Optional[Tuple[str, int, str]]:
    """
    LLM intent fallback. Returns (intent_type, confidence 0-100, model_used) or None.
    """
    if not settings.openrouter_api_key or not settings.llm_intent_enabled:
        return None

    models = settings.openrouter_model_list
    if not models:
        return None
    model = (settings.openrouter_model_intent or "").strip() or models[0]

    base_url = settings.openrouter_base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": f"Message:\n{text[:4000]}"},
        ],
        "temperature": 0.1,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=18.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                return None
            data = resp.json()
            content = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            parsed = _safe_json_extract(content)
            if not isinstance(parsed, dict):
                return None
            it = str(parsed.get("intent_type") or "none")
            if it not in _VALID_INTENTS:
                it = "none"
            try:
                ic = int(parsed.get("intent_confidence", 0))
            except (TypeError, ValueError):
                ic = 0
            ic = max(0, min(100, ic))
            return (it, ic, model)
    except Exception:
        return None


async def call_openrouter_enrich_explanation(
    text: str,
    seed: Dict[str, Any],
) -> Optional[Dict[str, str]]:
    """Optional ChatGPT-style refinement for three explanation fields."""
    if not settings.openrouter_api_key or not settings.llm_explanation_enrich_enabled:
        return None

    models = settings.openrouter_model_list
    if not models:
        return None
    model = (settings.openrouter_model_enrich or "").strip() or models[0]

    base_url = settings.openrouter_base_url.rstrip("/")
    url = f"{base_url}/chat/completions"
    user_payload = json.dumps(seed, ensure_ascii=False)[:3500]
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": ENRICH_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"Message:\n{text[:2000]}\n\nCurrent summary JSON:\n{user_payload}",
            },
        ],
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=22.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                return None
            data = resp.json()
            content = (
                data.get("choices", [{}])[0].get("message", {}).get("content", "")
            )
            parsed = _safe_json_extract(content)
            if not isinstance(parsed, dict):
                return None
            out: Dict[str, str] = {}
            for k in ("scammer_wants", "if_you_act", "why_people_fooled"):
                v = parsed.get(k)
                if isinstance(v, str) and v.strip():
                    out[k] = v.strip()[:400]
            return out if out else None
    except Exception:
        return None

