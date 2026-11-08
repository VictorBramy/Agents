import json
import re
import sys
sys.stdout.reconfigure(encoding='utf-8')
from datetime import datetime, timedelta
from flight_agent.config import GEMINI_API_KEY, GEMINI_MODELS
from google import genai
from google.genai import types

def test_prompt(user_prompt):
    today_str = datetime.now().strftime("%Y-%m-%d")
    weekday_name = datetime.now().strftime("%A")

    enhanced_prompt = f"""
You are an expert Flight Query Parser AI specializing in Hebrew and English travel queries.
Current reference date: {today_str} ({weekday_name}). Year: {datetime.now().year}.

CRITICAL DATE REASONING RULES:
1. IN-STAY CONSTRAINTS ("שיהיה בתאריך X", "לשהות ב-X", "להיות ב-X", "כולל את תאריך X"):
   - If the user wants to BE at the destination on date X, but explicitly specifies "אבל לא בהלוך וגם לא בחזור" (not outbound and not return on date X):
     -> Departure MUST be strictly BEFORE date X (e.g. 1-2 days before X).
     -> Return MUST be strictly AFTER date X (e.g. 1-2 days after X).
     -> NEITHER departure_date NOR return_date can equal X! (departure_date != X and return_date != X).
2. DURATION LIMITS ("עד N ימים", "למשך N ימים"):
   - If duration is specified (e.g. "עד 5 ימים"), ensure (return_date - departure_date) <= N days.
3. MONTH CONSTRAINTS ("בנובמבר", "בדצמבר"):
   - Keep both departure_date and return_date strictly inside the requested month.
4. PASSENGERS:
   - "2 אנשים", "זוג", "שניים", "2 כרטיסים" -> passengers: 2.
5. BAGGAGE:
   - "עם מזוודות", "כולל כבודה", "עם טרולי" -> with_luggage: true.

Extract the flight search parameters:
- "origin": 3-letter IATA code (default 'TLV').
- "destination_iata": 3-letter IATA code.
- "destination_name": City name in Hebrew.
- "departure_date": 'YYYY-MM-DD'.
- "return_date": 'YYYY-MM-DD' or null if one-way.
- "trip_type": 'round-trip' or 'one-way'.
- "direct_only": boolean.
- "currency": 'ILS' or 'USD'.
- "passengers": integer.
- "with_luggage": boolean.
- "user_intent_summary": Concise 1-sentence Hebrew explanation of the exact dates and constraints chosen.

Return ONLY a valid JSON object matching this schema.

User Query: "{user_prompt}"
"""
    client = genai.Client(api_key=GEMINI_API_KEY.strip())
    res = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=enhanced_prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.0
        )
    )
    print("Gemini raw text:")
    print(res.text)
    data = json.loads(res.text)
    print("\nParsed JSON:")
    print(json.dumps(data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    test_prompt("טיסה לוינה 2 אנשים עם מזוודות בתאריך נובמבר עד 5 ימים שיהיה בתאריך 26.11 אבל לא בחזור וגם לא הלוך")
