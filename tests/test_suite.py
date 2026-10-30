"""
Automated Test Suite for SafePlate AI
Tests deterministic allergen screening, Gemma 2 recipe generation, profile storage, and pantry tracking.
"""

import sys
import unittest
import json
import tempfile
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from allergy_engine import AllergyEngine
from pantry_store import PantryStore

class TestAllergyEngine(unittest.TestCase):
    def setUp(self):
        self.engine = AllergyEngine()

    def test_engine_status(self):
        status = self.engine.get_status()
        self.assertIn("connected", status)
        self.assertIn("model", status)
        self.assertIn("privacy_mode", status)

    def test_deterministic_screening_detects_hazards(self):
        # Scan text containing wheat flour and peanuts for Alex
        text = "Delicious stir fry with chicken, soy sauce, broccoli, and crushed peanuts"
        res = self.engine.scan_ingredients_deterministic(text, ["gluten", "tree_nuts"])
        self.assertFalse(res["safe"])
        self.assertGreaterEqual(res["hazard_count"], 2)
        triggers = [h["matched_trigger"] for h in res["flagged_hazards"]]
        self.assertIn("soy sauce", triggers)
        self.assertIn("peanuts", triggers)

    def test_deterministic_screening_approves_safe_food(self):
        # Scan 100% safe food for Alex
        text = "Pan-seared salmon with jasmine rice, steamed carrots, extra virgin olive oil, and sea salt"
        res = self.engine.scan_ingredients_deterministic(text, ["gluten", "tree_nuts"])
        self.assertTrue(res["safe"])
        self.assertEqual(res["hazard_count"], 0)

    def test_recipe_generation(self):
        res = self.engine.generate_safe_meal(
            friend_name="Alex",
            allergies=["gluten", "tree_nuts"],
            severity="Severe Celiac",
            available_pantry=["Chicken", "Jasmine Rice", "Coconut Milk", "Tamari"],
            profile_id="alex-roommate"
        )
        self.assertIn("recipe", res)
        self.assertTrue(len(res["recipe"]) > 50)
        self.assertIn("model", res)

    def test_dining_card_generation(self):
        card = self.engine.generate_dining_card(
            friend_name="Alex",
            allergies=["gluten", "tree_nuts"],
            severity="Severe Anaphylaxis"
        )
        self.assertIn("card_text", card)
        self.assertIn("CHEF", card["card_text"].upper())


class TestPantryStore(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_rules = Path(self.temp_dir.name) / "test_rules.json"
        
        # Seed test data
        sample_data = {
            "profiles": [
                {
                    "id": "alex-roommate",
                    "name": "Alex",
                    "relation": "Roommate",
                    "allergies": ["gluten", "tree_nuts"],
                    "severity": "High"
                }
            ],
            "pantry_items": [
                { "id": "p1", "name": "Jasmine Rice", "category": "grains" }
            ]
        }
        with open(self.test_rules, "w", encoding="utf-8") as f:
            json.dump(sample_data, f)
            
        self.store = PantryStore(data_path=self.test_rules)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_profiles(self):
        profs = self.store.get_profiles()
        self.assertGreaterEqual(len(profs), 1)
        self.assertEqual(profs[0]["name"], "Alex")

    def test_create_profile(self):
        new_prof = self.store.create_profile({
            "name": "Sam",
            "relation": "Friend",
            "allergies": ["dairy"],
            "severity": "Moderate"
        })
        self.assertIn("id", new_prof)
        fetched = self.store.get_profile(new_prof["id"])
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched["name"], "Sam")

    def test_add_and_delete_pantry_item(self):
        item = self.store.add_pantry_item({
            "name": "Sunflower Butter",
            "category": "spreads"
        })
        self.assertIn("id", item)
        self.assertTrue(any(i["id"] == item["id"] for i in self.store.get_pantry_items()))

        # Delete
        success = self.store.delete_pantry_item(item["id"])
        self.assertTrue(success)
        self.assertFalse(any(i["id"] == item["id"] for i in self.store.get_pantry_items()))


if __name__ == "__main__":
    unittest.main()
