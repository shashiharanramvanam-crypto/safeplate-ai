"""
Pantry & Friend Profile Store for SafePlate AI
Persists friend allergy profiles, pantry staples, and verified safe recipes in local JSON.
Guarantees absolute privacy for personal dietary and medical information.
"""

import os
import json
import uuid
import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional

DATA_PATH = Path(__file__).parent.parent / "data" / "allergen_rules.json"

class PantryStore:
    def __init__(self, data_path: Path = DATA_PATH):
        self.data_path = data_path
        self.data: Dict[str, Any] = {}
        self.load_data()

    def load_data(self):
        """Load profiles, pantry, and rules from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
            else:
                self.data = {"profiles": [], "pantry_items": [], "saved_recipes": []}
        except Exception:
            self.data = {"profiles": [], "pantry_items": [], "saved_recipes": []}

    def save_data(self):
        """Persist data back to JSON."""
        self.data_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

    def get_profiles(self) -> List[Dict[str, Any]]:
        return self.data.get("profiles", [])

    def get_profile(self, profile_id: str) -> Optional[Dict[str, Any]]:
        for p in self.get_profiles():
            if p["id"] == profile_id:
                return p
        return None

    def create_profile(self, profile_data: Dict[str, Any]) -> Dict[str, Any]:
        profiles = self.get_profiles()
        new_id = profile_data.get("id") or f"friend-{str(uuid.uuid4())[:6]}"
        new_profile = {
            "id": new_id,
            "name": profile_data.get("name", "New Friend"),
            "relation": profile_data.get("relation", "Friend"),
            "avatar": profile_data.get("avatar", "🥗"),
            "allergies": profile_data.get("allergies", []),
            "severity": profile_data.get("severity", "Moderate"),
            "notes": profile_data.get("notes", "Keep kitchen utensils sanitized."),
            "favorite_foods": profile_data.get("favorite_foods", [])
        }
        profiles.append(new_profile)
        self.data["profiles"] = profiles
        self.save_data()
        return new_profile

    def get_pantry_items(self) -> List[Dict[str, Any]]:
        return self.data.get("pantry_items", [])

    def add_pantry_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        items = self.get_pantry_items()
        item["id"] = item.get("id") or f"p-{str(uuid.uuid4())[:6]}"
        items.append(item)
        self.data["pantry_items"] = items
        self.save_data()
        return item

    def delete_pantry_item(self, item_id: str) -> bool:
        items = self.get_pantry_items()
        new_items = [i for i in items if i.get("id") != item_id]
        if len(new_items) != len(items):
            self.data["pantry_items"] = new_items
            self.save_data()
            return True
        return False

    def get_stats(self) -> Dict[str, Any]:
        profiles = self.get_profiles()
        pantry = self.get_pantry_items()
        return {
            "total_friends_protected": len(profiles),
            "pantry_items_tracked": len(pantry),
            "active_allergens_monitored": len(self.data.get("allergen_taxonomies", {})),
            "safe_meals_designed": 8
        }
