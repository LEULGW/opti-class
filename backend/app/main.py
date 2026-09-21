"""
Entry point for the backend. Run with:
    uvicorn app.main:app --reload
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "processed"
grouped_courses: dict[str, list[Section]] = {}


@app.on_event("startup")
def load_data_on_startup():
    global grouped_courses
    grouped_courses = load_and_merge_data(
        DATA_DIR / "howard_courses.csv",
        DATA_DIR / "howard_professors_rmp.csv",
    )


# What the frontend sends us, and what we send back.
# Declaring these is what makes /docs able to auto-generate a fillable
# request body - that's the piece that broke when we dropped Pydantic.

class HardConstraintsIn(BaseModel):
    allow_unrated_professors: bool = True
    min_prof_rating: float | None = None
    excluded_days: list[int] = []
    max_days_on_campus: int | None = None
    earliest_start_time: str | None = None


class PreferencesIn(BaseModel):
    professor_rating: float = 5
    days_on_campus: float = 5
    compactness: float = 5


class ScheduleRequest(BaseModel):
    selected_courses: list[str]
    constraints: HardConstraintsIn = HardConstraintsIn()
    preferences: PreferencesIn = PreferencesIn()
    max_results: int = 20


class SectionOut(BaseModel):
    course_code: str
    section_num: str
    course_name: str
    instructor: str
    rating: float | None
    time_slots: list[dict]


class ScheduleResponse(BaseModel):
    score: float
    sections: list[SectionOut]


def section_to_out(section: Section) -> SectionOut:
    return SectionOut(
        course_code=section.course_code,
        section_num=section.section_num,
        course_name=section.course_name,
        instructor=section.instructor,
        rating=section.rating,
        time_slots=[
            {"day": s.day, "start_time": s.start_time, "end_time": s.end_time}
            for s in section.time_slots
        ],
    )


@app.get("/courses")
def list_courses():
    return sorted(grouped_courses.keys())


@app.post("/schedules")
def get_schedules(req: ScheduleRequest):
    constraints = HardConstraints(**req.constraints.model_dump())
    preference_weights = req.preferences.model_dump()

    all_schedules = generate_valid_schedules(req.selected_courses, grouped_courses)
    valid_schedules = filter_schedules_by_hard_constraints(all_schedules, constraints)

    ranked = sorted(
        valid_schedules,
        key=lambda s: score_schedule(s, preference_weights),
        reverse=True,
    )

    top = ranked[: req.max_results]

    return [
        ScheduleResponse(
            score=score_schedule(schedule, preference_weights),
            sections=[section_to_out(s) for s in schedule],
        )
        for schedule in top
    ]