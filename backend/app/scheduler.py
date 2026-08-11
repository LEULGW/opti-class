import pandas as pd

from datetime import datetime
from dataclasses import dataclass, field
from pathlib import Path
from collections import defaultdict
from typing import Dict, List

BASE_DIR = Path(__file__).resolve().parent.parent.parent


# Data Models
@dataclass
class TimeSlot:
    day: int
    start_time: str
    end_time: str


@dataclass
class Section:
    course_code: str
    section_num: str
    course_name: str
    instructor: str
    rating: float | None
    time_slots: List[TimeSlot]
    busy_mask: int = 0 


@dataclass
class HardConstraints:
    """Everything a schedule MUST satisfy, or it gets dropped entirely
    (never even reaches scoring)."""

    allow_unrated_professors: bool = True
    min_prof_rating: float | None = None
    excluded_days: List[int] = field(default_factory=list)
    max_days_on_campus: int | None = None
    earliest_start_time: str | None = None  # e.g. "10:00" means no class before 10am


# Parsing Helpers
DAY_MAP = {
    "Monday": 0,
    "Tuesday": 1,
    "Wednesday": 2,
    "Thursday": 3,
    "Friday": 4,
    "Saturday": 5,
    "Sunday": 6,
}


def parse_time_to_military(time_str: str) -> str:
    """Convert '4:10 PM' -> '16:10'."""
    time_str = time_str.strip()
    parsed_time = datetime.strptime(time_str, "%I:%M %p")
    return parsed_time.strftime("%H:%M")


def time_to_minutes(time_str: str) -> int:
    """Convert 'HH:MM' -> minutes since midnight. '16:10' -> 970."""
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    return hours * 60 + minutes


def parse_days(days_str: str) -> List[int]:
    """Convert 'Monday, Wednesday' -> [0, 2]."""

    day_numbers = []

    for day in days_str.split(","):
        cleaned_day = day.strip().title()

        if cleaned_day in DAY_MAP:
            day_numbers.append(DAY_MAP[cleaned_day])
        else:
            print(f"WARNING: unrecognized day value '{cleaned_day}' in '{days_str}'")

    return day_numbers



# Bitmask Conflict Detection
#
# Each Section gets one big integer (busy_mask) representing every 5-minute
# block of the week it's in class. Bit 0 = Monday 00:00-00:05, and so on,
# moving forward through the week.
#
 
BLOCK_SIZE_MINUTES = 5
MINUTES_PER_DAY = 24 * 60
 
 
def build_busy_mask(section: Section) -> int:
    """Builds the busy_mask for one section from its time_slots.
 
    Example: a Tuesday 11:10-12:00 class sets the bits covering that
    specific 50-minute window on Tuesday, and nothing else.
    """
 
    mask = 0
 
    for slot in section.time_slots:
        start_minutes = time_to_minutes(slot.start_time)
        end_minutes = time_to_minutes(slot.end_time)
 
        day_offset_minutes = slot.day * MINUTES_PER_DAY
 
        start_block = (day_offset_minutes + start_minutes) // BLOCK_SIZE_MINUTES
        end_block = (day_offset_minutes + end_minutes) // BLOCK_SIZE_MINUTES
 
        for block in range(start_block, end_block):
            mask = mask | (1 << block)
 
    return mask


def generate_valid_schedules(
    selected_courses: List[str],
    grouped_courses: Dict[str, List[Section]],
) -> List[List[Section]]:
    """Generate every schedule with no time conflicts, one section per selected course."""

    missing = []
    for course in selected_courses:
        if course not in grouped_courses:
            missing.append(course)

    if missing:
        raise ValueError(f"No sections found for: {missing}")

    schedules = []

    def dfs(path: List[Section], occupied_mask: int):

        if len(path) == len(selected_courses):
            schedules.append(path.copy())
            return

        course_code = selected_courses[len(path)]

        for section in grouped_courses[course_code]:

            if (occupied_mask & section.busy_mask) != 0:
                continue

            path.append(section)
            dfs(path, occupied_mask | section.busy_mask)
            path.pop()
    
    dfs([], 0)

    return schedules



def has_unrated_professor(schedule: List[Section]) -> bool:
    """Returns True if any section in the schedule has no RMP rating (None)."""

    for section in schedule:
        if section.rating is None:
            return True

    return False

