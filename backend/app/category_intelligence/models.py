from typing import Any, Literal

from pydantic import BaseModel, Field


class DecisionAttribute(BaseModel):
    key: str                          # stable snake_case identifier, e.g. "noise_level"
    name: str                         # display name, e.g. "Noise Level"
    search_gate: bool                 # True = must be resolved (value OR "don't care") before search
    value_type: Literal["number", "enum", "boolean", "range", "string"]
    unit: str | None = None           # "dB", "inches", "usd", "sq_ft" — None for enum/bool/string
    score_direction: Literal[
        "higher_is_better",
        "lower_is_better",
        "match_preference",
        "must_have",
    ]
    typical_values: list[Any] | None = None   # [min, max] for number/range; option list for enum
    clarifying_question: str          # full sentence to ask the user
    extraction_signals: list[str] = Field(default_factory=list)   # phrases users say for this attribute
    assessment_note: str = ""         # one-sentence scoring guidance


class CategorySchema(BaseModel):
    category: str
    summary: str                      # one-sentence buyer need
    decision_attributes: list[DecisionAttribute] = Field(default_factory=list)
    entity_terms: list[str] = Field(default_factory=list)   # product-type terms users commonly name
    risks: list[str] = Field(default_factory=list)          # purchase gotchas
    confidence: Literal["low", "medium", "high"] = "medium"


class CategoryIntelligenceRecord(BaseModel):
    category: str
    normalized_category_key: str
    category_schema: CategorySchema
    created_at: str
    updated_at: str
    model_metadata: dict
