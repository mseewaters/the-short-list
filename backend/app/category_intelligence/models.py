from typing import Literal

from pydantic import BaseModel, Field


class CategoryIntelligence(BaseModel):
    category_summary: str
    buyer_need: str
    key_decision_factors: list[str] = Field(default_factory=list)
    common_entities: list[str] = Field(default_factory=list)
    important_attributes: list[str] = Field(default_factory=list)
    comparison_dimensions: list[str] = Field(default_factory=list)
    risks_or_gotchas: list[str] = Field(default_factory=list)
    good_default_recommendation_logic: list[str] = Field(default_factory=list)
    clarifying_questions: list[str] = Field(default_factory=list)
    confidence: Literal["low", "medium", "high"]


class EntityCandidate(BaseModel):
    name: str
    type: Literal[
        "product_type",
        "feature",
        "installation_constraint",
        "performance_metric",
        "style",
        "risk",
    ]
    synonyms: list[str] = Field(default_factory=list)
    source_field: str


class AttributeSchemaItem(BaseModel):
    name: str
    value_type: Literal["string", "number", "boolean", "enum", "range"]
    unit: str | None = None
    importance: Literal["high", "medium", "low"]
    user_visible: bool
    comparison_relevant: bool
    score_direction: Literal[
        "higher_is_better",
        "lower_is_better",
        "match_user_preference",
        "must_have",
        "informational",
    ]
    evidence_type: Literal["spec", "review", "user_preference", "expert_rule", "mixed"]
    quantifiable: bool


class DecisionAxis(BaseModel):
    name: str
    positive_direction: str
    tradeoff_against: str | None = None
    derived_from: str


class GraphEdge(BaseModel):
    from_: str = Field(alias="from")
    relationship: Literal["HAS_ENTITY", "HAS_ATTRIBUTE", "IMPACTS", "RELATES_TO", "TRADEOFF_WITH"]
    to: str
    confidence: Literal["low", "medium", "high"]


class IntakeQuestion(BaseModel):
    question: str
    maps_to_attribute: str
    priority: Literal["high", "medium", "low"]
    answer_type: Literal["string", "number", "boolean", "enum", "range"]


class NormalizedCategoryIntelligence(BaseModel):
    entity_candidates: list[EntityCandidate] = Field(default_factory=list)
    attribute_schema: list[AttributeSchemaItem] = Field(default_factory=list)
    decision_axes: list[DecisionAxis] = Field(default_factory=list)
    graph_edges: list[GraphEdge] = Field(default_factory=list)
    intake_questions: list[IntakeQuestion] = Field(default_factory=list)


class CategoryIntelligenceRecord(BaseModel):
    category: str
    normalized_category_key: str
    raw_intelligence: CategoryIntelligence
    normalized_intelligence: NormalizedCategoryIntelligence
    created_at: str
    updated_at: str
    model_metadata: dict