def has_professor_below_min_rating(schedule: List[Section], min_rating: float) -> bool:
    """Returns True if any section in the schedule has a professor rating below the specified minimum."""

    for section in schedule:
        if section.rating is not None and section.rating < min_rating:
            return True

    return False


def has_class_on_excluded_day(schedule: List[Section], excluded_days: List[int]) -> bool:
    """Returns True if any section in the schedule meets on a day the student excluded."""

    for section in schedule:
        for slot in section.time_slots:
            if slot.day in excluded_days:
                return True

    return False


def exceeds_max_days(schedule: List[Section], max_days: int) -> bool:
    """Returns True if the schedule uses more distinct days than the student's max."""

    days_used = set()
    for section in schedule:
        for slot in section.time_slots:
            days_used.add(slot.day)

    return len(days_used) > max_days


def has_class_before_time(schedule: List[Section], earliest_start_time: str) -> bool:
    """Returns True if any section starts earlier than earliest_start_time (e.g. '10:00')."""

    for section in schedule:
        for slot in section.time_slots:
            if slot.start_time < earliest_start_time:
                return True

    return False


def schedule_passes_hard_constraints(schedule: List[Section], constraints: HardConstraints) -> bool:
    """Checks a single schedule against every hard constraint. Returns False
    the moment any single constraint is violated."""

    if not constraints.allow_unrated_professors:
        if has_unrated_professor(schedule):
            return False
    
    if constraints.min_prof_rating is not None:
        if has_professor_below_min_rating(schedule, constraints.min_prof_rating):
            return False

    if len(constraints.excluded_days) > 0:
        if has_class_on_excluded_day(schedule, constraints.excluded_days):
            return False

    if constraints.max_days_on_campus is not None:
        if exceeds_max_days(schedule, constraints.max_days_on_campus):
            return False

    if constraints.earliest_start_time is not None:
        if has_class_before_time(schedule, constraints.earliest_start_time):
            return False

    return True


def filter_schedules_by_hard_constraints(
    schedules: List[List[Section]],
    constraints: HardConstraints,
) -> List[List[Section]]:
    """Drops every schedule that fails any hard constraint. What survives is
    the pool that scoring will rank."""

    filtered = []
    for schedule in schedules:
        if schedule_passes_hard_constraints(schedule, constraints):
            filtered.append(schedule)

    return filtered



def load_and_merge_data(
    courses_path: str | Path,
    rmp_path: str | Path,
) -> Dict[str, List[Section]]:
    """
    Load course data and professor ratings, merge rows that belong to the
    same section (a section can span multiple rows if it has more than one
    meeting pattern), and group sections by course code.
    """

    courses_df = pd.read_csv(courses_path)
    rmp_df = pd.read_csv(rmp_path)

    professor_ratings = dict(
        zip(
            rmp_df["Name"].str.lower(),
            rmp_df["Overall_Rating"],
        )
    )

    # First pass: build a lookup of (course_code, section_num) -> Section,
    # so rows belonging to the same real section get merged together
    # instead of creating duplicate Section objects.
    sections_by_key = {}

    for _, row in courses_df.iterrows():

        if row["Days"] == "N/A" or row["Time"] == "N/A":
            continue

        try:
            start_str, end_str = row["Time"].split("-")
            start_time = parse_time_to_military(start_str)
            end_time = parse_time_to_military(end_str)
        except Exception:
            continue

        days = parse_days(str(row["Days"]))

        new_slots = []
        for day in days:
            new_slots.append(TimeSlot(day=day, start_time=start_time, end_time=end_time))

        instructor = str(row["Instructor"]).strip()
        rating = professor_ratings.get(instructor.lower())

        key = (row["Course_Code"], str(row["Section"]))

        if key in sections_by_key:
            # This section already exists from an earlier row - just add
            # this row's TimeSlots onto it, don't create a duplicate Section.
            sections_by_key[key].time_slots.extend(new_slots)
        else:
            sections_by_key[key] = Section(
                course_code=row["Course_Code"],
                section_num=str(row["Section"]),
                course_name=row["Course_Name"],
                instructor=instructor,
                rating=rating,
                time_slots=new_slots,
            )

    # Second pass: group the now-merged sections by course code.
    grouped_courses = defaultdict(list)
    for key in sections_by_key:
        section = sections_by_key[key]
        section.busy_mask = build_busy_mask(section)
        grouped_courses[section.course_code].append(section)

    return dict(grouped_courses)


