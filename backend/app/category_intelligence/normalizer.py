"""Structural repair for CategorySchema output.

Ensures required fields are present, keys are valid snake_case,
duplicates are removed, and list lengths are bounded.
The LLM provides all content; this module only enforces shape.
"""

from app.category_intelligence.models import CategorySchema, DecisionAttribute
from app.category_intelligence.service_utils import to_snake_case

_BUDGET_ATTRIBUTE = DecisionAttribute(
    key="budget",
    name="Budget",
    search_gate=True,
    value_type="number",
    unit="usd",
    score_direction="lower_is_better",
    typical_values=[100, 2000],
    clarifying_question="What's your budget for this purchase?",
    extraction_signals=["budget", "spend", "cost", "price", "how much", "dollars", "afford"],
    assessment_note="Exclude products above budget; prefer options toward the lower end of the range.",
)


def repair_category_schema(category: str, schema: CategorySchema) -> CategorySchema:
    """Apply structural repairs to a CategorySchema produced by the LLM."""
    attributes = _repair_attributes(schema.decision_attributes)
    return CategorySchema(
        category=schema.category or category,
        summary=schema.summary or f"Help the buyer choose the right {category}.",
        decision_attributes=attributes,
        entity_terms=list(dict.fromkeys(t for t in schema.entity_terms if t))[:10],
        risks=[r for r in schema.risks if r][:5],
        confidence=schema.confidence,
    )


def _repair_attributes(attributes: list[DecisionAttribute]) -> list[DecisionAttribute]:
    """Dedup on key, normalize keys to snake_case, ensure Budget, enforce limit."""
    seen_keys: set[str] = set()
    repaired: list[DecisionAttribute] = []

    for attr in attributes:
        key = attr.key.strip() if attr.key.strip() else to_snake_case(attr.name)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        repaired.append(
            DecisionAttribute(
                key=key,
                name=attr.name or key.replace("_", " ").title(),
                search_gate=attr.search_gate,
                value_type=attr.value_type,
                unit=attr.unit,
                score_direction=attr.score_direction,
                typical_values=attr.typical_values,
                clarifying_question=attr.clarifying_question or f"Tell me about your {attr.name or key} needs.",
                extraction_signals=attr.extraction_signals[:12],
                assessment_note=attr.assessment_note,
            )
        )

    budget_attrs = [a for a in repaired if a.key == "budget"]
    non_budget_attrs = [a for a in repaired if a.key != "budget"]

    if not budget_attrs:
        budget_attrs = [_BUDGET_ATTRIBUTE]

    capped = (budget_attrs + non_budget_attrs)[:12]

    if not any(a.search_gate for a in capped):
        first = capped[0]
        capped[0] = DecisionAttribute(**{**first.model_dump(), "search_gate": True})

    return capped
