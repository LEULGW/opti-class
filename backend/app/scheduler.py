import pandas as pd
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

@dataclass
class TimeSlot:
    day: int        # 0=Mon, 1=Tue, etc.
    start_time: str # "HH:MM" military time
    end_time: str   # "HH:MM" military time

@dataclass
class Section:
    course_code: str
    section_num: str
    course_name: str
    instructor: str
    rating: float
    time_slots: List[TimeSlot]

def parse_time_to_military(time_str: str) -> str:
    """Converts a time string like '4:10 PM' to a 24-hour 'HH:MM' string."""
    time_str = time_str.strip()
    t = datetime.strptime(time_str, "%I:%M %p")
    return t.strftime("%H:%M")


def parse_days(days_str: str) -> List[int]:
    """Maps day strings like 'Monday, Wednesday' to integers [0, 2]."""
    day_map = {"Monday": 0, "Tuesday": 1, "Wednesday": 2, "Thursday": 3, "Friday": 4, "Saturday": 5, "Sunday": 6}
    # Split by comma since Workday uses comma-separated strings for multi-day courses
    return [day_map[day.strip()] for day in days_str.split(',')]

def have_conflict(section1: Section, section2: Section) -> bool:
    """Returns True if there is a time overlap between any timeslots of two sections."""
    for slot1 in section1.time_slots:
        for slot2 in section2.time_slots:
            if slot1.day == slot2.day:
                start1, end1 = slot1.start_time, slot1.end_time
                start2, end2 = slot2.start_time, slot2.end_time

                if start1 < start2:
                    if start2 < end1:
                        return True
                else:
                    if start1 < end2:
                        return True
    return False

def load_and_merge_data(courses_path: str, rmp_path: str) -> Dict[str, List[Section]]:
    """Loads CSVs, links professor ratings, and groups sections by Course_Code."""
    courses_df = pd.read_csv(courses_path)
    rmp_df = pd.read_csv(rmp_path)
    
    # Quick dictionary for rapid lookup of professor ratings
    prof_ratings = dict(zip(rmp_df['Name'].str.lower(), rmp_df['Overall_Rating']))
    
    grouped_courses = {}
    
    for _, row in courses_df.iterrows():
        # Clean check utilizing your pre-cleaned "N/A" dataset markers
        if row['Days'] == 'N/A' or row['Time'] == 'N/A':
            continue
            
        # Parse time range (e.g., "4:10 PM - 5:00 PM")
        try:
            start_str, end_str = row['Time'].split('-')
            start_time = parse_time_to_military(start_str)
            end_time = parse_time_to_military(end_str)
        except Exception:
            continue 
            
        # Extract days and map them to their numeric values
        days = parse_days(str(row['Days']))
        slots = [TimeSlot(day=d, start_time=start_time, end_time=end_time) for d in days]

        # Match professor rating (assign None if missing from your RMP data)
        prof_name = str(row['Instructor']).strip().lower()
        rating = prof_ratings.get(prof_name, None)
        
        section = Section(
            course_code=row['Course_Code'],
            section_num=str(row['Section']),
            course_name=row['Course_Name'],
            instructor=row['Instructor'],
            rating=rating,  # This will be float or None
            time_slots=slots
        )
        
        if section.course_code not in grouped_courses:
            grouped_courses[section.course_code] = []
        grouped_courses[section.course_code].append(section)
        
    return grouped_courses

# Quick local testing execution
if __name__ == "__main__":
    data = load_and_merge_data(
        BASE_DIR / "backend" / "data" / "processed" / "howard_courses.csv",
        BASE_DIR / "backend" / "data" / "processed" / "howard_professors_rmp.csv"
    )
    print(f"Successfully processed {len(data)} unique courses into memory.")