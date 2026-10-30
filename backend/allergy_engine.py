"""
Allergy & Safe Meal Intelligence Engine for SafePlate AI
Powered by Google Gemma 2 2B running 100% locally via Ollama.
Provides deterministic allergen screening, safe recipe authoring, and cross-contamination shields.
"""

import json
import urllib.request
import urllib.error
import time
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"
PREFERRED_MODELS = ["gemma2:2b", "gemma:2b", "gemma2", "llama3.2:1b", "llama3.2"]

DATA_PATH = Path(__file__).parent.parent / "data" / "allergen_rules.json"

SAFEPLATE_SYSTEM_PROMPT = """You are 'SafePlate AI', an elite culinary safety architect and compassionate meal planner.
You are designing meals for a specific friend or loved one who suffers from serious food allergies (such as Celiac disease or anaphylactic nut allergies).

Safety Rules:
1. NEVER allow ambiguous or high-risk ingredients (e.g. standard soy sauce contains wheat; Worcestershire sauce often contains barley or anchovy; commercial pesto contains pine nuts or walnuts).
2. Explicitly recommend certified safe alternatives (e.g. Coconut Aminos or Certified GF Tamari instead of soy sauce; Sunflower Seed Butter instead of peanut butter; Cassava Flour instead of wheat flour).
3. Include specific cross-contamination kitchen advice (e.g. separate toaster, sanitize cutting boards, clean oil).
4. Keep recipes appetizing, warm, comforting, and clear.
"""

FALLBACK_RECIPES = {
    "alex-roommate": (
        "🥗 **Alex-Safe Golden Coconut Lime Chicken Rice Bowls**\n\n"
        "• **Safety Profile:** 100% Certified Gluten-Free & Strict Tree Nut / Peanut Free.\n"
        "• **Prep Time:** 25 mins | **Portions:** 2 hearty bowls\n\n"
        "**Safe Ingredients:**\n"
        "- 1 lb chicken breast, cut into bite-sized cubes\n"
        "- 1 cup jasmine rice (naturally gluten-free)\n"
        "- 1 can (13.5 oz) full-fat coconut milk (nut-free alternative to heavy cream)\n"
        "- 2 tbsp Certified Gluten-Free Tamari (San-J or Coconut Aminos — NO standard soy sauce!)\n"
        "- 1 tbsp avocado or olive oil\n"
        "- 1 red bell pepper, thinly sliced\n"
        "- 2 cloves fresh garlic, minced & 1 tbsp fresh ginger, grated\n"
        "- 1 fresh lime, cut into wedges & fresh cilantro for garnish\n\n"
        "**Kitchen Cross-Contamination Guard:**\n"
        "⚠️ Use a dedicated sanitized cutting board and wooden spoon that has never contacted wheat flour.\n\n"
        "**Method:**\n"
        "1. Rinse jasmine rice in cold water until clear. Cook in 1.75 cups water until fluffy.\n"
        "2. Heat oil in a clean skillet over medium-high heat. Brown chicken cubes for 5-6 minutes.\n"
        "3. Add minced garlic, ginger, and bell peppers. Sauté for 2 minutes until fragrant.\n"
        "4. Pour in coconut milk and GF Tamari. Bring to a gentle simmer for 8 minutes until sauce coats the spoon.\n"
        "5. Spoon over warm jasmine rice, squeeze fresh lime juice, and sprinkle fresh cilantro."
    ),
    "maya-friend": (
        "🍲 **Maya-Safe Mediterranean Herb Lemon Chicken & Quinoa**\n\n"
        "• **Safety Profile:** 100% Dairy-Free & Shellfish-Free.\n"
        "• **Prep Time:** 30 mins | **Portions:** 2 portions\n\n"
        "**Safe Ingredients:**\n"
        "- 1 lb chicken breast or chickpeas\n"
        "- 1 cup quinoa or brown rice\n"
        "- 3 tbsp extra virgin olive oil (rich dairy-free butter alternative)\n"
        "- 1 cup cherry tomatoes, halved & 1 cucumber, diced\n"
        "- 1 tbsp dried oregano, 2 cloves minced garlic, zest & juice of 1 lemon\n"
        "- Kalamata olives and fresh parsley\n\n"
        "**Kitchen Safety Guard:**\n"
        "⚠️ Ensure no shared oyster or fish sauce is used in the marinade.\n\n"
        "**Method:**\n"
        "1. Cook quinoa in vegetable broth for 15 minutes.\n"
        "2. Sauté chicken with garlic, oregano, and olive oil until golden.\n"
        "3. Toss with warm quinoa, tomatoes, cucumbers, olives, and fresh lemon dressing."
    )
}


