import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SURVEY_DB_PATH = BASE_DIR / "data" / "surveys.db"
SURVEY_SCREENSHOTS_DIR = BASE_DIR / "data" / "survey_screenshots"
SURVEY_SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

# Gmail IMAP settings
IMAP_SERVER = os.getenv("IMAP_SERVER", "imap.gmail.com")
IMAP_PORT = int(os.getenv("IMAP_PORT", "993"))
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD", "")

# Survey target sender
TARGET_SENDER = os.getenv("SURVEY_SENDER", "panelview@polyeda.com")

# Playwright settings
PLAYWRIGHT_HEADLESS = os.getenv("PLAYWRIGHT_HEADLESS", "true").lower() == "true"
PLAYWRIGHT_TIMEOUT = int(os.getenv("PLAYWRIGHT_TIMEOUT", "30000")) # 30 seconds

# Google Gemini AI Key
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
