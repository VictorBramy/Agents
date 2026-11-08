import re
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

def enforce_flight_intent_constraints(data: Dict[str, Any], user_prompt: str, today: Optional[datetime] = None) -> Dict[str, Any]:
    if not today:
        today = datetime.now()
    prompt_lower = user_prompt.lower()

    # 1. Passengers count enforcement
    pax_match = re.search(r'(\d+)\s*(?:אנשים|נוסעים|נוסע|כרטיסים|מבוגרים|adults?|passengers?|pax)', user_prompt, re.IGNORECASE)
    if pax_match:
        data["passengers"] = int(pax_match.group(1))
    elif any(w in user_prompt for w in ["זוג", "שנינו", "שני אנשים", "שני נוסעים", "שתי נוסעות", "couple"]):
        data["passengers"] = 2
    elif any(w in user_prompt for w in ["שלושה אנשים", "שלושה נוסעים", "3 אנשים"]):
        data["passengers"] = 3
    elif any(w in user_prompt for w in ["ארבעה אנשים", "ארבעה נוסעים", "4 אנשים"]):
        data["passengers"] = 4
    elif not data.get("passengers"):
        data["passengers"] = 1

    # 2. Max duration extraction (e.g. "עד 5 ימים", "מקסימום 4 ימים", "למשך 3 ימים")
    max_days = None
    dur_match = re.search(r'(?:עד|מקסימום|למשך|סביב)?\s*(\d+)\s*(?:ימים|יום|יממות|days?)', user_prompt, re.IGNORECASE)
    if dur_match:
        max_days = int(dur_match.group(1))

    # 3. Target month extraction
    month_map = {
        "ינואר": 1, "january": 1, "jan": 1,
        "פברואר": 2, "february": 2, "feb": 2,
        "מרץ": 3, "מרס": 3, "march": 3, "mar": 3,
        "אפריל": 4, "april": 4, "apr": 4,
        "מאי": 5, "may": 5,
        "יוני": 6, "june": 6, "jun": 6,
        "יולי": 7, "july": 7, "jul": 7,
        "אוגוסט": 8, "august": 8, "aug": 8,
        "ספטמבר": 9, "september": 9, "sep": 9,
        "אוקטובר": 10, "october": 10, "oct": 10,
        "נובמבר": 11, "november": 11, "nov": 11,
        "דצמבר": 12, "december": 12, "dec": 12
    }
    target_month = None
    for m_name, m_num in month_map.items():
        if m_name in prompt_lower:
            target_month = m_num
            break

    # 4. Target in-stay date extraction (e.g. "26.11", "26/11", "26 בנובמבר")
    date_match = re.search(r'(\d{1,2})[./\-](\d{1,2})(?:[./\-](\d{2,4}))?', user_prompt)
    target_date = None
    if date_match:
        d = int(date_match.group(1))
        m = int(date_match.group(2))
        y = int(date_match.group(3)) if date_match.group(3) else today.year
        if y < 100:
            y += 2000
        try:
            target_date = datetime(y, m, d)
            if target_date.date() < today.date():
                target_date = datetime(y + 1, m, d)
        except ValueError:
            target_date = None
    elif target_month:
        day_match = re.search(r'(\d{1,2})\s*(?:ב)?(?:ינואר|פברואר|מרץ|מרס|אפריל|מאי|יוני|יולי|אוגוסט|ספטמבר|אוקטובר|נובמבר|דצמבר)', user_prompt)
        if day_match:
            d = int(day_match.group(1))
            try:
                target_date = datetime(today.year, target_month, d)
                if target_date.date() < today.date():
                    target_date = datetime(today.year + 1, target_month, d)
            except ValueError:
                target_date = None

    # 5. Check for negative flight constraint relative to the date
    # E.g. "אבל לא בחזור וגם לא הלוך", "לא בהלוך ולא בחזור", "לא לטוס ב-"
    has_negative_flight_constraint = bool(re.search(
        r'(?:אבל\s+)?לא\s+(?:ב|ל)?(?:חזור|הלוך)|'
        r'לא\s+בהלוך\s+ולא\s+בחזור|'
        r'לא\s+בחזור\s+וגם\s+לא\s+הלוך|'
        r'שלא\s+יהיה\s+(?:הלוך|חזור)|'
        r'לא\s+לטוס\s+ב|'
        r'לא\s+ביום\s+הטיסה|'
        r'not\s+on\s+(?:departure|return|flight)',
        user_prompt,
        re.IGNORECASE
    ))

    # Check for in-stay requirement: "שיהיה ב", "לשהות ב", "להיות ב"
    has_in_stay_intent = bool(re.search(
        r'(?:שיהיה|להיות|לשהות|אירוע|נוכח|שאהיה|שנהיה)\s+(?:ב|ל|בתאריך)|'
        r'be\s+there\s+on|stay\s+(?:over|during|on)',
        user_prompt,
        re.IGNORECASE
    )) or has_negative_flight_constraint

    if target_date and has_negative_flight_constraint:
        target_str = target_date.strftime("%Y-%m-%d")
        curr_dep = data.get("departure_date")
        curr_ret = data.get("return_date")

        needs_adjustment = False
        if curr_dep == target_str or curr_ret == target_str:
            needs_adjustment = True
        elif not curr_dep or curr_dep >= target_str:
            needs_adjustment = True
        elif not curr_ret or curr_ret <= target_str:
            needs_adjustment = True

        # Check duration if specified
        if not needs_adjustment and curr_dep and curr_ret and max_days:
            try:
                dt_dep = datetime.strptime(curr_dep, "%Y-%m-%d")
                dt_ret = datetime.strptime(curr_ret, "%Y-%m-%d")
                if (dt_ret - dt_dep).days > max_days:
                    needs_adjustment = True
            except ValueError:
                needs_adjustment = True

        if needs_adjustment:
            # We want departure strictly before target_date, and return strictly after target_date
            duration = max_days if max_days and 2 <= max_days <= 14 else 4
            
            # Place target_date in the middle of stay
            dep_dt = target_date - timedelta(days=2)
            ret_dt = dep_dt + timedelta(days=duration)

            # Ensure departure is not in the past
            if dep_dt.date() < today.date():
                dep_dt = target_date - timedelta(days=1)
                ret_dt = dep_dt + timedelta(days=duration)

            # Target month adherence
            if target_month:
                if dep_dt.month != target_month:
                    dep_dt = target_date - timedelta(days=1)
                    ret_dt = dep_dt + timedelta(days=duration)
                if ret_dt.month != target_month and duration > 2:
                    ret_dt = target_date + timedelta(days=2)
                    dep_dt = ret_dt - timedelta(days=duration)

            # Strict negative condition verification: neither flight on target_date
            if dep_dt.strftime("%Y-%m-%d") == target_str:
                dep_dt -= timedelta(days=1)
            if ret_dt.strftime("%Y-%m-%d") == target_str:
                ret_dt += timedelta(days=1)

            data["departure_date"] = dep_dt.strftime("%Y-%m-%d")
            data["return_date"] = ret_dt.strftime("%Y-%m-%d")
            data["trip_type"] = "round-trip"

    # 6. Baggage flag
    if any(w in user_prompt for w in ["עם מזוודות", "עם כבודה", "כולל מזוודה", "כולל כבודה", "with luggage", "with bags"]):
        data["baggage"] = "checked"

    # 7. Update summary with explicit details
    dest_name = data.get("destination_name") or "היעד"
    dep = data.get("departure_date")
    ret = data.get("return_date")
    pax = data.get("passengers", 1)
    
    extra_notes = []
    if target_date and has_negative_flight_constraint:
        t_fmt = target_date.strftime("%d/%m")
        extra_notes.append(f"כולל שהות ב-{t_fmt} (ללא טיסה ביום זה)")
    if data.get("baggage") == "checked":
        extra_notes.append("כולל כבודה ומזוודות")
    if max_days:
        extra_notes.append(f"עד {max_days} ימים")

    notes_str = f" [{', '.join(extra_notes)}]" if extra_notes else ""
    if ret:
        data["summary"] = f"טיסה ל{dest_name} ל-{pax} נוסעים (יציאה {dep}, חזרה {ret}){notes_str}"
    else:
        data["summary"] = f"טיסה בכיוון אחד ל{dest_name} ל-{pax} נוסעים (יציאה {dep}){notes_str}"

    return data

