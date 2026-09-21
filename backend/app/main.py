"""
Entry point for the backend. Run with:
    uvicorn app.main:app --reload

No Pydantic here on purpose - request bodies are read as plain dicts,
and responses are built as plain dicts/lists. FastAPI just needs
regular JSON-serializable Python (dicts, lists, strings, numbers) to
turn into a response - it doesn't require any special classes.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.scheduler import (
    HardConstraints,
    Section,
    load_and_merge_data,
    generate_valid_schedules,
    filter_schedules_by_hard_constraints,
    score_schedule,
)

app = FastAPI(title="Howard Scheduler API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Loaded once at startup, reused by every request below.
DATA_DIR = Path(__file__).resolve().parent / "data" / "processed"
grouped_courses: dict[str, list[Section]] = {}


@app.on_event("startup")
def load_data_on_startup():
    global grouped_courses
    grouped_courses = load_and_merge_data(
        DATA_DIR / "howard_courses.csv",
        DATA_DIR / "howard_professors_rmp.csv",
    )


def section_to_dict(section: Section) -> dict:
    """Turns one Section object into a plain dict, since dataclass
    instances aren't automatically JSON-serializable."""
    return {
        "course_code": section.course_code,
        "section_num": section.section_num,
        "course_name": section.course_name,
        "instructor": section.instructor,
        "rating": section.rating,
        "time_slots": [
            {"day": s.day, "start_time": s.start_time, "end_time": s.end_time}
            for s in section.time_slots
        ],
    }


@app.get("/courses")
def list_courses():
    return sorted(grouped_courses.keys())


@app.post("/schedules")
async def get_schedules(request: Request):
    # request.json() reads and parses the raw JSON body the frontend sent.
    # body is just a plain dict at this point - e.g.
    # {"selected_courses": ["CS101"], "constraints": {...}, "preferences": {...}}
    body = await request.json()

    selected_courses = body["selected_courses"]

    # .get(key, default) reads a key if it's there, otherwise falls back -
    # this is doing by hand what Pydantic was doing automatically before.
    constraints_in = body.get("constraints", {})
    constraints = HardConstraints(
        allow_unrated_professors=constraints_in.get("allow_unrated_professors", True),
        min_prof_rating=constraints_in.get("min_prof_rating"),
        excluded_days=constraints_in.get("excluded_days", []),
        max_days_on_campus=constraints_in.get("max_days_on_campus"),
        earliest_start_time=constraints_in.get("earliest_start_time"),
    )

    preference_weights = body.get("preferences", {
        "professor_rating": 5,
        "days_on_campus": 5,
        "compactness": 5,
    })

    max_results = body.get("max_results", 20)

    all_schedules = generate_valid_schedules(selected_courses, grouped_courses)
    valid_schedules = filter_schedules_by_hard_constraints(all_schedules, constraints)

    ranked = sorted(
        valid_schedules,
        key=lambda s: score_schedule(s, preference_weights),
        reverse=True,
    )

    top = ranked[:max_results]

    return [
        {
            "score": score_schedule(schedule, preference_weights),
            "sections": [section_to_dict(s) for s in schedule],
        }
        for schedule in top
    ]