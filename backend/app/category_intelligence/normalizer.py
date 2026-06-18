import re

from app.category_intelligence.models import (
    AttributeSchemaItem,
    CategoryIntelligence,
    DecisionAxis,
    EntityCandidate,
    GraphEdge,
    IntakeQuestion,
    NormalizedCategoryIntelligence,
)
from app.category_intelligence.service_utils import normalize_name


def classify_entity(name: str, source_field: str) -> str:
    text = name.lower()
    words = set(re.findall(r"[a-z0-9]+", text))
    if source_field == "risks_or_gotchas":
        return "risk"
    if "helmet" in words or any(term in text for term in ["fan", "vacuum", "router", "coffee maker", "softener"]):
        return "product_type"
    if any(word in text for word in ["mips", "rotational protection", "rotational-impact", "visor", "system"]):
        return "feature"
    if any(word in words for word in ["style", "finish", "look", "design", "aesthetic", "color"]):
        return "style"
    if any(
        word in text
        for word in [
            "installation",
            "compatibility",
            "mount compatibility",
            "mounting",
            "sizing",
            "setup",
            "size range",
            "head circumference",
        ]
    ):
        return "installation_constraint"
    if any(
        word in text
        for word in [
            "brightness",
            "airflow",
            "speed",
            "coverage",
            "performance",
            "quiet",
            "noise",
            "weight",
            "battery",
            "capacity",
        ]
    ):
        return "performance_metric"
    if any(
        word in text
        for word in ["remote", "app", "button", "control", "motor", "blade", "filter", "bin", "screen", "antenna"]
    ):
        return "feature"
    if source_field in {"important_attributes", "key_decision_factors"}:
        return "feature"
    return "product_type"


def infer_value_type(name: str) -> str:
    text = name.lower()
    if any(word in text for word in ["budget", "price", "cost", "size", "height", "width", "length", "brightness"]):
        return "number"
    if any(word in text for word in ["range", "coverage"]):
        return "range"
    if any(word in text for word in ["has ", "includes", "compatible", "required"]):
        return "boolean"
    if any(word in text for word in ["style", "type", "finish", "control"]):
        return "enum"
    return "string"


def infer_unit(name: str) -> str | None:
    text = name.lower()
    if "price" in text or "budget" in text or "cost" in text:
        return "usd"
    if "height" in text or "width" in text or "length" in text or "size" in text:
        return "inches_or_feet"
    if "brightness" in text:
        return "nits"
    if "coverage" in text:
        return "square_feet"
    return None


def infer_score_direction(name: str) -> str:
    text = name.lower()
    if any(word in text for word in ["budget", "price", "cost", "noise", "weight", "maintenance", "energy use"]):
        return "lower_is_better"
    if any(word in text for word in ["compatible", "compatibility", "certification", "safety", "required", "fit"]):
        return "must_have"
    if any(word in text for word in ["style", "finish", "color", "control", "type", "preference", "design"]):
        return "match_user_preference"
    if any(
        word in text
        for word in [
            "brightness",
            "coverage",
            "airflow",
            "capacity",
            "performance",
            "speed",
            "range",
            "battery life",
            "reliability",
            "warranty",
        ]
    ):
        return "higher_is_better"
    return "informational"


def infer_evidence_type(name: str) -> str:
    text = name.lower()
    if any(word in text for word in ["style", "finish", "color", "control", "type", "preference", "design"]):
        return "user_preference"
    if any(word in text for word in ["quiet", "comfort", "reliability", "ease", "ugly", "attractive"]):
        return "review"
    if any(word in text for word in ["safety", "certification", "installation", "compatibility", "required", "fit"]):
        return "expert_rule"
    if any(
        word in text
        for word in [
            "budget",
            "price",
            "cost",
            "size",
            "height",
            "width",
            "length",
            "weight",
            "brightness",
            "coverage",
            "capacity",
            "noise",
            "airflow",
            "speed",
            "range",
        ]
    ):
        return "spec"
    return "mixed"


def infer_quantifiable(name: str, value_type: str) -> bool:
    text = name.lower()
    if value_type in {"number", "range", "boolean"}:
        return True
    return any(
        word in text
        for word in [
            "budget",
            "price",
            "cost",
            "size",
            "height",
            "width",
            "length",
            "weight",
            "brightness",
            "coverage",
            "capacity",
            "noise",
            "airflow",
            "speed",
            "range",
        ]
    )


