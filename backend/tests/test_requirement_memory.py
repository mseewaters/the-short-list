import os
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.requirement_memory import update_user_requirement_profile


CEILING_FAN_CONTEXT = {
    "decision_attributes": [
        {
            "key": "noise_level",
            "name": "Noise Level",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "lower_is_better",
            "typical_values": None,
            "clarifying_question": "How quiet does it need to be?",
            "extraction_signals": ["quiet", "noisy", "noise", "silent", "loud"],
            "assessment_note": "",
        },
        {
            "key": "budget",
            "name": "Budget",
            "search_gate": True,
            "value_type": "number",
            "unit": "usd",
            "score_direction": "lower_is_better",
            "typical_values": [50, 500],
            "clarifying_question": "What is your budget?",
            "extraction_signals": ["budget", "spend", "cost", "price", "under $", "less than"],
            "assessment_note": "",
        },
        {
            "key": "style",
            "name": "Style",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["modern", "traditional", "industrial", "farmhouse"],
            "clarifying_question": "What style do you prefer?",
            "extraction_signals": ["style", "design", "look", "aesthetic"],
            "assessment_note": "",
        },
    ],
    "entity_terms": [],
}


CEILING_FAN_SCHEMA_MATCH_CONTEXT = {
    "decision_attributes": [
        {
            "key": "noise_level",
            "name": "Noise Level",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "lower_is_better",
            "typical_values": None,
            "clarifying_question": "How quiet does it need to be?",
            "extraction_signals": ["quiet", "noisy", "noise", "silent"],
            "assessment_note": "",
        },
        {
            "key": "lighting_control",
            "name": "Lighting Control",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["dimmable", "led", "no light", "included"],
            "clarifying_question": "What lighting do you need?",
            "extraction_signals": ["dimmable lights", "dimmable", "dimmer", "lights", "led", "light kit"],
            "assessment_note": "",
        },
        {
            "key": "smart_home_compatibility",
            "name": "Smart Home Compatibility",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["Alexa", "Google Home", "HomeKit", "None"],
            "clarifying_question": "Do you need smart home compatibility?",
            "extraction_signals": ["alexa", "google home", "homekit", "smart home", "voice control", "works with"],
            "assessment_note": "",
        },
        {
            "key": "indoor_damp_wet_rating",
            "name": "Indoor/Damp/Wet Rating",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["indoor/dry", "damp", "wet/outdoor"],
            "clarifying_question": "Where will the fan be installed: indoors, damp, or wet/outdoor?",
            "extraction_signals": ["indoor", "outdoor", "damp", "wet", "location", "rating"],
            "assessment_note": "",
        },
    ],
    "entity_terms": ["Dimmable lights", "Alexa"],
}


CEILING_FAN_UI_FOLLOWUP_CONTEXT = {
    "decision_attributes": [
        {
            "key": "noise_level",
            "name": "Noise Level",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "lower_is_better",
            "typical_values": None,
            "clarifying_question": "How quiet does it need to be?",
            "extraction_signals": ["quiet", "noisy", "noise", "silent"],
            "assessment_note": "",
        },
        {
            "key": "room_size",
            "name": "Room size",
            "search_gate": True,
            "value_type": "range",
            "score_direction": "must_have",
            "typical_values": [75, 400],
            "clarifying_question": "What room size does it need to support?",
            "extraction_signals": ["room size", "sq ft", "square feet", "large room", "small room"],
            "assessment_note": "",
        },
        {
            "key": "mounting_style",
            "name": "Mounting style",
            "search_gate": True,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["flush mount", "standard downrod", "hugger"],
            "clarifying_question": "What mounting style do you need?",
            "extraction_signals": ["flush mount", "low profile", "hugger", "downrod", "sloped ceiling"],
            "assessment_note": "",
        },
        {
            "key": "indoor_outdoor_use",
            "name": "Indoor/outdoor use",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["indoor", "damp", "outdoor"],
            "clarifying_question": "Is this for indoor or outdoor use?",
            "extraction_signals": ["indoor", "outdoor", "damp", "wet"],
            "assessment_note": "",
        },
        {
            "key": "lighting_control",
            "name": "Lighting Control",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["dimmable", "led", "no light"],
            "clarifying_question": "What lighting do you need?",
            "extraction_signals": ["dimmable lights", "dimmable", "dimmer", "lights", "led"],
            "assessment_note": "",
        },
        {
            "key": "smart_home_compatibility",
            "name": "Smart Home Compatibility",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["Alexa", "Google Home", "HomeKit"],
            "clarifying_question": "Do you need smart home compatibility?",
            "extraction_signals": ["alexa", "google home", "homekit", "smart home", "voice control", "works with"],
            "assessment_note": "",
        },
        {
            "key": "control_features",
            "name": "Control Features",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["remote control", "pull chain", "wall switch"],
            "clarifying_question": "What control features do you prefer?",
            "extraction_signals": ["remote control", "remote", "pull chain", "wall control"],
            "assessment_note": "",
        },
        {
            "key": "airflow_features",
            "name": "Airflow Features",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["reverse", "high airflow", "DC motor"],
            "clarifying_question": "What airflow features matter to you?",
            "extraction_signals": ["reverse airflow", "reverse", "reversible", "airflow", "dc motor"],
            "assessment_note": "",
        },
    ],
    "entity_terms": ["Dimmable lights", "Alexa", "Remote control", "Reverse airflow"],
}


