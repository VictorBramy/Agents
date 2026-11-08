import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DB_PATH = DATA_DIR / "flights.db"

# Load environment
load_dotenv(BASE_DIR / ".env")

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not GEMINI_API_KEY:
    try:
        from core.db import get_setting
        GEMINI_API_KEY = get_setting("GEMINI_API_KEY", "")
    except Exception:
        pass

DEFAULT_ORIGIN = "TLV"
DEFAULT_CURRENCY = "ILS"

# Preferred Gemini models in fallback order
GEMINI_MODELS = [
    "gemini-3.8-flash",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.6-flash"
]