def make_attribute(name: str, importance: str = "medium") -> AttributeSchemaItem:
    value_type = infer_value_type(name)
    return AttributeSchemaItem(
        name=normalize_name(name),
        value_type=value_type,
        unit=infer_unit(name),
        importance=importance,
        user_visible=True,
        comparison_relevant=True,
        score_direction=infer_score_direction(name),
        evidence_type=infer_evidence_type(name),
        quantifiable=infer_quantifiable(name, value_type),
    )


def infer_answer_type(question: str, attribute: str) -> str:
    text = f"{question} {attribute}".lower()
    if any(word in text for word in ["budget", "price", "how much", "height", "size", "dimensions"]):
        return "number"
    if text.startswith("do ") or text.startswith("does ") or "yes" in text:
        return "boolean"
    if any(word in text for word in ["which", "what kind", "type"]):
        return "enum"
    return "string"


def split_terms(items: list[str]) -> list[str]:
    terms: list[str] = []
    for item in items:
        for part in re.split(r",|/|;|\band\b", item):
            clean = part.strip(" .")
            if clean:
                terms.append(clean)
    return terms


def dedupe_by_name(items):
    seen = set()
    deduped = []
    for item in items:
        key = item.name.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def closest_attribute_name(question: str, attributes: list[AttributeSchemaItem]) -> str:
    if not attributes:
        return "Budget"

    question_text = question.lower()
    if any(word in question_text for word in ["budget", "price", "cost", "spend"]):
        for attribute in attributes:
            if attribute.name.lower() == "budget":
                return attribute.name

    question_words = set(re.findall(r"[a-z0-9]+", question_text))
    best_attribute = attributes[0]
    best_score = 0

    for attribute in attributes:
        attribute_words = set(re.findall(r"[a-z0-9]+", attribute.name.lower()))
        score = len(question_words.intersection(attribute_words))
        if score > best_score:
            best_score = score
            best_attribute = attribute

    return best_attribute.name


def normalize_category_intelligence(
    category: str,
    raw_intelligence: CategoryIntelligence,
) -> NormalizedCategoryIntelligence:
    entity_candidates = build_entity_candidates(raw_intelligence)[:12]
    attribute_schema = limit_attributes(build_attribute_schema(raw_intelligence), 15)
    decision_axes = build_decision_axes(raw_intelligence)[:8]
    graph_edges = build_graph_edges(category, entity_candidates, attribute_schema, decision_axes)
    intake_questions = build_intake_questions(raw_intelligence, attribute_schema)

    return NormalizedCategoryIntelligence(
        entity_candidates=entity_candidates,
        attribute_schema=attribute_schema,
        decision_axes=decision_axes,
        graph_edges=graph_edges,
        intake_questions=intake_questions,
    )


def enforce_normalized_category_intelligence(
    category: str,
    raw_intelligence: CategoryIntelligence,
    normalized_intelligence: NormalizedCategoryIntelligence,
) -> NormalizedCategoryIntelligence:
    fallback = normalize_category_intelligence(category, raw_intelligence)

    entity_candidates = dedupe_by_name(normalized_intelligence.entity_candidates)[:12]
    attribute_schema = dedupe_by_name(normalized_intelligence.attribute_schema)
    attribute_schema = ensure_budget_attribute(attribute_schema)
    if not attribute_schema:
        attribute_schema = fallback.attribute_schema
    attribute_schema = limit_attributes(attribute_schema, 15)

    decision_axes = dedupe_by_name(normalized_intelligence.decision_axes)[:8]
    if not decision_axes:
        decision_axes = fallback.decision_axes

    graph_edges = repair_graph_edges(
        category=category,
        graph_edges=normalized_intelligence.graph_edges,
        entities=entity_candidates,
        attributes=attribute_schema,
        axes=decision_axes,
    )
    intake_questions = repair_intake_questions(
        normalized_intelligence.intake_questions,
        fallback.intake_questions,
        attribute_schema,
    )

    return NormalizedCategoryIntelligence(
        entity_candidates=entity_candidates,
        attribute_schema=attribute_schema,
        decision_axes=decision_axes,
        graph_edges=graph_edges,
        intake_questions=intake_questions,
    )


def ensure_budget_attribute(attributes: list[AttributeSchemaItem]) -> list[AttributeSchemaItem]:
    if any(attribute.name.lower() == "budget" for attribute in attributes):
        return attributes

    return attributes + [
        AttributeSchemaItem(
            name="Budget",
            value_type="number",
            unit="usd",
            importance="high",
            user_visible=True,
            comparison_relevant=True,
            score_direction="lower_is_better",
            evidence_type="user_preference",
            quantifiable=True,
        )
    ]


