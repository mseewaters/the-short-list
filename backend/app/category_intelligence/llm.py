import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Protocol

from app.category_intelligence.models import CategoryIntelligence, NormalizedCategoryIntelligence
from app.category_intelligence.prompts import (
    build_category_extraction_prompt,
    build_category_intelligence_prompt,
    build_category_normalization_prompt,
)


class CategoryIntelligenceError(Exception):
    pass


class LLMProvider(Protocol):
    def generate_json(self, prompt: str) -> tuple[dict, dict]:
        pass


def load_local_env() -> None:
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if not env_path.exists():
        return

    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


class LocalCategoryIntelligenceProvider:
    def generate_json(self, prompt: str) -> tuple[dict, dict]:
        data = json.loads(prompt.split("\n\n", 1)[1])
        if "user_input" in data:
            return local_category_extraction(data), {
                "provider": "local",
                "model": "deterministic-category-extraction",
            }
        if "raw_intelligence" in data:
            return local_category_normalization(data), {
                "provider": "local",
                "model": "deterministic-category-normalization",
            }

        category = data["category"]
        context = data.get("context") or "general consumer purchase"

        intelligence = {
            "category_summary": f"{category} is a consumer product category with practical tradeoffs.",
            "buyer_need": f"The buyer needs help choosing {category} for {context}.",
            "key_decision_factors": [
                "fit for the user's situation",
                "ease of use",
                "reliability",
                "price/value",
            ],
            "common_entities": [
                "entry-level option",
                "mid-range option",
                "premium option",
            ],
            "important_attributes": [
                "size or compatibility",
                "performance",
                "maintenance",
                "controls",
            ],
            "comparison_dimensions": [
                "must-have fit",
                "nice-to-have features",
                "tradeoffs",
                "confidence",
            ],
            "risks_or_gotchas": [
                "marketing claims may hide real limitations",
                "specs may not map cleanly to the user's real need",
            ],
            "good_default_recommendation_logic": [
                "exclude options that fail must-have requirements",
                "prefer simple, reliable products over feature-heavy ones",
                "surface uncertainty instead of hiding it",
            ],
            "clarifying_questions": [
                "What is your budget?",
                "Where will this be used?",
                "What would make a product a bad fit?",
            ],
            "confidence": "medium",
        }

        return intelligence, {"provider": "local", "model": "deterministic-category-intelligence"}