CEILING_FAN_BAD_VALUE_CONTEXT = {
    "decision_attributes": [
        {
            "key": "ceiling_height",
            "name": "Ceiling Height",
            "search_gate": True,
            "value_type": "range",
            "score_direction": "must_have",
            "typical_values": [8, 12],
            "clarifying_question": "What ceiling height does the fan need to fit?",
            "extraction_signals": ["ceiling height", "foot ceiling", "feet ceiling", "low ceiling", "high ceiling"],
            "assessment_note": "",
        },
        {
            "key": "control_method",
            "name": "Control Method",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["remote control", "pull chain", "wall switch", "Alexa"],
            "clarifying_question": "What control method do you prefer?",
            "extraction_signals": ["remote control", "pull chain", "wall switch", "alexa", "voice control"],
            "assessment_note": "",
        },
        {
            "key": "finish",
            "name": "Finish",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["brushed nickel", "matte black", "bronze", "white"],
            "clarifying_question": "What finish do you prefer?",
            "extraction_signals": ["matte black", "brushed nickel", "oil rubbed bronze", "antique brass"],
            "assessment_note": "",
        },
        {
            "key": "light_kit_included",
            "name": "Light Kit Included",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["dimmable", "led", "color changing led", "no light"],
            "clarifying_question": "What light kit do you need?",
            "extraction_signals": ["dimmable lights", "dimmable", "color changing led", "led", "light kit"],
            "assessment_note": "",
        },
        {
            "key": "mounting_style",
            "name": "Mounting Style",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["flush mount", "standard downrod", "hugger"],
            "clarifying_question": "What mounting style do you need?",
            "extraction_signals": ["flush mount", "low profile", "hugger", "downrod"],
            "assessment_note": "",
        },
        {
            "key": "noise_level",
            "name": "Noise Level",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "lower_is_better",
            "typical_values": None,
            "clarifying_question": "How quiet does it need to be?",
            "extraction_signals": ["quiet", "noisy", "noise", "silent", "loud"],
            "assessment_note": "",
        },
        {
            "key": "room_size",
            "name": "Room Size",
            "search_gate": True,
            "value_type": "range",
            "score_direction": "must_have",
            "typical_values": [75, 400],
            "clarifying_question": "What room size does the fan need to support?",
            "extraction_signals": ["room size", "sq ft", "square feet", "small room", "large room"],
            "assessment_note": "",
        },
        {
            "key": "damp_or_wet_rating",
            "name": "Damp or Wet Rating",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["indoor/dry", "damp", "wet/outdoor"],
            "clarifying_question": "Is this for indoor, damp, or outdoor use?",
            "extraction_signals": ["indoor", "outdoor", "damp", "wet"],
            "assessment_note": "",
        },
        {
            "key": "airflow_features",
            "name": "Airflow Features",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["reverse", "high airflow"],
            "clarifying_question": "What airflow features matter?",
            "extraction_signals": ["reverse airflow", "reverse", "reversible", "airflow"],
            "assessment_note": "",
        },
    ],
    "entity_terms": ["Dimmable lights", "Color changing LED", "Remote", "Reverse airflow"],
}


ROUTER_CONTEXT = {
    "decision_attributes": [
        {
            "key": "coverage",
            "name": "Coverage",
            "search_gate": True,
            "value_type": "range",
            "score_direction": "higher_is_better",
            "typical_values": [1000, 5000],
            "clarifying_question": "What coverage area do you need?",
            "extraction_signals": ["coverage", "range", "whole home", "whole house", "3-story", "three story"],
            "assessment_note": "",
        },
        {
            "key": "budget",
            "name": "Budget",
            "search_gate": True,
            "value_type": "number",
            "unit": "usd",
            "score_direction": "lower_is_better",
            "typical_values": [50, 400],
            "clarifying_question": "What is your budget?",
            "extraction_signals": ["budget", "spend", "cost", "price", "under"],
            "assessment_note": "",
        },
    ],
    "entity_terms": [],
}


