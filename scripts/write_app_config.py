"""Create the public mobile config from `.env` before running `flet build apk`.

Only non-secret client values are written. AI provider keys are never copied.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "assets" / "app_config.json"
PUBLIC_KEYS = ("AI_BACKEND_URL", "FIREBASE_API_KEY", "FIREBASE_PROJECT_ID")


def main() -> int:
    values = dotenv_values(ROOT / ".env")
    config = {key: (values.get(key) or "").strip() for key in PUBLIC_KEYS}
    missing = [key for key, value in config.items() if not value]
    if missing:
        print(f"Missing in .env: {', '.join(missing)}")
        return 1
    if urlsplit(config["AI_BACKEND_URL"]).scheme != "https":
        print("AI_BACKEND_URL must use https for a mobile build.")
        return 1
    OUTPUT.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
