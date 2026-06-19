from typing import Any

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    user_id: str = "default"


class SessionResponse(BaseModel):
    status: str = "ok"
    session_id: str
    user_context: dict | None = None
    messages: list[dict] = Field(default_factory=list)
    search_intent: dict | None = None


class ClarifyRequest(BaseModel):
    session_id: str
    user_id: str = "default"
    message: str
    category: str | None = None
    category_context: dict | None = None


class Requirement(BaseModel):
    label: str
    value: str


class UserRequirement(BaseModel):
    attributeName: str
    status: str
    value: str | int | float | bool | None = None
    normalizedOperator: str = "match"
    normalizedValue: Any = None
    unit: str | None = None
    importance: str
    hardness: str = "soft"
    weight: float = 0.5
    source: str
    confidence: float
    productEvidenceConfidence: float | None = None
    missingProductDataStrategy: str = "penalize_unknown"
    scoringFunction: str = "match_user_preference"
    needsMoreSpecification: bool = False
    specificationQuestion: str | None = None
    evidence: str
    updatedAt: str


class FollowUpQuestion(BaseModel):
    question: str
    mapsToAttribute: str
    priority: str
    reason: str


class UserRequirementProfile(BaseModel):
    categoryName: str | None = None
    originalUserPrompt: str
    latestUserMessage: str
    requirements: list[UserRequirement] = Field(default_factory=list)
    followUpQuestions: list[FollowUpQuestion] = Field(default_factory=list)
    summary: str
    createdAt: str
    updatedAt: str


class ClarifyResponse(BaseModel):
    category: str | None
    requirements: list[Requirement] = Field(default_factory=list)
    user_requirement_profile: UserRequirementProfile | None = None
    missing_fields: list[str] = Field(default_factory=list)
    agent_trace: list[str] = Field(default_factory=list)
    agent_message: str
    ready_to_search: bool


class SearchRequest(BaseModel):
    session_id: str


class CriterionResult(BaseModel):
    label: str
    met: bool
    note: str


class ProductCandidate(BaseModel):
    id: str
    name: str
    price: str
    score: int
    verdict: str
    criteria: list[CriterionResult] = Field(default_factory=list)


class SearchResponse(BaseModel):
    status: str
    candidates: list[ProductCandidate] = Field(default_factory=list)
    recommendation: str


class CategoryIntelligenceRequest(BaseModel):
    category: str
    context: str | None = None


class CategoryIntelligenceResponse(BaseModel):
    category: str
    raw_intelligence: dict
    normalized_intelligence: dict
    cached: bool


class CategoryExtractRequest(BaseModel):
    user_input: str
    additional_context: str | None = None


class CategoryExtractResponse(BaseModel):
    proposed_category: str
    normalized_category_key: str
    broader_category: str
    more_specific_categories: list[str] = Field(default_factory=list)
    confidence: str
    explanation: str
    matched_existing_category: bool
