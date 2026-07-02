from bs4 import BeautifulSoup
import csv, re, pandas as pd

INPUT_FILE  = "howard_course_sections_workday.html"
OUTPUT_FILE = "howard_courses.csv"


def parse_meeting(text):
    """'ASB-105 | Wednesday | 4:10 PM - 5:00 PM' → (room, days, time)"""
    if not text or text == "N/A":
        return "N/A", "N/A", "N/A"
    # Strip semester date ranges like "| 08/17/2026 - 12/15/2026"
    text = re.sub(r"\|\s*\d{2}/\d{2}/\d{4}\s*-\s*\d{2}/\d{2}/\d{4}", "", text).strip()
    parts = [p.strip() for p in text.split("|") if p.strip()]
    time_pat = re.compile(r"\d{1,2}:\d{2}\s*(AM|PM)")
    day_pat  = re.compile(r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)")
    room, days, time_val = "N/A", "N/A", "N/A"
    for p in parts:
        if time_pat.search(p):
            time_val = p
        elif day_pat.search(p):
            days = p
        elif p:
            room = p
    return room, days, time_val


def parse_course_id(text):
    """'ACAD 007-01 - College Study Skills' → ('ACAD 007', '01')"""
    m = re.match(r"([A-Z]{2,5}\s+\d{3}(?:-\d{3})?)-(\d{2,3})", text)
    if m:
        return m.group(1).strip(), m.group(2).strip()
    return text.strip(), "N/A"


def main():
    print(f"Reading {INPUT_FILE}...")
    with open(INPUT_FILE, "r", encoding="utf-8", errors="ignore") as f:
        soup = BeautifulSoup(f, "html.parser")

    cards = soup.find_all(attrs={"data-automation-id": "compositeContainer"})
    print(f"Found {len(cards)} course sections.")

    rows = []
    for card in cards:
        # All title attributes in this card
        titles = [
            el.get("title", "").strip()
            for el in card.find_all(title=True)
            if el.get("title", "").strip()
        ]

        # Course code + section from first title matching "DEPT 000-00"
        course_title_raw = next(
            (t for t in titles if re.match(r"[A-Z]{2,5}\s+\d{3}", t)), "N/A"
        )
        course_code, section = parse_course_id(course_title_raw)

        # Name | Status | Instructor from compositeSubHeaderOne
        sub = card.find(attrs={"data-automation-id": "compositeSubHeaderOne"})
        sub_parts = [p.strip() for p in sub.get("title", "").split("|")] if sub else []
        course_name = sub_parts[0] if len(sub_parts) > 0 else "N/A"
        status      = sub_parts[1] if len(sub_parts) > 1 else "N/A"
        instructor  = sub_parts[2] if len(sub_parts) > 2 else "N/A"

        # Meeting info from title containing a time pattern
        meeting_raw = next(
            (t for t in titles if re.search(r"\d{1,2}:\d{2}\s*(AM|PM)", t)), "N/A"
        )
        room, days, time_val = parse_meeting(meeting_raw)

        rows.append({
            "Course_Code": course_code or "N/A",
            "Section":     section     or "N/A",
            "Course_Name": course_name or "N/A",
            "Status":      status      or "N/A",
            "Instructor":  instructor  or "N/A",
            "Room":        room,
            "Days":        days,
            "Time":        time_val,
        })

    # Clean up with pandas
    df = pd.DataFrame(rows)
    df["Section"] = df["Section"].apply(
        lambda x: str(int(float(x))) if re.match(r"^\d+\.?\d*$", str(x)) else str(x)
    )
    df = df.fillna("N/A").replace("", "N/A")
    df["Course_Name"] = df["Course_Name"].str.replace("&amp;", "&", regex=False)
    df["Instructor"]  = df["Instructor"].str.replace("&amp;", "&", regex=False)

    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✓ Saved {len(df)} rows to {OUTPUT_FILE}")
    print(f"\nN/A counts (expected for online/self-scheduled courses):")
    print((df == "N/A").sum().to_string())


if __name__ == "__main__":
    main()