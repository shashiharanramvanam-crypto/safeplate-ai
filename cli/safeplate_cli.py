"""
Offline Kitchen CLI & Allergy Shield for SafePlate AI
Instant command-line companion for checking pantry ingredients while cooking.
"""

import sys
import time
import os
from pathlib import Path

# Add backend to path
sys.path.append(str(Path(__file__).parent.parent / "backend"))

from allergy_engine import AllergyEngine
from pantry_store import PantryStore

# ANSI Color codes
GREEN = "\033[38;5;71m"
EMERALD = "\033[38;5;120m"
AMBER = "\033[38;5;214m"
CORAL = "\033[38;5;203m"
GRAY = "\033[38;5;244m"
RED = "\033[38;5;196m"
BOLD = "\033[1m"
RESET = "\033[0m"

BANNER = f"""
{GREEN}
       .---.
      /     \\
     | (🥗)  |       {EMERALD}SAFEPLATE AI : BUILD FOR A FRIEND{GREEN}
      \\ === /        {AMBER}Zero-Hallucination Safe Meal & Allergy Shield{GREEN}
       `---`         {GRAY}Powered by Google Gemma 2B Open Weights{RESET}
"""

def typewriter(text: str, delay: float = 0.012, color: str = GREEN):
    sys.stdout.write(color)
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    sys.stdout.write(RESET + "\n")