if __name__ == "__main__":
    prompt = "טיסה לוינה 2 אנשים עם מזוודות בתאריך נובמבר עד 5 ימים שיהיה בתאריך 26.11 אבל לא בחזור וגם לא הלוך"
    # Test case 1: LLM incorrectly returned departure_date = 2026-11-26
    flawed_data = {
        "origin": "TLV",
        "destination": "VIE",
        "destination_name": "וינה",
        "departure_date": "2026-11-26",
        "return_date": "2026-12-01",
        "trip_type": "round-trip",
        "passengers": 1
    }
    corrected = enforce_flight_intent_constraints(flawed_data, prompt, datetime(2026, 11, 7))
    print("Corrected flawed LLM data:")
    print(corrected)
    assert corrected["departure_date"] != "2026-11-26", "Departure must not be 26.11!"
    assert corrected["return_date"] != "2026-11-26", "Return must not be 26.11!"
    assert corrected["departure_date"] < "2026-11-26" < corrected["return_date"], "Stay must encompass 26.11!"
    dep_dt = datetime.strptime(corrected["departure_date"], "%Y-%m-%d")
    ret_dt = datetime.strptime(corrected["return_date"], "%Y-%m-%d")
    assert (ret_dt - dep_dt).days <= 5, "Trip duration must be <= 5 days!"
    assert corrected["passengers"] == 2, "Passengers must be 2!"
    assert corrected["baggage"] == "checked", "Baggage must be checked!"
    print("ALL ASSERTIONS PASSED SUCCESSFULLY!")
