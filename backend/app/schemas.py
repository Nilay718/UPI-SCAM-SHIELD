from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

RiskLevel = Literal["LOW", "MEDIUM", "HIGH"]
ScamVerdict = Literal["YES", "NO"]


class RuleHit(BaseModel):
    rule_id: str
    title: str
    severity: int = Field(ge=0, le=100)
    reason: str
    matched_terms: List[str] = Field(default_factory=list)


class RuleAnalysis(BaseModel):
    score: int = Field(ge=0, le=100)
    hits: List[RuleHit] = Field(default_factory=list)


class LLMAnalysis(BaseModel):
    model_config = {"protected_namespaces": ()}
    available: bool = False
    model_used: Optional[str] = None
    is_scam: Optional[bool] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    reasons: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)
    raw: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[str] = None


class FinalDecision(BaseModel):
    risk_level: RiskLevel
    is_scam: bool
    risk_score: int = Field(ge=0, le=100)
    reasons: List[str] = Field(default_factory=list)
    suggested_actions: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    input_text: str
    extracted_text: Optional[str] = None
    rule_analysis: RuleAnalysis
    llm_analysis: LLMAnalysis
    decision: FinalDecision


class FinalDecisionOut(BaseModel):
    risk: RiskLevel
    is_scam: ScamVerdict
    confidence: int = Field(ge=0, le=100)
    reason: List[str] = Field(default_factory=list)
    summary: str = ""
    actions: List[str] = Field(default_factory=list)


class ExplanationBlock(BaseModel):
    headline: str
    one_line_verdict: str
    danger_for_you: str = ""
    summary: str
    scammer_wants: str = ""
    if_you_act: str = ""
    why_people_fooled: str = ""
    learning_note: str = ""
    learning_matched_phrases: List[str] = Field(default_factory=list)
    detailed_analysis: List[str] = Field(default_factory=list)
    common_trick: List[str] = Field(default_factory=list)
    action_steps: List[str] = Field(default_factory=list)
    golden_rule: str
    confidence_note: str = ""


class IntentOut(BaseModel):
    intent_type: str
    intent_confidence: int = Field(ge=0, le=100)


class AdaptiveOut(BaseModel):
    adaptive_score_boost: int = Field(ge=0, le=100)
    matched_learned_phrases: List[str] = Field(default_factory=list)


class PersonalizationOut(BaseModel):
    personalized_risk_score: int = Field(ge=0, le=100)
    context_score: int = Field(ge=0, le=100)
    context_reason: str
    why_risky_for_you: str = ""
    sender_type: str = "unknown"
    transaction_context: str = "expected"
    user_type: str = "general"


class OcrLineHintOut(BaseModel):
    line: str
    risk_level: Literal["high", "medium", "low"]
    tooltip: str


class AnalyzeResponseV2(BaseModel):
    model_config = {"protected_namespaces": ()}
    input: str
    extracted_text: Optional[str] = None
    model_used: Optional[str] = None
    final_decision: FinalDecisionOut
    explanation: Optional[ExplanationBlock] = None
    analysis_log_id: Optional[int] = None
    intent: Optional[IntentOut] = None
    adaptive: Optional[AdaptiveOut] = None
    personalization: Optional[PersonalizationOut] = None
    ocr_line_hints: Optional[List[OcrLineHintOut]] = None


class InternalEvidence(BaseModel):
    rule_score: int = Field(ge=0, le=100)
    rule_hits: List[RuleHit] = Field(default_factory=list)
    ai_available: bool = False
    ai_note: Optional[str] = None
    base_rule_score_before_context: int = Field(ge=0, le=100, default=0)
    adaptive_score_boost: int = Field(ge=0, le=100, default=0)
    intent_boost_applied: int = Field(ge=0, le=100, default=0)
    intent: Optional[IntentOut] = None


class AnalyzeResponseVerbose(BaseModel):
    model_config = {"protected_namespaces": ()}
    input: str
    extracted_text: Optional[str] = None
    model_used: Optional[str] = None
    final_decision: FinalDecisionOut
    explanation: Optional[ExplanationBlock] = None
    analysis_log_id: Optional[int] = None
    intent: Optional[IntentOut] = None
    adaptive: Optional[AdaptiveOut] = None
    personalization: Optional[PersonalizationOut] = None
    ocr_line_hints: Optional[List[OcrLineHintOut]] = None
    internal: InternalEvidence


class FeedbackRequest(BaseModel):
    input_text: str
    extracted_text: Optional[str] = None
    predicted_risk_level: RiskLevel
    predicted_is_scam: bool
    user_label: Literal["SCAM", "NOT_SCAM"]
    analysis_log_id: Optional[int] = None

