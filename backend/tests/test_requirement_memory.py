import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.requirement_memory import update_user_requirement_profile


CEILING_FAN_CONTEXT = {
    "attribute_schema": [
        {
            "name": "Noise Level",
            "value_type": "string",
            "importance": "high",
        },
        {
            "name": "Budget",
            "value_type": "number",
            "importance": "high",
            "score_direction": "lower_is_better",
        },
        {
            "name": "Style",
            "value_type": "enum",
            "importance": "medium",
        },
    ],
    "intake_questions": [
        {
            "question": "What is your budget?",
            "maps_to_attribute": "Budget",
            "priority": "high",
            "answer_type": "number",
        },
        {
            "question": "How quiet does it need to be?",
            "maps_to_attribute": "Noise Level",
            "priority": "high",
            "answer_type": "string",
        },
    ],
}


CEILING_FAN_SCHEMA_MATCH_CONTEXT = {
    "entity_candidates": [
        {
            "name": "Dimmable lights",
            "type": "feature",
            "maps_to_attribute": "Lighting Control",
        },
        {
            "name": "Alexa",
            "type": "compatibility_target",
            "maps_to_attribute": "Smart Home Compatibility",
        },
    ],
    "attribute_schema": [
        {
            "name": "Noise Level",
            "value_type": "string",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
        {
            "name": "Lighting Control",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Smart Home Compatibility",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Indoor/Damp/Wet Rating",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
    ],
    "intake_questions": [
        {
            "question": "How quiet does it need to be?",
            "maps_to_attribute": "Noise Level",
            "priority": "high",
            "answer_type": "string",
        },
        {
            "question": "Where will the fan be installed: indoors, damp location, or wet/outdoor location?",
            "maps_to_attribute": "Indoor/Damp/Wet Rating",
            "priority": "high",
            "answer_type": "enum",
        },
    ],
}


CEILING_FAN_UI_FOLLOWUP_CONTEXT = {
    "entity_candidates": [
        {
            "name": "Dimmable lights",
            "type": "feature",
            "maps_to_attribute": "Lighting Control",
        },
        {
            "name": "Alexa",
            "type": "compatibility_target",
            "maps_to_attribute": "Smart Home Compatibility",
        },
        {
            "name": "Remote control",
            "type": "control_feature",
            "maps_to_attribute": "Control Features",
        },
        {
            "name": "Reverse airflow",
            "type": "airflow_feature",
            "maps_to_attribute": "Airflow Features",
        },
    ],
    "attribute_schema": [
        {
            "name": "Noise Level",
            "value_type": "string",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
        {
            "name": "Room size",
            "value_type": "range",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Mounting style",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Indoor/outdoor use",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Lighting Control",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Smart Home Compatibility",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Control Features",
            "value_type": "enum",
            "importance": "medium",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Airflow Features",
            "value_type": "enum",
            "importance": "medium",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
    ],
    "intake_questions": [
        {
            "question": "How quiet does it need to be?",
            "maps_to_attribute": "Noise level",
            "priority": "high",
            "answer_type": "string",
        },
        {
            "question": "What room size does it need to support?",
            "maps_to_attribute": "Room size",
            "priority": "high",
            "answer_type": "range",
        },
        {
            "question": "What mounting style do you need?",
            "maps_to_attribute": "Mounting style",
            "priority": "high",
            "answer_type": "enum",
        },
        {
            "question": "Is this for indoor or outdoor use?",
            "maps_to_attribute": "Indoor/outdoor use",
            "priority": "high",
            "answer_type": "enum",
        },
    ],
}


CEILING_FAN_BAD_VALUE_CONTEXT = {
    "entity_candidates": [
        {
            "name": "Dimmable lights",
            "type": "feature",
            "maps_to_attribute": "Light Kit Included",
        },
        {
            "name": "Color changing LED",
            "type": "feature",
            "maps_to_attribute": "Light Kit Included",
        },
        {
            "name": "Alexa",
            "type": "compatibility_target",
            "maps_to_attribute": "Control Method",
        },
        {
            "name": "Remote",
            "type": "control_feature",
            "maps_to_attribute": "Control Method",
        },
        {
            "name": "Reverse airflow",
            "type": "airflow_feature",
            "maps_to_attribute": "Airflow Features",
        },
    ],
    "attribute_schema": [
        {
            "name": "Ceiling Height",
            "value_type": "range",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Control Method",
            "value_type": "enum",
            "importance": "medium",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Finish",
            "value_type": "enum",
            "importance": "medium",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Light Kit Included",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Mounting Style",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Noise Level",
            "value_type": "string",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
        {
            "name": "Room Size",
            "value_type": "range",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Damp or Wet Rating",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Airflow Features",
            "value_type": "enum",
            "importance": "medium",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
    ],
    "intake_questions": [
        {
            "question": "What ceiling height does the fan need to fit?",
            "maps_to_attribute": "Ceiling Height",
            "priority": "high",
            "answer_type": "range",
        },
        {
            "question": "What control method do you prefer?",
            "maps_to_attribute": "Control Method",
            "priority": "medium",
            "answer_type": "enum",
        },
        {
            "question": "What room size does the fan need to support?",
            "maps_to_attribute": "Room Size",
            "priority": "high",
            "answer_type": "range",
        },
        {
            "question": "How quiet does it need to be?",
            "maps_to_attribute": "Noise Level",
            "priority": "high",
            "answer_type": "string",
        },
    ],
}


ROUTER_CONTEXT = {
    "attribute_schema": [
        {
            "name": "Coverage",
            "value_type": "range",
            "importance": "high",
        },
        {
            "name": "Budget",
            "value_type": "number",
            "importance": "high",
            "score_direction": "lower_is_better",
        },
    ],
    "intake_questions": [
        {
            "question": "What is your budget?",
            "maps_to_attribute": "Budget",
            "priority": "high",
            "answer_type": "number",
        },
    ],
}


CEILING_FAN_MOUNTING_CONTEXT = {
    "entity_candidates": [
        {
            "name": "Flush mount",
            "type": "installation_constraint",
            "source_field": "common_entities",
        },
        {
            "name": "Standard downrod",
            "type": "installation_constraint",
            "source_field": "common_entities",
        },
        {
            "name": "Sloped ceiling mount",
            "type": "installation_constraint",
            "source_field": "common_entities",
        },
    ],
    "attribute_schema": [
        {
            "name": "Mounting Type",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Budget",
            "value_type": "number",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
        {
            "name": "Style",
            "value_type": "enum",
            "importance": "medium",
            "comparison_relevant": True,
        },
    ],
    "intake_questions": [
        {
            "question": "What mounting type do you need?",
            "maps_to_attribute": "Mounting Type",
            "priority": "high",
            "answer_type": "enum",
        },
        {
            "question": "What is your budget?",
            "maps_to_attribute": "Budget",
            "priority": "high",
            "answer_type": "number",
        },
        {
            "question": "What style do you prefer?",
            "maps_to_attribute": "Style",
            "priority": "medium",
            "answer_type": "enum",
        },
    ],
}


ROUTER_BAND_CONTEXT = {
    "entity_candidates": [
        {
            "name": "Dual-band router",
            "type": "product_type",
            "source_field": "common_entities",
        },
        {
            "name": "Tri-band mesh system",
            "type": "product_type",
            "source_field": "common_entities",
        },
        {
            "name": "6 GHz band",
            "type": "feature",
            "source_field": "common_entities",
        },
    ],
    "attribute_schema": [
        {
            "name": "Band Type",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Budget",
            "value_type": "number",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
    ],
    "intake_questions": [
        {
            "question": "What band type do you need?",
            "maps_to_attribute": "Band Type",
            "priority": "high",
            "answer_type": "enum",
        }
    ],
}


TV_CONTEXT = {
    "entity_candidates": [
        {
            "name": "PS5",
            "type": "gaming_console",
            "maps_to_attribute": "Gaming Compatibility",
        },
        {
            "name": "HDMI 2.1",
            "type": "gaming_feature",
            "maps_to_attribute": "Gaming Compatibility",
        },
        {
            "name": "glare",
            "type": "viewing_condition",
            "maps_to_attribute": "Glare Handling",
        },
    ],
    "attribute_schema": [
        {
            "name": "Brightness",
            "value_type": "string",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "higher_is_better",
        },
        {
            "name": "Glare Handling",
            "value_type": "string",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "higher_is_better",
        },
        {
            "name": "Gaming Compatibility",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
    ],
    "intake_questions": [
        {
            "question": "Will you use it in a bright room?",
            "maps_to_attribute": "Brightness",
            "priority": "high",
            "answer_type": "string",
        },
        {
            "question": "Do you need gaming console compatibility such as PS5, Xbox, or HDMI 2.1?",
            "maps_to_attribute": "Gaming Compatibility",
            "priority": "high",
            "answer_type": "enum",
        },
    ],
}


BIKE_HELMET_CONTEXT = {
    "entity_candidates": [
        {
            "name": "MIPS",
            "type": "rotational impact protection",
            "maps_to_attribute": "Rotational Impact Protection",
        },
        {
            "name": "hot weather",
            "type": "riding_condition",
            "maps_to_attribute": "Ventilation",
        },
        {
            "name": "large head",
            "type": "fit_need",
            "maps_to_attribute": "Fit Size Range",
        },
    ],
    "attribute_schema": [
        {
            "name": "Safety Certification",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Rotational Impact Protection",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Fit Size Range",
            "value_type": "range",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Ventilation",
            "value_type": "string",
            "importance": "medium",
            "comparison_relevant": True,
            "score_direction": "higher_is_better",
        },
    ],
    "intake_questions": [
        {
            "question": "Do you want rotational impact protection such as MIPS?",
            "maps_to_attribute": "Rotational Impact Protection",
            "priority": "high",
            "answer_type": "enum",
        },
        {
            "question": "What head size or fit range do you need?",
            "maps_to_attribute": "Fit Size Range",
            "priority": "high",
            "answer_type": "string",
        },
    ],
}


PHASED_CLARIFICATION_CONTEXT = {
    "attribute_schema": [
        {
            "name": "Budget",
            "value_type": "number",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
        {
            "name": "Mounting Type",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "must_have",
        },
        {
            "name": "Style",
            "value_type": "enum",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "match_user_preference",
        },
        {
            "name": "Noise Level",
            "value_type": "string",
            "importance": "medium",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
    ],
    "intake_questions": [
        {
            "question": "What style do you prefer?",
            "maps_to_attribute": "Style",
            "priority": "high",
            "answer_type": "enum",
        },
    ],
    "decision_axes": [
        {
            "name": "Quietness vs price",
            "positive_direction": "lower noise",
            "tradeoff_against": "price",
            "derived_from": "comparison_dimensions",
        }
    ],
}


CEILING_FAN_OPTIONAL_STYLE_CONTEXT = {
    "attribute_schema": [
        {
            "name": "Budget",
            "value_type": "number",
            "importance": "high",
            "comparison_relevant": True,
            "score_direction": "lower_is_better",
        },
        {
            "name": "Style",
            "value_type": "enum",
            "importance": "medium",
            "comparison_relevant": True,
        },
    ],
    "intake_questions": [
        {
            "question": "What is your budget?",
            "maps_to_attribute": "Budget",
            "priority": "high",
            "answer_type": "number",
        },
        {
            "question": "What style do you prefer?",
            "maps_to_attribute": "Style",
            "priority": "medium",
            "answer_type": "enum",
        },
    ],
}


class RequirementMemoryTests(unittest.TestCase):
    def setUp(self):
        os.environ["LLM_PROVIDER"] = "local"

    def test_user_requirement_profile_captures_structured_memory(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt="I need a fan.",
            latest_user_message="My wife hates noisy ones.",
            category_context=CEILING_FAN_CONTEXT,
            updated_at="2026-06-18T19:00:00+00:00",
        )

        noise = next(item for item in profile.requirements if item.attributeName == "Noise Level")

        self.assertEqual(profile.categoryName, "Ceiling fan")
        self.assertEqual(noise.status, "specified")
        self.assertEqual(noise.value, "quiet")
        self.assertEqual(noise.importance, "critical")
        self.assertEqual(noise.source, "explicit_user_statement")
        self.assertGreaterEqual(noise.confidence, 0.9)
        self.assertEqual(noise.evidence, "noisy")
        self.assertEqual(noise.updatedAt, "2026-06-18T19:00:00+00:00")
        self.assertEqual(profile.followUpQuestions[0].mapsToAttribute, "Budget")

    def test_profile_accumulates_and_marks_ignored_attributes(self):
        first = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt="I need a quiet fan.",
            latest_user_message="I need a quiet fan under $250.",
            category_context=CEILING_FAN_CONTEXT,
            updated_at="2026-06-18T19:00:00+00:00",
        )
        second = update_user_requirement_profile(
            first,
            category_name="Ceiling fan",
            original_user_prompt="I need a quiet fan.",
            latest_user_message="I don't care about style.",
            category_context=CEILING_FAN_CONTEXT,
            updated_at="2026-06-18T19:05:00+00:00",
        )

        by_name = {item.attributeName: item for item in second.requirements}

        self.assertEqual(by_name["Noise Level"].value, "quiet")
        self.assertEqual(by_name["Budget"].value, "under $250")
        self.assertEqual(by_name["Budget"].normalizedOperator, "max")
        self.assertEqual(by_name["Budget"].normalizedValue, 250)
        self.assertEqual(by_name["Budget"].unit, "usd")
        self.assertEqual(by_name["Budget"].hardness, "hard")
        self.assertEqual(by_name["Budget"].scoringFunction, "numeric_max")
        self.assertEqual(by_name["Budget"].missingProductDataStrategy, "exclude_if_missing")
        self.assertEqual(by_name["Style"].status, "ignored")
        self.assertEqual(by_name["Style"].hardness, "ignore")
        self.assertEqual(by_name["Style"].scoringFunction, "do_not_score")
        self.assertEqual(by_name["Style"].updatedAt, "2026-06-18T19:05:00+00:00")
        self.assertEqual(second.followUpQuestions, [])

    def test_vague_llm_requirement_prompts_for_more_specific_scoring_value(self):
        class FakeRequirementProvider:
            def generate_json(self, prompt: str):
                self.prompt = prompt
                return (
                    {
                        "requirements": [
                            {
                                "attributeName": "Budget",
                                "status": "specified",
                                "value": "reasonable",
                                "normalizedOperator": "max",
                                "normalizedValue": None,
                                "unit": "usd",
                                "importance": "high",
                                "hardness": "soft",
                                "weight": 0.8,
                                "source": "explicit_user_statement",
                                "confidence": 0.6,
                                "productEvidenceConfidence": None,
                                "missingProductDataStrategy": "manual_review",
                                "scoringFunction": "numeric_max",
                                "needsMoreSpecification": True,
                                "specificationQuestion": "What budget limit should I use in USD?",
                                "evidence": "reasonable budget",
                            }
                        ]
                    },
                    {"provider": "test", "model": "fake-requirement-memory"},
                )

        os.environ["LLM_PROVIDER"] = "openai-compatible"
        fake_provider = FakeRequirementProvider()

        with patch("app.requirement_memory.profile.get_llm_provider", return_value=fake_provider):
            profile = update_user_requirement_profile(
                None,
                category_name="Ceiling fan",
                original_user_prompt="I need a ceiling fan.",
                latest_user_message="I want a reasonable budget.",
                category_context=CEILING_FAN_CONTEXT,
                clarification_prompt_count=2,
                updated_at="2026-06-18T19:07:00+00:00",
            )

        budget = next(item for item in profile.requirements if item.attributeName == "Budget")

        self.assertIn("needsMoreSpecification", fake_provider.prompt)
        self.assertTrue(budget.needsMoreSpecification)
        self.assertEqual(profile.followUpQuestions[0].reason, "requirement_needs_more_specification_for_scoring")
        self.assertEqual(profile.followUpQuestions[0].question, "What budget limit should I use in USD?")

    def test_ceiling_fan_sentence_satisfies_schema_matched_attributes(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt="i need a fan for a living room that is quiet, has dimmable lights and works with Alexa",
            latest_user_message="i need a fan for a living room that is quiet, has dimmable lights and works with Alexa",
            category_context=CEILING_FAN_SCHEMA_MATCH_CONTEXT,
            updated_at="2026-06-18T19:08:00+00:00",
        )

        by_name = {item.attributeName: item for item in profile.requirements}

        self.assertEqual(by_name["Noise Level"].value, "quiet")
        self.assertEqual(by_name["Lighting Control"].value, "dimmable lights")
        self.assertEqual(by_name["Smart Home Compatibility"].value, "Alexa")
        self.assertEqual(by_name["Indoor/Damp/Wet Rating"].value, "indoor/dry")
        self.assertEqual(profile.followUpQuestions, [])

    def test_ceiling_fan_living_room_and_quiet_do_not_get_reasked(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt=(
                "This is for a living room. The fan should have dimmable lights and be controlled by Alexa. "
                "I also want to be able to reverse the flow using the remote. "
                "The fan should create good airflow while being quiet."
            ),
            latest_user_message=(
                "This is for a living room. The fan should have dimmable lights and be controlled by Alexa. "
                "I also want to be able to reverse the flow using the remote. "
                "The fan should create good airflow while being quiet."
            ),
            category_context=CEILING_FAN_UI_FOLLOWUP_CONTEXT,
            updated_at="2026-06-18T19:08:30+00:00",
        )

        by_name = {item.attributeName: item for item in profile.requirements}
        missing = {question.mapsToAttribute for question in profile.followUpQuestions}

        self.assertEqual(by_name["Noise Level"].value, "quiet")
        self.assertEqual(by_name["Indoor/outdoor use"].value, "indoor/dry")
        self.assertEqual(by_name["Lighting Control"].value, "dimmable lights")
        self.assertEqual(by_name["Smart Home Compatibility"].value, "Alexa")
        self.assertNotIn("Noise level", missing)
        self.assertNotIn("Noise Level", missing)
        self.assertNotIn("Indoor/outdoor use", missing)
        self.assertIn("Room size", missing)
        self.assertIn("Mounting style", missing)

    def test_ceiling_fan_intake_question_words_do_not_become_requirement_values(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt=(
                "I need a fan for a bedroom, it should have dimmable lights, with color changing LED. "
                "It needs to be quiet. I'd prefer a brown or black finish."
            ),
            latest_user_message=(
                "I need a fan for a bedroom, it should have dimmable lights, with color changing LED. "
                "It needs to be quiet. I'd prefer a brown or black finish."
            ),
            category_context=CEILING_FAN_BAD_VALUE_CONTEXT,
            updated_at="2026-06-18T19:08:45+00:00",
        )

        by_name = {item.attributeName: item for item in profile.requirements}
        missing = {question.mapsToAttribute for question in profile.followUpQuestions}

        self.assertNotIn("Ceiling Height", by_name)
        self.assertNotIn("Room Size", by_name)
        self.assertEqual(by_name["Noise Level"].value, "quiet")
        self.assertIn("brown or black finish", by_name["Finish"].value.lower())
        self.assertEqual(by_name["Light Kit Included"].value, "dimmable lights")
        self.assertEqual(by_name["Damp or Wet Rating"].value, "indoor/dry")
        self.assertNotEqual(getattr(by_name.get("Control Method"), "value", None), "prefer")
        self.assertNotIn("Noise Level", missing)
        self.assertIn("Ceiling Height", missing)
        self.assertIn("Room Size", missing)

    def test_llm_paraphrases_are_repaired_to_schema_attribute_names(self):
        class FakeRequirementProvider:
            def generate_json(self, prompt: str):
                self.prompt = prompt
                return (
                    {
                        "requirements": [
                            {
                                "attributeName": "Quiet operation",
                                "status": "specified",
                                "value": "quiet",
                                "importance": "critical",
                                "source": "explicit_user_statement",
                                "confidence": 0.95,
                                "evidence": "quiet",
                            },
                            {
                                "attributeName": "Light kit",
                                "status": "specified",
                                "value": "dimmable lights",
                                "importance": "high",
                                "source": "explicit_user_statement",
                                "confidence": 0.9,
                                "evidence": "dimmable lights",
                            },
                            {
                                "attributeName": "Voice assistant compatibility",
                                "status": "specified",
                                "value": "Alexa",
                                "importance": "high",
                                "source": "explicit_user_statement",
                                "confidence": 0.95,
                                "evidence": "works with Alexa",
                            },
                            {
                                "attributeName": "Location rating",
                                "status": "inferred",
                                "value": "indoor/dry",
                                "importance": "high",
                                "source": "inferred_from_user_statement",
                                "confidence": 0.85,
                                "evidence": "living room",
                            },
                        ]
                    },
                    {"provider": "test", "model": "fake-requirement-memory"},
                )

        os.environ["LLM_PROVIDER"] = "openai-compatible"
        fake_provider = FakeRequirementProvider()

        with patch("app.requirement_memory.profile.get_llm_provider", return_value=fake_provider):
            profile = update_user_requirement_profile(
                None,
                category_name="Ceiling fan",
                original_user_prompt="i need a fan for a living room that is quiet, has dimmable lights and works with Alexa",
                latest_user_message="i need a fan for a living room that is quiet, has dimmable lights and works with Alexa",
                category_context=CEILING_FAN_SCHEMA_MATCH_CONTEXT,
                updated_at="2026-06-18T19:09:00+00:00",
            )

        names = {item.attributeName for item in profile.requirements}

        self.assertIn("categoryAttributeMatchingHints", fake_provider.prompt)
        self.assertNotIn("Noise Level when that schema attribute exists", fake_provider.prompt)
        self.assertEqual(
            names,
            {"Noise Level", "Lighting Control", "Smart Home Compatibility", "Indoor/Damp/Wet Rating"},
        )
        self.assertEqual(profile.followUpQuestions, [])

    def test_tv_requirements_use_category_entities_without_category_specific_rules(self):
        profile = update_user_requirement_profile(
            None,
            category_name="TV",
            original_user_prompt="Need a TV for a bright room, no glare, and PS5.",
            latest_user_message="Need a TV for a bright room, no glare, and PS5.",
            category_context=TV_CONTEXT,
            updated_at="2026-06-18T19:11:00+00:00",
        )

        by_name = {item.attributeName: item for item in profile.requirements}
        missing = {question.mapsToAttribute for question in profile.followUpQuestions}

        self.assertEqual(by_name["Brightness"].value, "bright-room friendly")
        self.assertEqual(by_name["Glare Handling"].value, "glare")
        self.assertEqual(by_name["Gaming Compatibility"].value, "PS5")
        self.assertNotIn("Brightness", missing)
        self.assertNotIn("Glare Handling", missing)
        self.assertNotIn("Gaming Compatibility", missing)

    def test_bike_helmet_requirements_use_category_entities_without_category_specific_rules(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Bike helmet",
            original_user_prompt="I want a safe helmet for hot weather. My head is large, MIPS if possible.",
            latest_user_message="I want a safe helmet for hot weather. My head is large, MIPS if possible.",
            category_context=BIKE_HELMET_CONTEXT,
            updated_at="2026-06-18T19:12:00+00:00",
        )

        by_name = {item.attributeName: item for item in profile.requirements}
        missing = {question.mapsToAttribute for question in profile.followUpQuestions}

        self.assertEqual(by_name["Rotational Impact Protection"].value, "MIPS")
        self.assertEqual(by_name["Ventilation"].value, "hot weather")
        self.assertEqual(by_name["Fit Size Range"].value, "large head")
        self.assertNotIn("Rotational Impact Protection", missing)
        self.assertNotIn("Ventilation", missing)
        self.assertIn("Fit Size Range", missing)
        self.assertTrue(by_name["Fit Size Range"].needsMoreSpecification)

    def test_profile_uses_llm_observations_for_ambiguous_language(self):
        class FakeRequirementProvider:
            def generate_json(self, prompt: str):
                self.prompt = prompt
                return (
                    {
                        "requirements": [
                            {
                                "attributeName": "Ease of Use",
                                "status": "inferred",
                                "value": "simple enough for non-technical users",
                                "importance": "high",
                                "source": "inferred_from_user_statement",
                                "confidence": 0.84,
                                "evidence": "my dad will never open an app",
                            }
                        ]
                    },
                    {"provider": "test", "model": "fake-requirement-memory"},
                )

        os.environ["LLM_PROVIDER"] = "openai-compatible"
        fake_provider = FakeRequirementProvider()
        context = {
            "attribute_schema": [
                {
                    "name": "Ease of Use",
                    "value_type": "string",
                    "importance": "high",
                }
            ],
            "intake_questions": [],
        }

        with patch("app.requirement_memory.profile.get_llm_provider", return_value=fake_provider):
            profile = update_user_requirement_profile(
                None,
                category_name="Robot vacuum",
                original_user_prompt="I need a robot vacuum.",
                latest_user_message="My dad will never open an app.",
                category_context=context,
                updated_at="2026-06-18T19:10:00+00:00",
            )

        requirement = profile.requirements[0]

        self.assertIn("requirement_memory_update", fake_provider.prompt)
        self.assertEqual(requirement.attributeName, "Ease of Use")
        self.assertEqual(requirement.status, "inferred")
        self.assertEqual(requirement.source, "inferred_from_user_statement")
        self.assertEqual(requirement.value, "simple enough for non-technical users")

    def test_clarify_response_includes_durable_profile(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "I need a quiet ceiling fan under $250.",
                "category": "Ceiling fan",
                "category_context": CEILING_FAN_CONTEXT,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        profile = body["user_requirement_profile"]
        requirement_names = {item["attributeName"] for item in profile["requirements"]}

        self.assertIn("Noise Level", requirement_names)
        self.assertIn("Budget", requirement_names)
        self.assertEqual(profile["latestUserMessage"], "I need a quiet ceiling fan under $250.")
        self.assertIn("user_requirement_profile", body)

    def test_clarify_does_not_reclassify_selected_category_from_message_text(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "I keep saying fan, but this is really about a TV under $900.",
                "category": "TV",
                "category_context": CEILING_FAN_CONTEXT,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertEqual(body["category"], "TV")
        self.assertEqual(body["user_requirement_profile"]["categoryName"], "TV")
        self.assertIn("Intent Agent: category locked = TV", body["agent_trace"])

    def test_explicit_category_change_resets_requirement_profile(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        first_response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "I need a quiet ceiling fan under $250.",
                "category": "Ceiling fan",
                "category_context": CEILING_FAN_CONTEXT,
            },
        )
        self.assertEqual(first_response.status_code, 200)

        second_response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "Actually I need whole-home coverage for a three-story house.",
                "category": "Router",
                "category_context": ROUTER_CONTEXT,
            },
        )

        self.assertEqual(second_response.status_code, 200)
        body = second_response.json()
        profile = body["user_requirement_profile"]
        requirement_names = {item["attributeName"] for item in profile["requirements"]}

        self.assertEqual(profile["categoryName"], "Router")
        self.assertIn("Coverage", requirement_names)
        self.assertNotIn("Noise Level", requirement_names)
        self.assertIn("Clarify: category changed; reset requirement memory", body["agent_trace"])

    def test_optional_attributes_do_not_block_research_readiness(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "Budget is under $250.",
                "category": "Ceiling fan",
                "category_context": CEILING_FAN_OPTIONAL_STYLE_CONTEXT,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertTrue(body["ready_to_search"])
        self.assertEqual(body["missing_fields"], [])

    def test_first_two_clarification_prompts_only_ask_minimum_critical_requirements(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt="I need a ceiling fan.",
            latest_user_message="I need a ceiling fan.",
            category_context=PHASED_CLARIFICATION_CONTEXT,
            clarification_prompt_count=0,
            updated_at="2026-06-18T20:00:00+00:00",
        )

        self.assertEqual(
            [question.mapsToAttribute for question in profile.followUpQuestions],
            ["Budget", "Mounting Type"],
        )
        self.assertTrue(
            all(question.reason == "missing_absolute_minimum_critical_requirement" for question in profile.followUpQuestions)
        )

    def test_after_two_prompts_uses_mapped_intake_and_decision_axis_questions(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt="I need a ceiling fan.",
            latest_user_message="Budget is under $250 and Mounting Type is flush mount.",
            category_context=PHASED_CLARIFICATION_CONTEXT,
            clarification_prompt_count=2,
            updated_at="2026-06-18T20:05:00+00:00",
        )

        self.assertEqual(
            [question.mapsToAttribute for question in profile.followUpQuestions],
            ["Style", "Noise Level"],
        )
        self.assertEqual(profile.followUpQuestions[0].question, "What style do you prefer?")
        self.assertEqual(profile.followUpQuestions[0].reason, "missing_intake_attribute")
        self.assertEqual(profile.followUpQuestions[1].reason, "missing_decision_axis_tradeoff")

    def test_after_five_prompts_no_more_followups_are_required(self):
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt="I need a ceiling fan.",
            latest_user_message="I need a ceiling fan.",
            category_context=PHASED_CLARIFICATION_CONTEXT,
            clarification_prompt_count=5,
            updated_at="2026-06-18T20:10:00+00:00",
        )

        self.assertEqual(profile.followUpQuestions, [])

    def test_research_becomes_available_after_fifth_clarification_prompt(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        messages = [
            "Budget is under $250.",
            "I am not sure yet.",
            "I still do not know.",
            "No preference yet.",
            "Can decide later.",
        ]
        latest_body = None
        for message in messages:
            response = client.post(
                "/clarify",
                json={
                    "session_id": session_id,
                    "user_id": "test",
                    "message": message,
                    "category": "Ceiling fan",
                    "category_context": PHASED_CLARIFICATION_CONTEXT,
                },
            )
            self.assertEqual(response.status_code, 200)
            latest_body = response.json()

        self.assertTrue(latest_body["ready_to_search"])
        self.assertIn("You can move to research now", latest_body["agent_message"])

    def test_user_can_ask_about_attribute_options_without_setting_requirement(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "What are the options for mounting type?",
                "category": "Ceiling fan",
                "category_context": CEILING_FAN_MOUNTING_CONTEXT,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        requirement_names = {
            item["attributeName"]
            for item in body["user_requirement_profile"]["requirements"]
        }

        self.assertIn("Flush mount", body["agent_message"])
        self.assertIn("Standard downrod", body["agent_message"])
        self.assertIn("Mounting Type", body["missing_fields"])
        self.assertNotIn("Mounting Type", requirement_names)

    def test_mixed_requirement_and_question_extracts_requirement_then_answers_question(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "Budget is under $250. What are the options for mounting type?",
                "category": "Ceiling fan",
                "category_context": CEILING_FAN_MOUNTING_CONTEXT,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()
        by_name = {
            item["attributeName"]: item
            for item in body["user_requirement_profile"]["requirements"]
        }

        self.assertEqual(by_name["Budget"]["value"], "under $250")
        self.assertNotIn("Mounting Type", by_name)
        self.assertIn("Flush mount", body["agent_message"])
        self.assertEqual(body["missing_fields"], ["Mounting Type"])

    def test_llm_mixed_turn_keeps_requirement_and_drops_question_only_attribute(self):
        class FakeRequirementProvider:
            def generate_json(self, prompt: str):
                self.prompt = prompt
                return (
                    {
                        "requirements": [
                            {
                                "attributeName": "Budget",
                                "status": "specified",
                                "value": "under $250",
                                "importance": "critical",
                                "source": "explicit_user_statement",
                                "confidence": 0.96,
                                "evidence": "Budget is under $250",
                            },
                            {
                                "attributeName": "Mounting Type",
                                "status": "specified",
                                "value": "unknown",
                                "importance": "high",
                                "source": "explicit_user_statement",
                                "confidence": 0.5,
                                "evidence": "What are the options for mounting type?",
                            },
                        ]
                    },
                    {"provider": "test", "model": "fake-requirement-memory"},
                )

        os.environ["LLM_PROVIDER"] = "openai-compatible"
        fake_provider = FakeRequirementProvider()

        with patch("app.requirement_memory.profile.get_llm_provider", return_value=fake_provider):
            profile = update_user_requirement_profile(
                None,
                category_name="Ceiling fan",
                original_user_prompt="I need a ceiling fan.",
                latest_user_message="Budget is under $250. What are the options for mounting type?",
                category_context=CEILING_FAN_MOUNTING_CONTEXT,
                updated_at="2026-06-18T19:15:00+00:00",
            )

        by_name = {item.attributeName: item for item in profile.requirements}

        self.assertIn("extract the stated requirement information first", fake_provider.prompt)
        self.assertEqual(by_name["Budget"].value, "under $250")
        self.assertNotIn("Mounting Type", by_name)

    def test_attribute_option_answer_uses_entities_for_other_categories(self):
        client = TestClient(app)
        session_response = client.post("/sessions", json={"user_id": "test"})
        session_id = session_response.json()["session_id"]

        response = client.post(
            "/clarify",
            json={
                "session_id": session_id,
                "user_id": "test",
                "message": "What are the band type options?",
                "category": "Router",
                "category_context": ROUTER_BAND_CONTEXT,
            },
        )

        self.assertEqual(response.status_code, 200)
        body = response.json()

        self.assertIn("Dual-band router", body["agent_message"])
        self.assertIn("Tri-band mesh system", body["agent_message"])
        self.assertIn("Band Type", body["missing_fields"])


if __name__ == "__main__":
    unittest.main()
