from flight_agent.ai_advisor import _get_gemini_client
from flight_agent.config import GEMINI_MODELS
from google.genai import types
import json

client = _get_gemini_client()
user_prompt = "אני מחפש טיסות הכי זולות לאתונה לסוף נובמבר הלוך ושוב ישיר בלבד"
sample_flights = [
    {"engine": "טיסות סודיות (Playwright)", "airline": "SKY express", "price": 380, "currency": "ILS", "direct": True, "outbound_time": "23:30 -> 01:45", "return_time": "03:30 -> 05:30"},
    {"engine": "Kiwi.com", "airline": "Wizz Air Malta", "price": 453, "currency": "ILS", "direct": True, "outbound_time": "10:00 -> 12:15", "return_time": "14:00 -> 16:15"},
    {"engine": "Google Flights", "airline": "ישראייר", "price": 538, "currency": "ILS", "direct": True, "outbound_time": "16:45 -> 19:00", "return_time": "20:00 -> 22:15"}
]

p = f"""
אתה סוכן נסיעות AI אוטונומי.
המשתמש כתב לך את הפרומפט הבא:
"{user_prompt}"

ביצעת סריקת עומק באינטרנט ובאתרי חברות התעופה בישראל עבור תל אביב -> אתונה (הלוך ושוב ישיר), 2026-11-20 עד 2026-11-25.
הנה הטיסות הזולות ביותר שאיתרת:
{json.dumps(sample_flights, ensure_ascii=False)}

נסח מענה מקצועי, אישי ומדויק שעונה ישירות לפרומפט שלו.
החזר JSON בלבד:
{{
  "best_deal": "...",
  "price_verdict": "...",
  "tips": ["...", "...", "..."],
  "summary_markdown": "..."
}}
"""

res = client.models.generate_content(
    model="gemini-3.1-flash-lite",
    contents=p,
    config=types.GenerateContentConfig(response_mime_type="application/json", temperature=0.2)
)

print("Gemini advice response:")
parsed = json.loads(res.text)
print("Best deal:", parsed.get("best_deal"))
print("Summary markdown:\n", parsed.get("summary_markdown"))