CEILING_FAN_MOUNTING_CONTEXT = {
    "decision_attributes": [
        {
            "key": "mounting_type",
            "name": "Mounting Type",
            "search_gate": True,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["Flush mount", "Standard downrod", "Sloped ceiling mount"],
            "clarifying_question": "What mounting type do you need?",
            "extraction_signals": ["flush mount", "low profile", "sloped ceiling", "standard downrod", "hugger"],
            "assessment_note": "",
        },
        {
            "key": "budget",
            "name": "Budget",
            "search_gate": True,
            "value_type": "number",
            "unit": "usd",
            "score_direction": "lower_is_better",
            "typical_values": [50, 500],
            "clarifying_question": "What is your budget?",
            "extraction_signals": ["budget", "spend", "cost", "price", "under"],
            "assessment_note": "",
        },
        {
            "key": "style",
            "name": "Style",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["modern", "traditional", "industrial"],
            "clarifying_question": "What style do you prefer?",
            "extraction_signals": ["style", "design", "look", "aesthetic"],
            "assessment_note": "",
        },
    ],
    "entity_terms": ["Flush mount", "Standard downrod", "Sloped ceiling mount"],
}


ROUTER_BAND_CONTEXT = {
    "decision_attributes": [
        {
            "key": "band_type",
            "name": "Band Type",
            "search_gate": True,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": None,
            "clarifying_question": "What band type do you need?",
            "extraction_signals": ["dual-band", "tri-band", "6 ghz", "wifi 6", "wi-fi 6e", "mesh system"],
            "assessment_note": "",
        },
        {
            "key": "budget",
            "name": "Budget",
            "search_gate": True,
            "value_type": "number",
            "unit": "usd",
            "score_direction": "lower_is_better",
            "typical_values": [50, 400],
            "clarifying_question": "What is your budget?",
            "extraction_signals": ["budget", "spend", "cost", "price", "under"],
            "assessment_note": "",
        },
    ],
    "entity_terms": ["Dual-band router", "Tri-band mesh system", "6 GHz band"],
}


TV_CONTEXT = {
    "decision_attributes": [
        {
            "key": "brightness",
            "name": "Brightness",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "higher_is_better",
            "typical_values": None,
            "clarifying_question": "Will you use it in a bright room?",
            "extraction_signals": ["bright room", "brightness", "nits", "sunny", "hdr"],
            "assessment_note": "",
        },
        {
            "key": "glare_handling",
            "name": "Glare Handling",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "higher_is_better",
            "typical_values": None,
            "clarifying_question": "Do you need anti-glare?",
            "extraction_signals": ["glare", "anti-glare", "matte screen", "glare handling"],
            "assessment_note": "",
        },
        {
            "key": "gaming_compatibility",
            "name": "Gaming Compatibility",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["PS5", "Xbox", "HDMI 2.1", "VRR", "none"],
            "clarifying_question": "Do you need gaming console compatibility?",
            "extraction_signals": ["ps5", "xbox", "hdmi 2.1", "gaming", "game mode", "vrr"],
            "assessment_note": "",
        },
    ],
    "entity_terms": ["PS5", "HDMI 2.1", "glare"],
}


BIKE_HELMET_CONTEXT = {
    "decision_attributes": [
        {
            "key": "safety_certification",
            "name": "Safety Certification",
            "search_gate": True,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["CPSC", "CE", "MIPS certified"],
            "clarifying_question": "What safety certification do you need?",
            "extraction_signals": ["cpsc", "ce certified", "certified", "safety certified"],
            "assessment_note": "",
        },
        {
            "key": "rotational_impact_protection",
            "name": "Rotational Impact Protection",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["MIPS", "SPIN", "WaveCel", "none"],
            "clarifying_question": "Do you want rotational impact protection such as MIPS?",
            "extraction_signals": ["mips", "spin", "wavecel", "rotational", "impact protection"],
            "assessment_note": "",
        },
        {
            "key": "fit_size_range",
            "name": "Fit Size Range",
            "search_gate": False,
            "value_type": "range",
            "score_direction": "must_have",
            "typical_values": [50, 62],
            "clarifying_question": "What head size or fit range do you need?",
            "extraction_signals": ["head is large", "large head", "small head", "head size", "fit size"],
            "assessment_note": "",
        },
        {
            "key": "ventilation",
            "name": "Ventilation",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "higher_is_better",
            "typical_values": None,
            "clarifying_question": "What ventilation do you need?",
            "extraction_signals": ["hot weather", "ventilation", "vents", "airflow", "breathable"],
            "assessment_note": "",
        },
    ],
    "entity_terms": ["MIPS", "hot weather", "large head"],
}


