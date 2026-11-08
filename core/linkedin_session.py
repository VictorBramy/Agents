import os
import json
import time
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from playwright.sync_api import sync_playwright

from core.config import BASE_DIR
from core.db import get_setting, set_setting

STORAGE_STATE_PATH = BASE_DIR / "data" / "linkedin_storage_state.json"
PROFILE_DIR = BASE_DIR / "data" / "linkedin_chrome_profile"
PROFILE_DIR.mkdir(parents=True, exist_ok=True)


def get_linkedin_status() -> Dict[str, Any]:
    """
    Checks whether a valid LinkedIn session exists in storage_state or via li_at cookie.
    """
    li_at = get_setting("LINKEDIN_LI_AT", "")
    has_storage = STORAGE_STATE_PATH.exists() and STORAGE_STATE_PATH.stat().st_size > 20
    is_connected = bool(li_at or has_storage)

    return {
        "is_connected": is_connected,
        "has_li_at": bool(li_at),
        "has_storage_state": has_storage,
        "storage_file": str(STORAGE_STATE_PATH)
    }


def save_li_at_cookie(cookie_value: str):
    """Saves the user's li_at session cookie in app settings and writes storage_state.json."""
    val = cookie_value.strip()
    if not val:
        return
    set_setting("LINKEDIN_LI_AT", val)

    state = {
        "cookies": [
            {
                "name": "li_at",
                "value": val,
                "domain": ".www.linkedin.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None"
            },
            {
                "name": "li_at",
                "value": val,
                "domain": ".linkedin.com",
                "path": "/",
                "expires": -1,
                "httpOnly": True,
                "secure": True,
                "sameSite": "None"
            }
        ],
        "origins": []
    }
    with open(STORAGE_STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2)


def get_linkedin_browser_context(p, headless: bool = True):
    """
    Spawns Google Chrome persistent context with isolated profile directory.
    Returns (context, context).
    """
    args = [
        "--disable-blink-features=AutomationControlled",
        "--no-first-run",
        "--no-default-browser-check"
    ]

    try:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=headless,
            viewport={"width": 1280, "height": 900},
            locale="he-IL",
            args=args
        )
    except Exception as e:
        print(f"[Persistent Context Failed, falling back to standard launch]: {e}")
        browser = p.chromium.launch(channel="chrome", headless=headless, args=args)
        if STORAGE_STATE_PATH.exists() and STORAGE_STATE_PATH.stat().st_size > 20:
            context = browser.new_context(storage_state=str(STORAGE_STATE_PATH), viewport={"width": 1280, "height": 900}, locale="he-IL")
        else:
            context = browser.new_context(viewport={"width": 1280, "height": 900}, locale="he-IL")

    li_at = get_setting("LINKEDIN_LI_AT", "")
    if li_at:
        try:
            context.add_cookies([
                {"name": "li_at", "value": li_at.strip(), "domain": ".www.linkedin.com", "path": "/"},
                {"name": "li_at", "value": li_at.strip(), "domain": ".linkedin.com", "path": "/"}
            ])
        except Exception:
            pass

    return context, context


def launch_login_browser():
    """
    Launches a dedicated Google Chrome window for LinkedIn login.
    Uses launch_persistent_context to avoid singleton collisions with running Chrome.
    """
    try:
        with sync_playwright() as p:
            args = [
                "--disable-blink-features=AutomationControlled",
                "--no-first-run",
                "--no-default-browser-check",
                "--start-maximized"
            ]
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(PROFILE_DIR),
                channel="chrome",
                headless=False,
                args=args
            )
            page = context.pages[0] if context.pages else context.new_page()

            li_at = get_setting("LINKEDIN_LI_AT", "")
            if li_at:
                try:
                    context.add_cookies([
                        {"name": "li_at", "value": li_at.strip(), "domain": ".www.linkedin.com", "path": "/"},
                        {"name": "li_at", "value": li_at.strip(), "domain": ".linkedin.com", "path": "/"}
                    ])
                except Exception:
                    pass

            page.goto("https://www.linkedin.com/login", wait_until="domcontentloaded")
            print("[LinkedIn Login] Dedicated login window opened. Waiting for user login...")

            start_time = time.time()
            logged_in = False
            while time.time() - start_time < 300:  # 5 minutes timeout
                try:
                    curr_url = page.url
                    cookies = context.cookies("https://www.linkedin.com")
                    has_li_cookie = any(c.get("name") == "li_at" for c in cookies)

                    if has_li_cookie or any(k in curr_url for k in ["feed", "mynetwork", "jobs"]):
                        print("[LinkedIn Login] Detected active login! Saving storage state...")
                        context.storage_state(path=str(STORAGE_STATE_PATH))
                        for c in cookies:
                            if c.get("name") == "li_at":
                                set_setting("LINKEDIN_LI_AT", c.get("value"))
                                break
                        logged_in = True
                        break
                    time.sleep(2)
                except Exception:
                    break

            try:
                context.close()
            except Exception:
                pass
            return logged_in
    except Exception as e:
        print(f"[LinkedIn Login Browser Launch Error]: {e}")
        return False