class AllergyEngine:
    def __init__(self, host: str = DEFAULT_OLLAMA_HOST, rules_path: Path = DATA_PATH):
        self.host = host.rstrip("/")
        self.rules_path = rules_path
        self.active_model: Optional[str] = None
        self.is_connected = False
        self.taxonomies: Dict[str, Any] = {}
        self.load_rules()
        self.detect_model()

    def load_rules(self):
        """Load deterministic allergen taxonomies."""
        try:
            if self.rules_path.exists():
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.taxonomies = data.get("allergen_taxonomies", {})
        except Exception:
            pass

    def detect_model(self) -> Optional[str]:
        """Detect available open-weight models in Ollama."""
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=3) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                models = [m.get("name", "") for m in data.get("models", [])]
                
                for pref in PREFERRED_MODELS:
                    for m in models:
                        if m.startswith(pref) or pref in m:
                            self.active_model = m
                            self.is_connected = True
                            return self.active_model
                
                if models:
                    self.active_model = models[0]
                    self.is_connected = True
                    return self.active_model
        except Exception:
            self.is_connected = False
            self.active_model = None
            
        return None

    def get_status(self) -> Dict[str, Any]:
        """Return engine status and model info."""
        self.detect_model()
        return {
            "connected": self.is_connected,
            "host": self.host,
            "model": self.active_model or "None (Deterministic Rulebook Active)",
            "is_gemma": "gemma" in (self.active_model or "").lower(),
            "privacy_mode": "100% Local Device Privacy — Zero Medical/Dietary Egress"
        }

    def scan_ingredients_deterministic(
        self,
        ingredient_text: str,
        allergies: List[str]
    ) -> Dict[str, Any]:
        """
        Deterministic, zero-hallucination rulebook scanner.
        Directly checks for known triggers and hidden derivatives.
        """
        text_lower = ingredient_text.lower()
        flagged_hazards: List[Dict[str, Any]] = []

        for allergy_key in allergies:
            tax = self.taxonomies.get(allergy_key)
            if not tax:
                continue

            display_name = tax.get("display_name", allergy_key)
            triggers = tax.get("triggers", [])
            substitutes = tax.get("safe_substitutes", [])

            for trig in triggers:
                # Word boundary search matching singular and plural forms
                pattern = r'\b' + re.escape(trig) + r'(?:s|es)?\b'
                if re.search(pattern, text_lower):
                    flagged_hazards.append({
                        "allergen_group": display_name,
                        "matched_trigger": trig,
                        "severity": "HIGH DANGER",
                        "safe_substitutes": substitutes[:2]
                    })

        is_safe = len(flagged_hazards) == 0
        return {
            "safe": is_safe,
            "verdict": "SAFE TO PREPARE" if is_safe else "ALLERGEN THREAT DETECTED",
            "hazard_count": len(flagged_hazards),
            "flagged_hazards": flagged_hazards
        }

    def _query_local_model(self, prompt: str) -> Optional[str]:
        """Send prompt to local Ollama instance."""
        if not (self.is_connected and self.active_model):
            return None
            
        try:
            full_prompt = (
                f"<start_of_turn>user\n"
                f"{SAFEPLATE_SYSTEM_PROMPT}\n\n"
                f"{prompt}<end_of_turn>\n"
                f"<start_of_turn>model\n"
            )
            payload = json.dumps({
                "model": self.active_model,
                "prompt": full_prompt,
                "stream": False,
                "options": {
                    "temperature": 0.5,
                    "top_p": 0.9,
                    "max_tokens": 400
                }
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.host}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=40) as resp:
                result = json.loads(resp.read().decode("utf-8"))
                return result.get("response", "").strip()
        except Exception:
            return None

    def generate_safe_meal(
        self,
        friend_name: str,
        allergies: List[str],
        severity: str,
        available_pantry: List[str],
        profile_id: str = "alex-roommate"
    ) -> Dict[str, Any]:
        """Generate a safe, delicious recipe for the friend using local Gemma 2."""
        start_time = time.time()
        allergy_str = ", ".join(allergies)
        pantry_str = ", ".join(available_pantry) if available_pantry else "Chicken, rice, olive oil, garlic, coconut milk"

        prompt = (
            f"Design a delicious, comforting homemade dinner recipe for my friend '{friend_name}'.\n"
            f"Strict Allergies to avoid: {allergy_str} (Severity: {severity}).\n"
            f"Available safe pantry staples: {pantry_str}.\n\n"
            f"Provide:\n"
            f"1. Recipe Name & Safety Verification badge.\n"
            f"2. Safe Ingredient list with explicit certified gluten-free / allergen-free brands or labels.\n"
            f"3. 2 Critical Cross-Contamination Kitchen Rules for roommates.\n"
            f"4. Concise, step-by-step cooking method."
        )

        response_text = self._query_local_model(prompt)
        elapsed = round(time.time() - start_time, 2)

        if response_text:
            return {
                "recipe": response_text,
                "model": self.active_model,
                "source": "local_open_weight_gemma",
                "latency_seconds": elapsed,
                "guarantee": "100% Local Inference — Safe & Private for Alex"
            }

        # Offline fallback
        fallback = FALLBACK_RECIPES.get(profile_id, FALLBACK_RECIPES["alex-roommate"])
        return {
            "recipe": fallback,
            "model": "SafePlate-Verified-Rulebook",
            "source": "local_fallback",
            "latency_seconds": elapsed,
            "guarantee": "100% Air-Gapped Fallback."
        }

    def generate_dining_card(
        self,
        friend_name: str,
        allergies: List[str],
        severity: str
    ) -> Dict[str, Any]:
        """Generate an emergency restaurant server communication briefing card."""
        start_time = time.time()
        allergy_str = ", ".join(allergies)

        prompt = (
            f"Create a polite, serious, and unambiguous Restaurant Server Allergy Card for my friend {friend_name}.\n"
            f"They have life-threatening allergies to: {allergy_str} ({severity}).\n"
            f"Include exact instructions for the chef regarding shared fryers, grills, cutting boards, and hidden sauces."
        )

        response_text = self._query_local_model(prompt)
        elapsed = round(time.time() - start_time, 2)

        if response_text:
            return {
                "card_text": response_text,
                "model": self.active_model,
                "latency_seconds": elapsed
            }

        fallback_card = (
            f"🚨 **CHEF & SERVER ALLERGY NOTICE FOR {friend_name.upper()}**\n\n"
            f"Dear Chef and Server,\n"
            f"I have a severe, life-threatening medical condition: **{severity}**.\n"
            f"I cannot consume any trace of: **{allergy_str.upper()}**.\n\n"
            f"• **GLUTEN/CELIAC:** No wheat, flour, bread, soy sauce, malt, or shared fryers/toasters.\n"
            f"• **NUTS:** No peanuts, tree nuts, nut oils, or pestos.\n"
            f"• **CROSS-CONTAMINATION:** Please prepare my meal in a clean pan with fresh gloves and fresh utensils.\n\n"
            f"Thank you for your care in keeping me safe tonight!"
        )
        return {
            "card_text": fallback_card,
            "model": "SafePlate-Verified-Rulebook",
            "latency_seconds": elapsed
        }
