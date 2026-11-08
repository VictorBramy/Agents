import re
import imaplib
import email
from email.header import decode_header
from typing import List, Dict, Any, Optional
from bs4 import BeautifulSoup
from datetime import datetime

from survey_agent.config import (
    IMAP_SERVER, IMAP_PORT, GMAIL_USER, GMAIL_APP_PASSWORD, TARGET_SENDER
)
from survey_agent.db import get_setting, insert_or_get_survey

def _decode_mime_header(header_value: Optional[str]) -> str:
    """Decodes MIME encoded header strings to readable UTF-8."""
    if not header_value:
        return ""
    decoded_fragments = decode_header(header_value)
    result = []
    for fragment, encoding in decoded_fragments:
        if isinstance(fragment, bytes):
            try:
                result.append(fragment.decode(encoding or "utf-8", errors="replace"))
            except Exception:
                result.append(fragment.decode("utf-8", errors="replace"))
        else:
            result.append(str(fragment))
    return "".join(result).strip()

def _extract_survey_links(html_content: str, text_content: str) -> List[str]:
    """
    Extracts survey links from Polyeda / Panel View email bodies.
    Looks for links containing panelview, polyeda, midgam, or generic survey paths.
    """
    found_links = []
    
    # 1. Search in HTML anchors
    if html_content:
        soup = BeautifulSoup(html_content, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            anchor_text = a.get_text().strip()
            
            # Check domain or link text
            is_polyeda_domain = any(dom in href.lower() for dom in ["panelview", "polyeda", "midgam", "survey"])
            is_survey_text = any(phrase in anchor_text for phrase in ["סקר", "כניסה", "לחצו כאן", "התחל", "להשתתפות"])
            
            if is_polyeda_domain or is_survey_text:
                if href.startswith("http") and href not in found_links:
                    found_links.append(href)

    # 2. Search via regex in text and HTML
    combined = (html_content or "") + " " + (text_content or "")
    url_patterns = [
        r'https?://(?:www\.)?(?:panelview|polyeda|midgam)\.co(?:m|\.il)[^\s"\'<>]+',
        r'https?://[^\s"\'<>]*(?:survey|surveys)[^\s"\'<>]*',
    ]
    for pat in url_patterns:
        for match in re.findall(pat, combined, re.IGNORECASE):
            url = match.rstrip(".,;!\"')")
            if url not in found_links and "unsubscribe" not in url.lower():
                found_links.append(url)

    # Filter out obvious non-survey links (privacy policy, unsubs, social media)
    valid_links = []
    for u in found_links:
        u_lower = u.lower()
        if any(bad in u_lower for bad in ["unsubscribe", "privacy", "facebook", "instagram", "twitter", "linkedin", "polyeda.com/privacy"]):
            continue
        valid_links.append(u)

    return valid_links

def _extract_points(text: str) -> int:
    """Extracts reward points amount from email text if present."""
    match = re.search(r'(\d+)\s*(?:נקודות|נק\'|נק|ש"ח|שקלים)', text)
    if match:
        try:
            return int(match.group(1))
        except Exception:
            pass
    return 0

def check_polyeda_emails() -> Dict[str, Any]:
    """
    Connects to Gmail via IMAP, searches for survey emails from panelview@polyeda.com,
    extracts survey invitations and saves them to SQLite database.
    """
    user = get_setting("GMAIL_USER") or GMAIL_USER
    password = get_setting("GMAIL_APP_PASSWORD") or GMAIL_APP_PASSWORD
    target_sender = get_setting("TARGET_SENDER") or TARGET_SENDER

    if not user or not password:
        return {
            "status": "error",
            "message": "כתובת Gmail או סיסמת אפליקציה (App Password) טרם הוגדרו במערכת.",
            "new_surveys": []
        }

    # Clean app password spaces (e.g. "abcd efgh ijkl mnop" -> "abcdefghijklmnop")
    clean_password = password.replace(" ", "").strip()
    clean_user = user.strip()

    try:
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, IMAP_PORT)
        mail.login(clean_user, clean_password)
        mail.select("INBOX")
    except Exception as e:
        return {
            "status": "error",
            "message": f"שגיאת התחברות ל-Gmail (IMAP): {str(e)}. ודא שסיסמת האפליקציה תקינה וש-IMAP מופעל בהגדרות Gmail.",
            "new_surveys": []
        }

    detected_surveys = []

    try:
        # Search for emails from polyeda / panelview
        # Try both FROM filter and broader search
        status, data = mail.search(None, f'(FROM "{target_sender}")')
        msg_ids = data[0].split() if status == "OK" and data[0] else []

        if not msg_ids:
            # Fallback search for sender keyword "polyeda" or "panelview"
            status, data = mail.search(None, '(OR FROM "polyeda" FROM "panelview")')
            msg_ids = data[0].split() if status == "OK" and data[0] else []

        print(f"[EmailListener] Found {len(msg_ids)} potential survey emails from {target_sender}.")

        # Process the most recent emails (up to 30)
        for msg_id in reversed(msg_ids[-30:]):
            res, msg_data = mail.fetch(msg_id, "(RFC822)")
            if res != "OK":
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            from_header = _decode_mime_header(msg.get("From"))
            subject_header = _decode_mime_header(msg.get("Subject"))
            date_header = _decode_mime_header(msg.get("Date"))
            message_id_header = msg.get("Message-ID") or f"imap_{msg_id.decode('utf-8')}"

            # Verify sender matches target
            if not any(token in from_header.lower() for token in ["polyeda", "panelview"]):
                continue

            # Extract body
            html_body = ""
            text_body = ""

            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get("Content-Disposition", ""))
                    if "attachment" in content_disposition:
                        continue
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            charset = part.get_content_charset() or "utf-8"
                            text = payload.decode(charset, errors="replace")
                            if content_type == "text/html":
                                html_body += text
                            elif content_type == "text/plain":
                                text_body += text
                    except Exception:
                        pass
            else:
                try:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        charset = msg.get_content_charset() or "utf-8"
                        text_body = payload.decode(charset, errors="replace")
                except Exception:
                    pass

            # Extract links and points
            links = _extract_survey_links(html_body, text_body)
            points = _extract_points(subject_header + " " + text_body)

            if links:
                primary_survey_url = links[0]
                survey_payload = {
                    "msg_id": message_id_header,
                    "sender": from_header,
                    "subject": subject_header,
                    "received_at": date_header,
                    "survey_url": primary_survey_url,
                    "reward_points": points,
                    "status": "pending"
                }
                
                survey_id = insert_or_get_survey(survey_payload)
                survey_payload["id"] = survey_id
                detected_surveys.append(survey_payload)

        mail.close()
        mail.logout()

        return {
            "status": "success",
            "message": f"סריקת המייל הושלמה בהצלחה! זוהו {len(detected_surveys)} הזמנות לסקר מ-{target_sender}.",
            "new_surveys": detected_surveys
        }

    except Exception as e:
        try:
            mail.logout()
        except Exception:
            pass
        return {
            "status": "error",
            "message": f"שגיאה בעיבוד הודעות הדואר: {str(e)}",
            "new_surveys": []
        }