def main():
    os.system("") # Enable ANSI on Windows console
    print(BANNER)

    engine = AllergyEngine()
    store = PantryStore()

    status = engine.get_status()
    print(f"{GRAY}[Status: Model: {status['model']} | Connected: {status['connected']} | Mode: {status['privacy_mode']}]{RESET}\n")
    
    current_profile = store.get_profile("alex-roommate") or store.get_profiles()[0]
    print(f"{EMERALD}Active Friend Profile:{RESET} {BOLD}{current_profile['name']}{RESET} ({current_profile['relation']})")
    print(f"{CORAL}Allergies Monitored:{RESET} {', '.join(current_profile['allergies']).upper()} &bull; {current_profile['severity']}")
    print(f"{GRAY}Type 'help' for commands, or type 'scan <ingredient>' to check safety instantly.{RESET}\n")

    while True:
        try:
            cmd = input(f"{GREEN}🥗 [{current_profile['name']}]{RESET} > ").strip()
            if not cmd:
                continue

            cmd_lower = cmd.lower()

            if cmd_lower in ["exit", "quit", "q"]:
                typewriter(f"Kitchen shield standing down. Keep {current_profile['name']} safe!", 0.015, EMERALD)
                break

            elif cmd_lower == "help":
                print(f"""
{BOLD}Kitchen Commands:{RESET}
  {EMERALD}scan <ingredients>{RESET}    - Deterministic screening for hidden allergen triggers
  {EMERALD}cook{RESET}                  - Generate an AI safe dinner recipe with Gemma 2
  {EMERALD}card{RESET}                  - Generate an emergency restaurant server card
  {EMERALD}profiles{RESET}              - View or switch friend profiles (Alex, Maya)
  {EMERALD}pantry{RESET}                - List verified safe pantry staples
  {EMERALD}status{RESET}                - Check local Gemma engine status & air-gap verification
  {EMERALD}clear{RESET}                 - Clear terminal screen
""")

            elif cmd_lower.startswith("scan"):
                parts = cmd.split(" ", 1)
                if len(parts) < 2:
                    raw_text = input("Enter ingredients or recipe text to scan: ").strip()
                else:
                    raw_text = parts[1]

                res = engine.scan_ingredients_deterministic(raw_text, current_profile.get("allergies", []))
                if res["safe"]:
                    print(f"\n{EMERALD}{BOLD}✅ VERDICT: 100% SAFE FOR {current_profile['name'].upper()}{RESET}")
                    print(f"No flagged allergen triggers found in text.\n")
                else:
                    print(f"\n{RED}{BOLD}🚨 WARNING: {res['hazard_count']} ALLERGEN HAZARD(S) DETECTED!{RESET}")
                    for h in res["flagged_hazards"]:
                        print(f"  {CORAL}• Trigger: '{h['matched_trigger']}' ({h['allergen_group']}){RESET}")
                        if h.get("safe_substitutes"):
                            print(f"    {GREEN}↳ Safe Alternative: {', '.join(h['safe_substitutes'])}{RESET}")
                    print()

            elif cmd_lower.startswith("cook"):
                print(f"\n{AMBER}[Consulting local Gemma 2 allergy engine for {current_profile['name']}...]{RESET}")
                pantry = [item["name"] for item in store.get_pantry_items()]
                res = engine.generate_safe_meal(
                    friend_name=current_profile["name"],
                    allergies=current_profile["allergies"],
                    severity=current_profile["severity"],
                    available_pantry=pantry,
                    profile_id=current_profile["id"]
                )
                print(f"\n{res['recipe']}\n")
                print(f"{GRAY}[Latency: {res['latency_seconds']}s | Model: {res['model']} | {res['guarantee']}]{RESET}\n")

            elif cmd_lower.startswith("card"):
                print(f"\n{AMBER}[Authoring restaurant server briefing card...]{RESET}")
                res = engine.generate_dining_card(
                    friend_name=current_profile["name"],
                    allergies=current_profile["allergies"],
                    severity=current_profile["severity"]
                )
                print(f"\n{res['card_text']}\n")

            elif cmd_lower == "profiles":
                profs = store.get_profiles()
                print(f"\n{BOLD}Saved Friend Profiles:{RESET}")
                for p in profs:
                    active_marker = f"{EMERALD}* ACTIVE{RESET}" if p["id"] == current_profile["id"] else ""
                    print(f"  {BOLD}{p['id']:<16}{RESET} {p['name']:<20} ({p['relation']}) {active_marker}")
                    print(f"    {CORAL}Allergies: {', '.join(p['allergies'])} | Severity: {p['severity']}{RESET}")
                print(f"\nTo switch profile, type: 'switch <profile-id>'\n")

            elif cmd_lower.startswith("switch "):
                target_id = cmd.split(" ", 1)[1].strip()
                p = store.get_profile(target_id)
                if p:
                    current_profile = p
                    print(f"\n{EMERALD}Switched active profile to {BOLD}{p['name']}{RESET}!\n")
                else:
                    print(f"{RED}Profile '{target_id}' not found.{RESET}")

            elif cmd_lower == "pantry":
                items = store.get_pantry_items()
                print(f"\n{BOLD}Verified Safe Pantry Items ({len(items)} items):{RESET}")
                for it in items:
                    print(f"  {GREEN}✦ {it.get('name'):<30}{RESET} {GRAY}[{it.get('category')}]{RESET} - {it.get('notes')}")
                print()

            elif cmd_lower == "status":
                s = engine.get_status()
                print(f"\n{BOLD}Engine Telemetry:{RESET}")
                print(f"  Model:            {s['model']}")
                print(f"  Ollama Host:      {s['host']}")
                print(f"  Connected:        {s['connected']}")
                print(f"  Gemma 2 Active:   {s['is_gemma']}")
                print(f"  Privacy:          {EMERALD}{s['privacy_mode']}{RESET}\n")

            elif cmd_lower == "clear":
                os.system("cls" if os.name == "nt" else "clear")
                print(BANNER)

            else:
                # Direct scan
                res = engine.scan_ingredients_deterministic(cmd, current_profile.get("allergies", []))
                if res["safe"]:
                    print(f"\n{EMERALD}✅ Safe for {current_profile['name']}{RESET}\n")
                else:
                    print(f"\n{RED}🚨 DANGER: Contains allergen for {current_profile['name']}:{RESET}")
                    for h in res["flagged_hazards"]:
                        print(f"  • {h['matched_trigger']} ({h['allergen_group']})")
                    print()

        except (KeyboardInterrupt, EOFError):
            print(f"\n{GRAY}Closing SafePlate... Farewell.{RESET}")
            break

if __name__ == "__main__":
    main()
