import sys
import json
from flight_agent.ai_advisor import parse_flight_intent

sys.stdout.reconfigure(encoding='utf-8')

prompt = "טיסה ל2 אנשים  לרומא 3-4 לילות טיסה ישירה חובה שהתאריך 26.11 יהיה חלק מהימים אבל לא ביום של ההלוך ולא ביום של החזור עם מזוודות"

print("Parsing prompt:", prompt)
res = parse_flight_intent(prompt)
print("\n--- RESULT ---")
print("destination:", res.get("destination"))
print("departure_date:", res.get("departure_date"))
print("return_date:", res.get("return_date"))
print("passengers:", res.get("passengers"))
print("min_nights:", res.get("min_nights"))
print("max_nights:", res.get("max_nights"))
print("candidate_date_options count:", len(res.get("candidate_date_options", [])))
for opt in res.get("candidate_date_options", []):
    print("  Candidate:", opt.get("departure_date"), "->", opt.get("return_date"), "nights:", opt.get("nights"), "label:", opt.get("label"), "price:", opt.get("price"))