PHASED_CLARIFICATION_CONTEXT = {
    "decision_attributes": [
        {
            "key": "budget",
            "name": "Budget",
            "search_gate": True,
            "value_type": "number",
            "unit": "usd",
            "score_direction": "lower_is_better",
            "typical_values": [50, 500],
            "clarifying_question": "What is your budget?",
            "extraction_signals": ["budget", "spend", "cost", "price", "under"],
            "assessment_note": "",
        },
        {
            "key": "mounting_type",
            "name": "Mounting Type",
            "search_gate": True,
            "value_type": "enum",
            "score_direction": "must_have",
            "typical_values": ["flush mount", "standard downrod", "hugger"],
            "clarifying_question": "What mounting type do you need?",
            "extraction_signals": ["flush mount", "low profile", "hugger", "downrod", "sloped ceiling"],
            "assessment_note": "",
        },
        {
            "key": "style",
            "name": "Style",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["modern", "traditional", "industrial"],
            "clarifying_question": "What style do you prefer?",
            "extraction_signals": ["style", "design", "look", "aesthetic"],
            "assessment_note": "",
        },
        {
            "key": "noise_level",
            "name": "Noise Level",
            "search_gate": False,
            "value_type": "string",
            "score_direction": "lower_is_better",
            "typical_values": None,
            "clarifying_question": "How quiet does it need to be?",
            "extraction_signals": ["quiet", "noisy", "noise", "silent"],
            "assessment_note": "",
        },
    ],
    "entity_terms": [],
}


CEILING_FAN_OPTIONAL_STYLE_CONTEXT = {
    "decision_attributes": [
        {
            "key": "budget",
            "name": "Budget",
            "search_gate": True,
            "value_type": "number",
            "unit": "usd",
            "score_direction": "lower_is_better",
            "typical_values": [50, 500],
            "clarifying_question": "What is your budget?",
            "extraction_signals": ["budget", "spend", "cost", "price", "under"],
            "assessment_note": "",
        },
        {
            "key": "style",
            "name": "Style",
            "search_gate": False,
            "value_type": "enum",
            "score_direction": "match_preference",
            "typical_values": ["modern", "traditional", "industrial"],
            "clarifying_question": "What style do you prefer?",
            "extraction_signals": ["style", "design", "look", "aesthetic"],
            "assessment_note": "",
        },
    ],
    "entity_terms": [],
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
        self.assertIn("large", by_name["Fit Size Range"].value.lower())
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
            "decision_attributes": [
                {
                    "key": "ease_of_use",
                    "name": "Ease of Use",
                    "search_gate": False,
                    "value_type": "string",
                    "score_direction": "higher_is_better",
                    "typical_values": None,
                    "clarifying_question": "How easy to use does it need to be?",
                    "extraction_signals": ["easy to use", "simple", "user-friendly", "intuitive"],
                    "assessment_note": "",
                }
            ],
            "entity_terms": [],
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
            all(question.reason == "missing_search_gate_requirement" for question in profile.followUpQuestions)
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
            ["Noise Level", "Style"],
        )
        self.assertEqual(profile.followUpQuestions[0].question, "How quiet does it need to be?")
        self.assertEqual(profile.followUpQuestions[0].reason, "missing_attribute")
        self.assertEqual(profile.followUpQuestions[1].reason, "missing_attribute")

    def test_after_five_prompts_unresolved_attributes_still_generate_questions(self):
        # The count-5 cap is removed — search_gate controls blocking, not the count.
        # With no requirements specified, all attributes are still unresolved and
        # follow-up questions should continue to be generated.
        profile = update_user_requirement_profile(
            None,
            category_name="Ceiling fan",
            original_user_prompt="I need a ceiling fan.",
            latest_user_message="I need a ceiling fan.",
            category_context=PHASED_CLARIFICATION_CONTEXT,
            clarification_prompt_count=5,
            updated_at="2026-06-18T20:10:00+00:00",
        )

        self.assertGreater(len(profile.followUpQuestions), 0)
        gate_reasons = {q.reason for q in profile.followUpQuestions}
        self.assertIn("missing_search_gate_requirement", gate_reasons)

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
        # Once ready, the agent acknowledges and offers to search — not a hard stop.
        message_lower = latest_body["agent_message"].lower()
        self.assertTrue(
            "search now" in message_lower or "got it" in message_lower,
            f"Unexpected agent message: {latest_body['agent_message']}",
        )

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

        self.assertIn("do not create a requirement for what they only asked about", fake_provider.prompt)
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