# Student Input (placeholders - real versions come from the frontend later)
def get_student_selection() -> List[str]:
    """Placeholder. Later this will come from the frontend."""
    return [
        "SWAH 001",
        "ACCT 201",
        "ACAD 100",
    ]


def get_hard_constraints() -> HardConstraints:
    """Placeholder. Later this will come from the frontend. Change the values
    below to test different constraints locally."""
    return HardConstraints(
        allow_unrated_professors=True,
        min_prof_rating=None,
        excluded_days=[],
        max_days_on_campus=None,
        earliest_start_time=None,
    )


# Schedule Scoring (Soft Constraints - only runs on schedules that already
# passed the hard constraints above)
def score_professor_rating(schedule: List[Section]) -> float:
    """Average professor rating across the schedule, scaled from a 0-5 range to 0-100.
    Sections with no rating (None) are skipped rather than counted as 0."""

    ratings = []
    for section in schedule:
        if section.rating is not None:
            ratings.append(section.rating)

    if len(ratings) == 0:
        return 0.0

    total = 0
    for rating in ratings:
        total += rating

    average_rating = total / len(ratings)
    score = (average_rating / 5.0) * 100

    return score


def score_days_on_campus(schedule: List[Section]) -> float:
    """Fewer distinct days with classes scores higher. Best case (1 day) = 100,
    worst case (5 days, Mon-Fri) = 0. This is a PREFERENCE, separate from the
    hard 'max_days_on_campus' constraint above - a student can prefer fewer
    days without requiring a strict cutoff."""

    days_used = set()
    for section in schedule:
        for slot in section.time_slots:
            days_used.add(slot.day)

    num_days = len(days_used)

    if num_days <= 1:
        return 100.0

    score = 100 - ((num_days - 1) / 4 * 100)

    if score < 0:
        score = 0

    return score


def score_schedule(
    schedule: List[Section],
    preferences: dict | None = None,
) -> float:
    """
    Combines sub-scores into one weighted score, 0-100.

    Still a work in progress - gap time and compactness scoring not added yet.
    """

    if preferences is None:
        preferences = {
            "professor_rating": 1,
            "days_on_campus": 1,
        }

    subscores = {
        "professor_rating": score_professor_rating(schedule),
        "days_on_campus": score_days_on_campus(schedule),
    }

    total_weight = 0
    weighted_sum = 0

    for key in subscores:
        weight = preferences.get(key, 0)
        weighted_sum += subscores[key] * weight
        total_weight += weight

    if total_weight == 0:
        return 0.0

    return weighted_sum / total_weight


# Main
def main():

    grouped_courses = load_and_merge_data(
        BASE_DIR / "backend" / "data" / "processed" / "howard_courses.csv",
        BASE_DIR / "backend" / "data" / "processed" / "howard_professors_rmp.csv",
    )

    selected_courses = get_student_selection()

    # Step 1: generate every combination with no time conflicts
    schedules = generate_valid_schedules(
        selected_courses,
        grouped_courses,
    )
    print(f"{len(schedules)} schedules before hard constraints")

    # Step 2: drop anything that fails a hard constraint (ratings, excluded
    # days, max days on campus, earliest start time)
    constraints = get_hard_constraints()
    schedules = filter_schedules_by_hard_constraints(
        schedules,
        constraints,
    )
    print(f"{len(schedules)} schedules after hard constraints")

    # Step 3: score and rank only what survived filtering
    scored_schedules = []
    for schedule in schedules:
        score = score_schedule(schedule)
        scored_schedules.append((schedule, score))

    scored_schedules.sort(key=lambda pair: pair[1], reverse=True)

    print(f"\nFound {len(scored_schedules)} valid schedules")

    for schedule, score in scored_schedules[:3]:

        print(f"\nScore: {score:.1f}")

        for section in schedule:
            print(
                f"{section.course_code} | "
                f"Section {section.section_num} | "
                f"{section.instructor} | "
                f"rating={section.rating}"
            )


if __name__ == "__main__":
    main()