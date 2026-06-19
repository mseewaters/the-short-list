import os
import unittest

from fastapi.testclient import TestClient

from app.category_intelligence.models import CategorySchema, DecisionAttribute
from app.category_intelligence.normalizer import repair_category_schema
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

    def test_valid_category_schema_shape(self):
        record, cached = get_category_intelligence("Coffee maker", "single person on the go")
        schema = record.category_schema

        self.assertFalse(cached)
        self.assertIsInstance(schema, CategorySchema)
        self.assertIsInstance(schema.category, str)
        self.assertIsInstance(schema.summary, str)
        self.assertIsInstance(schema.decision_attributes, list)
        self.assertIsInstance(schema.entity_terms, list)
        self.assertIsInstance(schema.risks, list)
        self.assertIn(schema.confidence, ["low", "medium", "high"])

    def test_decision_attributes_have_required_fields(self):
        record, _ = get_category_intelligence("Ceiling fan")
        schema = record.category_schema

        self.assertGreater(len(schema.decision_attributes), 0)
        for attribute in schema.decision_attributes:
            self.assertIsInstance(attribute, DecisionAttribute)
            self.assertIsInstance(attribute.key, str)
            self.assertTrue(attribute.key)
            self.assertIsInstance(attribute.name, str)
            self.assertIsInstance(attribute.search_gate, bool)
            self.assertIn(attribute.value_type, ["number", "enum", "boolean", "range", "string"])
            self.assertIn(attribute.score_direction, [
                "higher_is_better", "lower_is_better", "match_preference", "must_have"
            ])
            self.assertIsInstance(attribute.clarifying_question, str)
            self.assertIsInstance(attribute.extraction_signals, list)

    def test_schema_always_includes_budget_attribute(self):
        record, _ = get_category_intelligence("Sparse unknown category xyz")
        schema = record.category_schema
        attribute_names = {a.name for a in schema.decision_attributes}

        self.assertIn("Budget", attribute_names)
        budget = next(a for a in schema.decision_attributes if a.name == "Budget")
        self.assertEqual(budget.score_direction, "lower_is_better")
        self.assertEqual(budget.value_type, "number")

    def test_repair_enforces_budget_when_missing(self):
        schema = CategorySchema(
            category="Test",
            summary="Test summary",
            decision_attributes=[
                DecisionAttribute(
                    key="noise_level",
                    name="Noise Level",
                    search_gate=False,
                    value_type="string",
                    score_direction="lower_is_better",
                    clarifying_question="How quiet?",
                )
            ],
            entity_terms=[],
            risks=[],
        )

        repaired = repair_category_schema("Test", schema)
        attribute_names = {a.name for a in repaired.decision_attributes}

        self.assertIn("Budget", attribute_names)

    def test_repair_deduplicates_attribute_keys(self):
        schema = CategorySchema(
            category="Test",
            summary="Test summary",
            decision_attributes=[
                DecisionAttribute(
                    key="noise_level",
                    name="Noise Level",
                    search_gate=False,
                    value_type="string",
                    score_direction="lower_is_better",
                    clarifying_question="How quiet?",
                ),
                DecisionAttribute(
                    key="noise_level",
                    name="Noise Level duplicate",
                    search_gate=False,
                    value_type="string",
                    score_direction="lower_is_better",
                    clarifying_question="Same key?",
                ),
            ],
            entity_terms=[],
            risks=[],
        )

        repaired = repair_category_schema("Test", schema)
        keys = [a.key for a in repaired.decision_attributes if a.key == "noise_level"]

        self.assertEqual(len(keys), 1)

    def test_repair_caps_attributes_at_twelve(self):
        many_attributes = [
            DecisionAttribute(
                key=f"attribute_{i}",
                name=f"Attribute {i}",
                search_gate=False,
                value_type="string",
                score_direction="match_preference",
                clarifying_question=f"Tell me about attribute {i}?",
            )
            for i in range(20)
        ]
        schema = CategorySchema(
            category="Test",
            summary="Lots of attributes",
            decision_attributes=many_attributes,
            entity_terms=[],
            risks=[],
        )

        repaired = repair_category_schema("Test", schema)

        self.assertLessEqual(len(repaired.decision_attributes), 12)
        attribute_names = {a.name for a in repaired.decision_attributes}
        self.assertIn("Budget", attribute_names)

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
        self.assertIn("category_schema", body)
        schema = body["category_schema"]
        self.assertIn("decision_attributes", schema)
        self.assertIn("entity_terms", schema)
        self.assertIn("risks", schema)

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
        self.assertIn("matched_existing_category", body)

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

    def test_search_gate_attributes_limited_in_count(self):
        record, _ = get_category_intelligence("TV")
        schema = record.category_schema
        search_gate_attrs = [a for a in schema.decision_attributes if a.search_gate]

        self.assertLessEqual(len(search_gate_attrs), 4)

    def test_record_has_metadata_and_timestamps(self):
        record, _ = get_category_intelligence("Blender")

        self.assertIsInstance(record.created_at, str)
        self.assertIsInstance(record.updated_at, str)
        self.assertIsInstance(record.model_metadata, dict)
        self.assertIn("prompt_hash", record.model_metadata)
        self.assertEqual(record.normalized_category_key, "blender")


if __name__ == "__main__":
    unittest.main()
