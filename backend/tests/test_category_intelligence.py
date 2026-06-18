import os
import unittest

from fastapi.testclient import TestClient

from app.category_intelligence.llm import constrain_category_intelligence_payload
from app.category_intelligence.models import (
    AttributeSchemaItem,
    CategoryIntelligence,
    DecisionAxis,
    EntityCandidate,
    GraphEdge,
    IntakeQuestion,
    NormalizedCategoryIntelligence,
)
from app.category_intelligence.normalizer import (
    enforce_normalized_category_intelligence,
    normalize_category_intelligence,
)
from app.category_intelligence.service import get_category_intelligence, normalize_category_key
from app.category_intelligence.store import clear_category_intelligence_cache
from app.main import app


class CategoryIntelligenceTests(unittest.TestCase):
    def setUp(self):
        os.environ["LLM_PROVIDER"] = "local"
        clear_category_intelligence_cache()

    def test_normalized_category_key_generation(self):
        self.assertEqual(normalize_category_key(" Robot Vacuum! "), "robot-vacuum")
        self.assertEqual(normalize_category_key("TV for Bright Room"), "tv-for-bright-room")

    def test_cache_hit_behavior(self):
        first_record, first_cached = get_category_intelligence("Robot vacuum")
        second_record, second_cached = get_category_intelligence("Robot vacuum")

        self.assertFalse(first_cached)
        self.assertTrue(second_cached)
        self.assertEqual(first_record.normalized_category_key, second_record.normalized_category_key)
        self.assertEqual(first_record.created_at, second_record.created_at)

    def test_cache_miss_when_prompt_hash_changes(self):
        first_record, first_cached = get_category_intelligence("Robot vacuum", "first context")
        second_record, second_cached = get_category_intelligence("Robot vacuum", "different context")

        self.assertFalse(first_cached)
        self.assertFalse(second_cached)
        self.assertNotEqual(
            first_record.model_metadata["prompt_hash"],
            second_record.model_metadata["prompt_hash"],
        )

    def test_category_intelligence_list_caps(self):
        raw = {
            "category_summary": "summary",
            "buyer_need": "need",
            "key_decision_factors": [f"factor {index}" for index in range(20)],
            "common_entities": [f"entity {index}" for index in range(20)],
            "important_attributes": [f"attribute {index}" for index in range(20)],
            "comparison_dimensions": [f"dimension {index}" for index in range(20)],
            "risks_or_gotchas": [f"risk {index}" for index in range(20)],
            "good_default_recommendation_logic": [f"logic {index}" for index in range(20)],
            "clarifying_questions": [f"question {index}" for index in range(20)],
            "confidence": "medium",
        }

        constrained = constrain_category_intelligence_payload(raw)

        self.assertEqual(len(constrained["key_decision_factors"]), 8)
        self.assertEqual(len(constrained["common_entities"]), 8)
        self.assertEqual(len(constrained["important_attributes"]), 15)
        self.assertEqual(len(constrained["comparison_dimensions"]), 8)
        self.assertEqual(len(constrained["risks_or_gotchas"]), 7)
        self.assertEqual(len(constrained["good_default_recommendation_logic"]), 7)
        self.assertEqual(len(constrained["clarifying_questions"]), 8)

    def test_valid_structured_response_shape(self):
        record, cached = get_category_intelligence("Coffee maker", "single person on the go")
        intelligence = record.raw_intelligence

        self.assertFalse(cached)
        self.assertIsInstance(intelligence.category_summary, str)
        self.assertIsInstance(intelligence.buyer_need, str)
        self.assertIsInstance(intelligence.key_decision_factors, list)
        self.assertIsInstance(intelligence.common_entities, list)
        self.assertIsInstance(intelligence.important_attributes, list)
        self.assertIsInstance(intelligence.comparison_dimensions, list)
        self.assertIsInstance(intelligence.risks_or_gotchas, list)
        self.assertIsInstance(intelligence.good_default_recommendation_logic, list)
        self.assertIsInstance(intelligence.clarifying_questions, list)
        self.assertIn(intelligence.confidence, ["low", "medium", "high"])

    def test_api_happy_path(self):
        client = TestClient(app)
        response = client.post(
            "/api/category-intelligence",
            json={
                "category": "Router",
                "context": "3-story house",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["category"], "Router")
        self.assertFalse(body["cached"])
        self.assertIn("category_summary", body["raw_intelligence"])
        self.assertIn("entity_candidates", body["normalized_intelligence"])

        cached_response = client.post(
            "/api/category-intelligence",
            json={
                "category": "Router",
                "context": "3-story house",
            },
        )
        self.assertTrue(cached_response.json()["cached"])

    def test_category_extract_keeps_category_general(self):
        client = TestClient(app)
        response = client.post(
            "/api/category-extract",
            json={
                "user_input": "I need a quiet low-profile ceiling fan for an old house bedroom.",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["proposed_category"], "Ceiling fan")
        self.assertEqual(body["normalized_category_key"], "ceiling-fan")
        self.assertEqual(body["broader_category"], "Climate control")
        self.assertEqual(len(body["more_specific_categories"]), 3)
        self.assertNotIn("quiet", body["normalized_category_key"])
        self.assertTrue(body["matched_existing_category"])

    def test_category_extract_handles_water_softener(self):
        client = TestClient(app)
        response = client.post(
            "/api/category-extract",
            json={
                "user_input": "I need a water softener.",
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["proposed_category"], "Water softener")
        self.assertEqual(body["normalized_category_key"], "water-softener")
        self.assertEqual(body["broader_category"], "Water treatment")
        self.assertEqual(len(body["more_specific_categories"]), 3)
        self.assertEqual(body["confidence"], "high")

    def test_entity_candidate_extraction(self):
        raw = CategoryIntelligence(
            category_summary="Ceiling fans move air.",
            buyer_need="Quiet bedroom cooling.",
            key_decision_factors=["quiet operation"],
            common_entities=["low-profile fan", "remote control"],
            important_attributes=["blade span", "airflow"],
            comparison_dimensions=["noise", "style"],
            risks_or_gotchas=["ceiling too low"],
            good_default_recommendation_logic=[],
            clarifying_questions=[],
            confidence="high",
        )

        normalized = normalize_category_intelligence("Ceiling fan", raw)
        names = [entity.name for entity in normalized.entity_candidates]
        types = {entity.name: entity.type for entity in normalized.entity_candidates}

        self.assertIn("Low-profile fan", names)
        self.assertIn("Remote control", names)
        self.assertEqual(types["Remote control"], "feature")
        self.assertTrue(any(entity.source_field == "risks_or_gotchas" for entity in normalized.entity_candidates))

    def test_attribute_schema_generation(self):
        raw = CategoryIntelligence(
            category_summary="TVs vary by room fit.",
            buyer_need="Bright room viewing.",
            key_decision_factors=[],
            common_entities=[],
            important_attributes=["brightness", "screen size", "anti-glare"],
            comparison_dimensions=["price/value"],
            risks_or_gotchas=[],
            good_default_recommendation_logic=[],
            clarifying_questions=[],
            confidence="medium",
        )

        normalized = normalize_category_intelligence("TV", raw)
        attributes = {attribute.name: attribute for attribute in normalized.attribute_schema}

        self.assertEqual(attributes["Brightness"].value_type, "number")
        self.assertEqual(attributes["Brightness"].unit, "nits")
        self.assertEqual(attributes["Brightness"].score_direction, "higher_is_better")
        self.assertEqual(attributes["Brightness"].evidence_type, "spec")
        self.assertTrue(attributes["Brightness"].quantifiable)
        self.assertTrue(attributes["Screen size"].comparison_relevant)
        self.assertEqual(attributes["Budget"].value_type, "number")
        self.assertEqual(attributes["Budget"].unit, "usd")
        self.assertEqual(attributes["Budget"].score_direction, "lower_is_better")
        self.assertEqual(attributes["Budget"].evidence_type, "user_preference")
        self.assertTrue(attributes["Budget"].quantifiable)

    def test_attribute_schema_always_includes_budget(self):
        raw = CategoryIntelligence(
            category_summary="Sparse category.",
            buyer_need="Unknown.",
            confidence="low",
        )

        normalized = normalize_category_intelligence("Sparse", raw)
        attributes = {attribute.name: attribute for attribute in normalized.attribute_schema}

        self.assertIn("Budget", attributes)
        self.assertEqual(attributes["Budget"].importance, "high")
        self.assertEqual(attributes["Budget"].score_direction, "lower_is_better")

    def test_entity_candidate_typing_uses_tightened_vocabulary(self):
        raw = CategoryIntelligence(
            category_summary="Ceiling fans move air.",
            buyer_need="Quiet room cooling.",
            key_decision_factors=[],
            common_entities=[
                "remote control",
                "ceiling mount compatibility",
                "noise level",
                "modern style",
                "low-profile fan",
            ],
            important_attributes=[],
            comparison_dimensions=[],
            risks_or_gotchas=["wobbly installation"],
            good_default_recommendation_logic=[],
            clarifying_questions=[],
            confidence="medium",
        )

        normalized = normalize_category_intelligence("Ceiling fan", raw)
        types = {entity.name: entity.type for entity in normalized.entity_candidates}

        self.assertEqual(types["Remote control"], "feature")
        self.assertEqual(types["Ceiling mount compatibility"], "installation_constraint")
        self.assertEqual(types["Noise level"], "performance_metric")
        self.assertEqual(types["Modern style"], "style")
        self.assertEqual(types["Low-profile fan"], "product_type")
        self.assertEqual(types["Wobbly installation"], "risk")

    def test_bike_helmet_entities_do_not_match_accidental_substrings(self):
        raw = CategoryIntelligence(
            category_summary="Bike helmets protect cyclists.",
            buyer_need="Find a safe and comfortable helmet.",
            key_decision_factors=[],
            common_entities=[
                "mountain bike helmet",
                "MIPS-style rotational protection",
                "visor",
                "dial fit system",
            ],
            important_attributes=[],
            comparison_dimensions=[],
            risks_or_gotchas=[],
            good_default_recommendation_logic=[],
            clarifying_questions=[],
            confidence="medium",
        )

        normalized = normalize_category_intelligence("Bike Helmets", raw)
        types = {entity.name: entity.type for entity in normalized.entity_candidates}

        self.assertEqual(types["Mountain bike helmet"], "product_type")
        self.assertEqual(types["MIPS-style rotational protection"], "feature")
        self.assertEqual(types["Visor"], "feature")
        self.assertEqual(types["Dial fit system"], "feature")

    def test_attribute_cap_keeps_budget(self):
        raw = CategoryIntelligence(
            category_summary="Category with many attributes.",
            buyer_need="Compare many things.",
            key_decision_factors=[],
            common_entities=[],
            important_attributes=[f"attribute {index}" for index in range(20)],
            comparison_dimensions=[],
            risks_or_gotchas=[],
            good_default_recommendation_logic=[],
            clarifying_questions=[],
            confidence="medium",
        )

        normalized = normalize_category_intelligence("Many", raw)
        names = [attribute.name for attribute in normalized.attribute_schema]

        self.assertEqual(len(names), 15)
        self.assertIn("Budget", names)

    def test_graph_edge_shape(self):
        raw = CategoryIntelligence(
            category_summary="Routers provide connectivity.",
            buyer_need="Whole-home Wi-Fi.",
            key_decision_factors=["coverage"],
            common_entities=["mesh node"],
            important_attributes=["coverage range"],
            comparison_dimensions=["reliability"],
            risks_or_gotchas=["dead zones"],
            good_default_recommendation_logic=[],
            clarifying_questions=[],
            confidence="medium",
        )

        normalized = normalize_category_intelligence("Router", raw)
        edge = normalized.graph_edges[0].model_dump(by_alias=True)

        self.assertIn("from", edge)
        self.assertIn("relationship", edge)
        self.assertIn("to", edge)
        self.assertIn("confidence", edge)
        self.assertTrue(any(item.relationship == "HAS_ENTITY" for item in normalized.graph_edges))
        self.assertTrue(any(item.relationship == "HAS_ATTRIBUTE" for item in normalized.graph_edges))

    def test_question_to_attribute_mapping(self):
        raw = CategoryIntelligence(
            category_summary="Coffee makers brew coffee.",
            buyer_need="Fast morning coffee.",
            key_decision_factors=[],
            common_entities=[],
            important_attributes=["brew speed", "water reservoir size"],
            comparison_dimensions=[],
            risks_or_gotchas=[],
            good_default_recommendation_logic=[],
            clarifying_questions=["How fast do you need coffee?", "How much water capacity do you want?"],
            confidence="medium",
        )

        normalized = normalize_category_intelligence("Coffee maker", raw)

        self.assertEqual(normalized.intake_questions[0].maps_to_attribute, "Brew speed")
        self.assertEqual(normalized.intake_questions[0].priority, "high")
        self.assertIn(normalized.intake_questions[0].answer_type, ["string", "number", "boolean", "enum", "range"])

    def test_bike_helmet_budget_question_maps_to_budget(self):
        raw = CategoryIntelligence(
            category_summary="Bike helmets protect cyclists.",
            buyer_need="Find a safe and comfortable helmet.",
            key_decision_factors=[],
            common_entities=[],
            important_attributes=[
                "safety certification",
                "rotational-impact protection",
                "fit size range",
                "ventilation",
            ],
            comparison_dimensions=[],
            risks_or_gotchas=[],
            good_default_recommendation_logic=[],
            clarifying_questions=[
                "What type of riding will you use the helmet for?",
                "What is your budget?",
            ],
            confidence="medium",
        )

        normalized = normalize_category_intelligence("Bike Helmets", raw)
        attributes = {attribute.name for attribute in normalized.attribute_schema}

        self.assertIn("Riding style", attributes)
        self.assertEqual(normalized.intake_questions[0].maps_to_attribute, "Riding style")
        self.assertEqual(normalized.intake_questions[1].maps_to_attribute, "Budget")

    def test_llm_normalization_enforcement_repairs_budget_mapping(self):
        raw = CategoryIntelligence(
            category_summary="Bike helmets protect cyclists.",
            buyer_need="Find a safe and comfortable helmet.",
            important_attributes=["safety certification", "fit size range"],
            clarifying_questions=["What is your budget?"],
            confidence="medium",
        )
        llm_normalized = NormalizedCategoryIntelligence(
            entity_candidates=[
                EntityCandidate(
                    name="Bike helmet",
                    type="product_type",
                    synonyms=[],
                    source_field="common_entities",
                )
            ],
            attribute_schema=[
                AttributeSchemaItem(
                    name="Safety certification",
                    value_type="string",
                    unit=None,
                    importance="high",
                    user_visible=True,
                    comparison_relevant=True,
                    score_direction="must_have",
                    evidence_type="expert_rule",
                    quantifiable=False,
                )
            ],
            decision_axes=[
                DecisionAxis(
                    name="Safety vs price",
                    positive_direction="better safety",
                    tradeoff_against="price",
                    derived_from="comparison_dimensions",
                )
            ],
            graph_edges=[],
            intake_questions=[
                IntakeQuestion(
                    question="What is your budget?",
                    maps_to_attribute="Safety certification",
                    priority="high",
                    answer_type="string",
                )
            ],
        )

        enforced = enforce_normalized_category_intelligence("Bike Helmets", raw, llm_normalized)
        attributes = {attribute.name for attribute in enforced.attribute_schema}

        self.assertIn("Budget", attributes)
        self.assertEqual(enforced.intake_questions[0].maps_to_attribute, "Budget")
        self.assertEqual(enforced.intake_questions[0].answer_type, "number")

    def test_llm_normalization_enforcement_repairs_graph_edges(self):
        raw = CategoryIntelligence(
            category_summary="Routers provide connectivity.",
            buyer_need="Whole-home Wi-Fi.",
            important_attributes=["coverage range"],
            confidence="medium",
        )
        llm_normalized = NormalizedCategoryIntelligence(
            entity_candidates=[
                EntityCandidate(
                    name="Mesh router",
                    type="product_type",
                    synonyms=[],
                    source_field="common_entities",
                )
            ],
            attribute_schema=[
                AttributeSchemaItem(
                    name="Coverage range",
                    value_type="range",
                    unit="square_feet",
                    importance="high",
                    user_visible=True,
                    comparison_relevant=True,
                    score_direction="higher_is_better",
                    evidence_type="spec",
                    quantifiable=True,
                )
            ],
            decision_axes=[],
            graph_edges=[
                GraphEdge(
                    **{
                        "from": "Missing node",
                        "relationship": "HAS_ATTRIBUTE",
                        "to": "Coverage range",
                        "confidence": "medium",
                    }
                )
            ],
            intake_questions=[],
        )

        enforced = enforce_normalized_category_intelligence("Router", raw, llm_normalized)
        edges = [edge.model_dump(by_alias=True) for edge in enforced.graph_edges]

        self.assertNotIn("Missing node", {edge["from"] for edge in edges})
        self.assertTrue(
            any(
                edge["from"] == "Router"
                and edge["relationship"] == "HAS_ATTRIBUTE"
                and edge["to"] == "Coverage range"
                for edge in edges
            )
        )

    def test_intake_questions_only_map_to_existing_attributes(self):
        raw = CategoryIntelligence(
            category_summary="Sparse category.",
            buyer_need="Unknown.",
            key_decision_factors=[],
            common_entities=[],
            important_attributes=["brightness"],
            comparison_dimensions=[],
            risks_or_gotchas=[],
            good_default_recommendation_logic=[],
            clarifying_questions=["Do you need sparkle mode?"],
            confidence="low",
        )

        normalized = normalize_category_intelligence("Sparse", raw)
        attribute_names = {attribute.name for attribute in normalized.attribute_schema}

        self.assertTrue(attribute_names)
        self.assertIn(normalized.intake_questions[0].maps_to_attribute, attribute_names)

    def test_graceful_behavior_when_raw_fields_are_missing(self):
        raw = CategoryIntelligence(
            category_summary="Sparse category.",
            buyer_need="Unknown.",
            confidence="low",
        )

        normalized = normalize_category_intelligence("Sparse", raw)

        self.assertEqual(normalized.entity_candidates, [])
        self.assertGreaterEqual(len(normalized.attribute_schema), 1)
        self.assertGreaterEqual(len(normalized.decision_axes), 1)
        self.assertGreaterEqual(len(normalized.graph_edges), 1)


if __name__ == "__main__":
    unittest.main()