class OpenAICompatibleProvider:
    def __init__(self) -> None:
        load_local_env()
        self.api_key = os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL") or "gpt-4.1-mini"
        self.base_url = os.getenv("LLM_BASE_URL") or "https://api.openai.com/v1/chat/completions"

        if not self.api_key:
            raise CategoryIntelligenceError("LLM_API_KEY or OPENAI_API_KEY is required")

    def generate_json(self, prompt: str) -> tuple[dict, dict]:
        body = {
            "model": self.model,
            "messages": [
                {
                    "role": "system",
                    "content": "Return only valid JSON. No markdown.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.2,
        }
        request = urllib.request.Request(
            self.base_url,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = json.loads(response.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise CategoryIntelligenceError("LLM request failed") from exc

        try:
            content = response_body["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
            raise CategoryIntelligenceError("LLM returned invalid JSON") from exc

        metadata = {
            "provider": "openai-compatible",
            "model": self.model,
            "base_url": self.base_url,
        }
        return parsed, metadata


def get_llm_provider() -> LLMProvider:
    load_local_env()
    provider = os.getenv("LLM_PROVIDER", "local").lower()

    if provider in {"local", "mock", "deterministic"}:
        return LocalCategoryIntelligenceProvider()
    if provider in {"openai", "openai-compatible"}:
        return OpenAICompatibleProvider()

    raise CategoryIntelligenceError(f"Unsupported LLM_PROVIDER: {provider}")


def get_llm_config_metadata() -> dict:
    load_local_env()
    provider = os.getenv("LLM_PROVIDER", "local").lower()

    if provider in {"local", "mock", "deterministic"}:
        return {
            "provider": "local",
            "model": "deterministic-category-intelligence",
        }

    if provider in {"openai", "openai-compatible"}:
        return {
            "provider": "openai-compatible",
            "model": os.getenv("LLM_MODEL") or os.getenv("DEFAULT_MODEL") or "gpt-4.1-mini",
        }

    return {
        "provider": provider,
        "model": "unknown",
    }


def generate_category_intelligence(category: str, context: str | None = None) -> tuple[CategoryIntelligence, dict]:
    prompt = build_category_intelligence_prompt(category=category, context=context)
    raw_intelligence, metadata = get_llm_provider().generate_json(prompt)
    raw_intelligence = constrain_category_intelligence_payload(raw_intelligence)

    try:
        return CategoryIntelligence(**raw_intelligence), metadata
    except Exception as exc:
        raise CategoryIntelligenceError("LLM response did not match category intelligence schema") from exc


def generate_normalized_category_intelligence(
    category: str,
    raw_intelligence: CategoryIntelligence,
) -> tuple[NormalizedCategoryIntelligence, dict]:
    prompt = build_category_normalization_prompt(
        category=category,
        raw_intelligence=raw_intelligence.model_dump(),
    )
    raw_normalized, metadata = get_llm_provider().generate_json(prompt)

    try:
        return NormalizedCategoryIntelligence(**raw_normalized), metadata
    except Exception as exc:
        raise CategoryIntelligenceError("LLM response did not match normalized intelligence schema") from exc


def constrain_category_intelligence_payload(raw_intelligence: dict) -> dict:
    max_lengths = {
        "key_decision_factors": 8,
        "common_entities": 8,
        "important_attributes": 15,
        "comparison_dimensions": 8,
        "risks_or_gotchas": 7,
        "good_default_recommendation_logic": 7,
        "clarifying_questions": 8,
    }

    constrained = dict(raw_intelligence)
    for field, max_length in max_lengths.items():
        value = constrained.get(field)
        if isinstance(value, list):
            constrained[field] = dedupe_list(value)[:max_length]

    return constrained


def dedupe_list(items: list) -> list:
    seen = set()
    deduped = []
    for item in items:
        key = str(item).strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def local_category_normalization(data: dict) -> dict:
    category = data["category"]
    raw = data["raw_intelligence"]
    attributes = []

    for index, attribute in enumerate(raw.get("important_attributes", [])[:12]):
        attributes.append(local_attribute(attribute, "high" if index < 3 else "medium"))

    if all(attribute["name"].lower() != "budget" for attribute in attributes):
        attributes.append(
            {
                "name": "Budget",
                "value_type": "number",
                "unit": "usd",
                "importance": "high",
                "user_visible": True,
                "comparison_relevant": True,
                "score_direction": "lower_is_better",
                "evidence_type": "user_preference",
                "quantifiable": True,
            }
        )

    if not attributes:
        attributes.append(local_attribute("General fit", "medium"))

    entities = []
    for entity in raw.get("common_entities", [])[:8]:
        entities.append(
            {
                "name": title_text(entity),
                "type": "product_type",
                "synonyms": [],
                "source_field": "common_entities",
            }
        )

    for risk in raw.get("risks_or_gotchas", [])[:3]:
        entities.append(
            {
                "name": title_text(risk),
                "type": "risk",
                "synonyms": [],
                "source_field": "risks_or_gotchas",
            }
        )

    axes = [
        {
            "name": title_text(dimension),
            "positive_direction": f"better {dimension.lower()}",
            "tradeoff_against": "price/value",
            "derived_from": "comparison_dimensions",
        }
        for dimension in raw.get("comparison_dimensions", [])[:6]
    ]
    if not axes:
        axes.append(
            {
                "name": "Overall fit",
                "positive_direction": "better fit for the user's stated need",
                "tradeoff_against": "price/value",
                "derived_from": "fallback",
            }
        )

    graph_edges = []
    for entity in entities:
        graph_edges.append(
            {
                "from": title_text(category),
                "relationship": "HAS_ENTITY",
                "to": entity["name"],
                "confidence": "medium",
            }
        )
    for attribute in attributes:
        graph_edges.append(
            {
                "from": title_text(category),
                "relationship": "HAS_ATTRIBUTE",
                "to": attribute["name"],
                "confidence": "medium",
            }
        )

    questions = []
    for index, question in enumerate(raw.get("clarifying_questions", [])[:8]):
        mapped_attribute = "Budget" if "budget" in question.lower() else attributes[min(index, len(attributes) - 1)]["name"]
        questions.append(
            {
                "question": question,
                "maps_to_attribute": mapped_attribute,
                "priority": "high" if index == 0 else "medium",
                "answer_type": "number" if mapped_attribute == "Budget" else "string",
            }
        )

    return {
        "entity_candidates": entities,
        "attribute_schema": attributes,
        "decision_axes": axes,
        "graph_edges": graph_edges,
        "intake_questions": questions,
    }


def local_attribute(name: str, importance: str) -> dict:
    lowered = name.lower()
    value_type = "number" if any(word in lowered for word in ["price", "budget", "size", "weight"]) else "string"
    return {
        "name": title_text(name),
        "value_type": value_type,
        "unit": "usd" if any(word in lowered for word in ["price", "budget"]) else None,
        "importance": importance,
        "user_visible": True,
        "comparison_relevant": True,
        "score_direction": (
            "lower_is_better"
            if any(word in lowered for word in ["price", "budget", "weight"])
            else "match_user_preference"
        ),
        "evidence_type": "user_preference" if "budget" in lowered else "mixed",
        "quantifiable": value_type == "number",
    }


def title_text(text: str) -> str:
    return str(text).strip().capitalize()


def local_category_extraction(data: dict) -> dict:
    text = f"{data.get('user_input', '')} {data.get('additional_context', '')}".lower()
    proposed_category = "Unknown product"
    confidence = "low"

    if "water softener" in text:
        proposed_category = "Water softener"
        confidence = "high"
    elif "ceiling fan" in text or " fan" in text:
        proposed_category = "Ceiling fan"
        confidence = "high"
    elif "robot vacuum" in text or "roomba" in text:
        proposed_category = "Robot vacuum"
        confidence = "high"
    elif "coffee maker" in text or "coffee" in text:
        proposed_category = "Coffee maker"
        confidence = "high"
    elif "router" in text or "wi-fi" in text or "wifi" in text:
        proposed_category = "Router"
        confidence = "high"
    elif "tv" in text or "television" in text:
        proposed_category = "TV"
        confidence = "high"

    return {
        "proposed_category": proposed_category,
        "broader_category": local_broader_category(proposed_category),
        "more_specific_categories": local_more_specific_categories(proposed_category),
        "confidence": confidence,
        "explanation": (
            f"The core reusable category is {proposed_category}. "
            "Specific needs and usage context belong in the Understand stage."
        ),
    }


def generate_category_extraction(user_input: str, additional_context: str | None = None) -> tuple[dict, dict]:
    prompt = build_category_extraction_prompt(
        user_input=user_input,
        additional_context=additional_context,
    )
    raw_extraction, metadata = get_llm_provider().generate_json(prompt)

    if not isinstance(raw_extraction.get("proposed_category"), str):
        raise CategoryIntelligenceError("LLM category extraction missing proposed_category")
    if not isinstance(raw_extraction.get("broader_category"), str):
        raise CategoryIntelligenceError("LLM category extraction missing broader_category")
    if not isinstance(raw_extraction.get("more_specific_categories"), list):
        raise CategoryIntelligenceError("LLM category extraction missing more_specific_categories")
    if raw_extraction.get("confidence") not in {"low", "medium", "high"}:
        raise CategoryIntelligenceError("LLM category extraction returned invalid confidence")
    if not isinstance(raw_extraction.get("explanation"), str):
        raise CategoryIntelligenceError("LLM category extraction missing explanation")

    return raw_extraction, metadata


def local_broader_category(category: str) -> str:
    broader = {
        "Ceiling fan": "Climate control",
        "Robot vacuum": "Floor care",
        "TV": "Home entertainment",
        "Coffee maker": "Kitchen appliances",
        "Router": "Home networking",
        "Water softener": "Water treatment",
    }
    return broader.get(category, "Home products")


def local_more_specific_categories(category: str) -> list[str]:
    specific = {
        "Ceiling fan": [
            "Low profile ceiling fans",
            "Smart ceiling fans",
            "Ceiling fans with lights",
        ],
        "Robot vacuum": [
            "Self-emptying robot vacuums",
            "Robot vacuums for pet hair",
            "Robot vacuum and mop combos",
        ],
        "TV": [
            "Bright room TVs",
            "OLED TVs",
            "Mini LED TVs",
        ],
        "Coffee maker": [
            "Single-serve coffee makers",
            "Travel mug coffee makers",
            "Compact coffee makers",
        ],
        "Router": [
            "Mesh Wi-Fi systems",
            "Wi-Fi 6 routers",
            "Whole-home router systems",
        ],
        "Water softener": [
            "Salt-based water softeners",
            "Salt-free water conditioners",
            "Whole-house water softeners",
        ],
    }
    return specific.get(category, [f"{category} systems", f"Compact {category}", f"Premium {category}"])