def repair_graph_edges(
    category: str,
    graph_edges: list[GraphEdge],
    entities: list[EntityCandidate],
    attributes: list[AttributeSchemaItem],
    axes: list[DecisionAxis],
) -> list[GraphEdge]:
    valid_nodes = {normalize_name(category)}
    valid_nodes.update(entity.name for entity in entities)
    valid_nodes.update(attribute.name for attribute in attributes)
    valid_nodes.update(axis.name for axis in axes)

    repaired = []
    seen = set()
    for edge in graph_edges:
        if edge.from_ not in valid_nodes or edge.to not in valid_nodes:
            continue
        key = (edge.from_, edge.relationship, edge.to)
        if key in seen:
            continue
        seen.add(key)
        repaired.append(edge)

    category_name = normalize_name(category)
    existing_keys = {(edge.from_, edge.relationship, edge.to) for edge in repaired}

    for entity in entities:
        key = (category_name, "HAS_ENTITY", entity.name)
        if key not in existing_keys:
            repaired.append(
                GraphEdge(
                    **{
                        "from": category_name,
                        "relationship": "HAS_ENTITY",
                        "to": entity.name,
                        "confidence": "medium",
                    }
                )
            )

    for attribute in attributes:
        key = (category_name, "HAS_ATTRIBUTE", attribute.name)
        if key not in existing_keys:
            repaired.append(
                GraphEdge(
                    **{
                        "from": category_name,
                        "relationship": "HAS_ATTRIBUTE",
                        "to": attribute.name,
                        "confidence": "medium",
                    }
                )
            )

    if len(attributes) >= 2 and not any(edge.relationship == "TRADEOFF_WITH" for edge in repaired):
        repaired.append(
            GraphEdge(
                **{
                    "from": attributes[0].name,
                    "relationship": "TRADEOFF_WITH",
                    "to": attributes[1].name,
                    "confidence": "low",
                }
            )
        )

    return repaired


def repair_intake_questions(
    questions: list[IntakeQuestion],
    fallback_questions: list[IntakeQuestion],
    attributes: list[AttributeSchemaItem],
) -> list[IntakeQuestion]:
    valid_attribute_names = {attribute.name for attribute in attributes}
    if not valid_attribute_names:
        return fallback_questions

    repaired: list[IntakeQuestion] = []
    source_questions = questions or fallback_questions
    for question in source_questions[:8]:
        mapped_attribute = question.maps_to_attribute
        if "budget" in question.question.lower() and "Budget" in valid_attribute_names:
            mapped_attribute = "Budget"
        elif mapped_attribute not in valid_attribute_names:
            mapped_attribute = closest_attribute_name(question.question, attributes)
        if mapped_attribute not in valid_attribute_names:
            mapped_attribute = "Budget" if "Budget" in valid_attribute_names else attributes[0].name

        repaired.append(
            IntakeQuestion(
                question=question.question,
                maps_to_attribute=mapped_attribute,
                priority=question.priority,
                answer_type=infer_answer_type(question.question, mapped_attribute),
            )
        )

    return repaired


def limit_attributes(attributes: list[AttributeSchemaItem], limit: int) -> list[AttributeSchemaItem]:
    if len(attributes) <= limit:
        return attributes

    budget = next((attribute for attribute in attributes if attribute.name == "Budget"), None)
    limited = attributes[:limit]

    if budget and all(attribute.name != "Budget" for attribute in limited):
        limited[-1] = budget

    return limited


def build_entity_candidates(raw_intelligence: CategoryIntelligence) -> list[EntityCandidate]:
    candidates: list[EntityCandidate] = []
    source_lists = {
        "common_entities": raw_intelligence.common_entities,
        "risks_or_gotchas": raw_intelligence.risks_or_gotchas,
    }

    for source_field, values in source_lists.items():
        for term in split_terms(values):
            candidates.append(
                EntityCandidate(
                    name=normalize_name(term),
                    type=classify_entity(term, source_field),
                    synonyms=[term] if normalize_name(term).lower() != term.lower() else [],
                    source_field=source_field,
                )
            )

    return dedupe_by_name(candidates)


