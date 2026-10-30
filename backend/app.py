"""
Main HTTP Server & REST API for SafePlate AI
Kitchen meal planner and zero-hallucination allergy shield for friends.
Runs completely offline with standard Python 3 library on port 8082.
"""

import os
import sys
import json
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Dict, Any

from allergy_engine import AllergyEngine
from pantry_store import PantryStore

BASE_DIR = Path(__file__).parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"

engine = AllergyEngine()
store = PantryStore()

class SafePlateHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_cors_headers()
        self.end_headers()

    def send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")

    def send_json(self, data: Any, status: int = 200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_cors_headers()
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def send_error_json(self, message: str, status: int = 400):
        self.send_json({"error": message}, status=status)

    def read_body(self) -> Dict[str, Any]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception:
            return {}

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path == "/api/status":
            return self.send_json(engine.get_status())

        elif path == "/api/profiles":
            return self.send_json(store.get_profiles())

        elif path.startswith("/api/profiles/") and not path.endswith("/export"):
            pid = path.replace("/api/profiles/", "").strip()
            profile = store.get_profile(pid)
            if profile:
                return self.send_json(profile)
            return self.send_error_json("Profile not found", 404)

        elif path == "/api/pantry":
            return self.send_json(store.get_pantry_items())

        elif path == "/api/stats":
            return self.send_json(store.get_stats())

        elif path.startswith("/api/export/"):
            pid = path.replace("/api/export/", "").strip()
            profile = store.get_profile(pid)
            if not profile:
                return self.send_error_json("Profile not found", 404)
            
            archive_html = self.generate_archival_html(profile)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="safeplate_{pid}_kitchen_card.html"')
            self.send_cors_headers()
            self.end_headers()
            self.wfile.write(archive_html.encode("utf-8"))
            return

        if path == "" or path == "/":
            self.path = "/index.html"
        return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")
        body = self.read_body()

        if path == "/api/profiles":
            created = store.create_profile(body)
            return self.send_json(created, status=201)

        elif path == "/api/pantry":
            created = store.add_pantry_item(body)
            return self.send_json(created, status=201)

        elif path == "/api/scan":
            text = body.get("ingredients", "")
            allergies = body.get("allergies", ["gluten", "tree_nuts"])
            result = engine.scan_ingredients_deterministic(text, allergies)
            return self.send_json(result)

        elif path == "/api/recipe/generate":
            profile_id = body.get("profile_id", "alex-roommate")
            profile = store.get_profile(profile_id)
            if not profile:
                return self.send_error_json("Profile not found", 404)

            pantry = [item["name"] for item in store.get_pantry_items()]
            recipe_result = engine.generate_safe_meal(
                friend_name=profile["name"],
                allergies=profile.get("allergies", []),
                severity=profile.get("severity", "High"),
                available_pantry=pantry,
                profile_id=profile_id
            )
            return self.send_json(recipe_result)

        elif path == "/api/dining-card":
            profile_id = body.get("profile_id", "alex-roommate")
            profile = store.get_profile(profile_id)
            if not profile:
                return self.send_error_json("Profile not found", 404)

            card_result = engine.generate_dining_card(
                friend_name=profile["name"],
                allergies=profile.get("allergies", []),
                severity=profile.get("severity", "High")
            )
            return self.send_json(card_result)

        return self.send_error_json("Endpoint not found", 404)

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path.rstrip("/")

        if path.startswith("/api/pantry/"):
            item_id = path.replace("/api/pantry/", "").strip()
            if store.delete_pantry_item(item_id):
                return self.send_json({"success": True})
            return self.send_error_json("Pantry item not found", 404)

        return self.send_error_json("Endpoint not found", 404)

    def generate_archival_html(self, profile: Dict[str, Any]) -> str:
        """Create a standalone printable kitchen safety card for the fridge."""
        name = profile.get("name", "Friend")
        relation = profile.get("relation", "Friend")
        allergies = ", ".join(profile.get("allergies", [])).upper()
        severity = profile.get("severity", "High")
        notes = profile.get("notes", "")

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Safe Kitchen Guide &mdash; For {name}</title>
<style>
  body {{
    background: #fdfaf6;
    color: #2b2d42;
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    margin: 0;
    padding: 40px 20px;
    display: flex;
    justify-content: center;
  }}
  .card {{
    max-width: 680px;
    width: 100%;
    background: #fff;
    border: 3px solid #2b5c4f;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
    border-radius: 14px;
    padding: 35px;
  }}
  .badge-danger {{
    background: #d90429;
    color: #fff;
    display: inline-block;
    padding: 6px 14px;
    border-radius: 20px;
    font-size: 0.85rem;
    font-weight: bold;
    letter-spacing: 1px;
    margin-bottom: 12px;
  }}
  h1 {{ color: #2b5c4f; margin: 0 0 4px 0; font-size: 2rem; }}
  .sub {{ color: #6c757d; font-size: 1rem; margin-bottom: 24px; }}
  .rule-box {{
    background: #f8f9fa;
    border-left: 5px solid #e69500;
    padding: 18px 20px;
    border-radius: 4px;
    margin-bottom: 24px;
    line-height: 1.6;
  }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 14px; margin-bottom: 24px; }}
  .item-box {{
    background: #f0f7f4;
    border: 1px solid #b7e4c7;
    padding: 12px 16px;
    border-radius: 8px;
  }}
  .footer {{
    text-align: center;
    font-size: 0.8rem;
    color: #8d99ae;
    margin-top: 30px;
    border-top: 1px solid #eee;
    padding-top: 15px;
  }}
</style>
</head>
<body>
<div class="card">
  <div class="badge-danger">⚠️ STRICT ALLERGEN PROTOCOL ACTIVE</div>
  <h1>SafePlate Kitchen Guide &bull; {name}</h1>
  <div class="sub">{relation} &bull; Severity: <strong>{severity}</strong></div>

  <div class="rule-box">
    <strong>STRICT ALLERGENS MONITORED:</strong> {allergies}<br>
    <strong>ROOMMATE KITCHEN RULE:</strong> {notes}
  </div>

  <h3>Roommate Shared Kitchen Golden Rules:</h3>
  <div class="grid">
    <div class="item-box">
      <strong>🍞 Toasters & Crumbs</strong><br>
      Never toast gluten-free bread in a shared toaster. Use dedicated toaster bags or oven broiler.
    </div>
    <div class="item-box">
      <strong>🔪 Cutting Boards</strong><br>
      Use the green plastic board exclusively for {name}'s prep. Wooden boards harbor microscopic gluten and nut oils.
    </div>
    <div class="item-box">
      <strong>🥄 Condiment Jars</strong><br>
      Never double-dip butter knives into peanut butter or mayonnaise jars after touching wheat bread.
    </div>
    <div class="item-box">
      <strong>🍳 Frying Pans & Spatulas</strong><br>
      Scrub with fresh sponge and hot soapy water before searing food for {name}.
    </div>
  </div>

  <div class="footer">
    SafePlate AI &bull; Built with love for a friend &bull; Hacktoberfest 2026: Build for a Friend
  </div>
</div>
</body>
</html>"""


def run_server(port: int = 8082):
    server_address = ("127.0.0.1", port)
    httpd = ThreadingHTTPServer(server_address, SafePlateHandler)
    print(f"\n=======================================================")
    print(f"🥗  SAFEPLATE AI — BUILD FOR A FRIEND (LOCAL SERVER) 🥗")
    print(f"=======================================================")
    print(f"✦ Active URL:       http://localhost:{port}")
    print(f"✦ Gemma Engine:     {engine.active_model or 'Deterministic Rulebook'}")
    print(f"✦ Roommate Shield:  100% Offline & Private (Alex & Maya)")
    print(f"=======================================================\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping SafePlate server. Bon appetit!")
        httpd.server_close()


if __name__ == "__main__":
    port = 8082
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