def build_attribute_schema(raw_intelligence: CategoryIntelligence) -> list[AttributeSchemaItem]:
    attributes: list[AttributeSchemaItem] = []
    high_importance_names = set(raw_intelligence.key_decision_factors)

    for item in split_terms(raw_intelligence.important_attributes):
        attributes.append(make_attribute(item, "high" if item in high_importance_names else "medium"))

    question_text = " ".join(raw_intelligence.clarifying_questions).lower()
    existing_names = " ".join(attribute.name.lower() for attribute in attributes)
    if "riding" in question_text and "riding" not in existing_names:
        attributes.append(make_attribute("Riding style", "high"))
    elif "intended use" in question_text and "intended use" not in existing_names:
        attributes.append(make_attribute("Intended use", "high"))

    attributes.append(
        AttributeSchemaItem(
            name="Budget",
            value_type="number",
            unit="usd",
            importance="high",
            user_visible=True,
            comparison_relevant=True,
            score_direction="lower_is_better",
            evidence_type="user_preference",
            quantifiable=True,
        )
    )

    if not attributes:
        attributes.append(
            AttributeSchemaItem(
                name="General fit",
                value_type="string",
                unit=None,
                importance="medium",
                user_visible=True,
                comparison_relevant=True,
                score_direction="match_user_preference",
                evidence_type="user_preference",
                quantifiable=False,
            )
        )

    return dedupe_by_name(attributes)


def build_decision_axes(raw_intelligence: CategoryIntelligence) -> list[DecisionAxis]:
    axes: list[DecisionAxis] = []
    for dimension in split_terms(raw_intelligence.comparison_dimensions):
        name = normalize_name(dimension)
        axes.append(
            DecisionAxis(
                name=name,
                positive_direction=f"better {dimension.lower()}",
                tradeoff_against="price/value" if "price" not in dimension.lower() else "features",
                derived_from="comparison_dimensions",
            )
        )

    if not axes:
        axes.append(
            DecisionAxis(
                name="Overall fit",
                positive_direction="better fit for the user's stated need",
                tradeoff_against="price/value",
                derived_from="fallback",
            )
        )

    return dedupe_by_name(axes)


def build_graph_edges(
    category: str,
    entities: list[EntityCandidate],
    attributes: list[AttributeSchemaItem],
    axes: list[DecisionAxis],
) -> list[GraphEdge]:
    edges: list[GraphEdge] = []
    category_name = normalize_name(category)

    for entity in entities:
        edges.append(
            GraphEdge(
                **{
                    "from": category_name,
                    "relationship": "HAS_ENTITY",
                    "to": entity.name,
                    "confidence": "medium",
                }
            )
        )

    for attribute in attributes:
        edges.append(
            GraphEdge(
                **{
                    "from": category_name,
                    "relationship": "HAS_ATTRIBUTE",
                    "to": attribute.name,
                    "confidence": "medium",
                }
            )
        )

    for entity in entities:
        if entity.type in {"feature", "performance_metric", "style", "risk"} and axes:
            edges.append(
                GraphEdge(
                    **{
                        "from": entity.name,
                        "relationship": "IMPACTS",
                        "to": axes[0].name,
                        "confidence": "low",
                    }
                )
            )

    for entity in entities:
        if entity.type == "risk" and attributes:
            edges.append(
                GraphEdge(
                    **{
                        "from": entity.name,
                        "relationship": "RELATES_TO",
                        "to": attributes[0].name,
                        "confidence": "low",
                    }
                )
            )

    if len(attributes) >= 2:
        edges.append(
            GraphEdge(
                **{
                    "from": attributes[0].name,
                    "relationship": "TRADEOFF_WITH",
                    "to": attributes[1].name,
                    "confidence": "low",
                }
            )
        )

    return edges


def build_intake_questions(
    raw_intelligence: CategoryIntelligence,
    attributes: list[AttributeSchemaItem],
) -> list[IntakeQuestion]:
    questions: list[IntakeQuestion] = []
    valid_attribute_names = {attribute.name for attribute in attributes}
    fallback_attribute = attributes[0].name if attributes else "Budget"

    for index, question in enumerate(raw_intelligence.clarifying_questions):
        mapped_attribute = closest_attribute_name(question, attributes)
        if mapped_attribute not in valid_attribute_names:
            mapped_attribute = fallback_attribute
        answer_type = infer_answer_type(question, mapped_attribute)
        questions.append(
            IntakeQuestion(
                question=question,
                maps_to_attribute=mapped_attribute,
                priority="high" if index == 0 else "medium",
                answer_type=answer_type,
            )
        )

    return questions
