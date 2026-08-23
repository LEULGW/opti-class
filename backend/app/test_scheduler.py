from scheduler import (
    TimeSlot,
    Section,
    parse_time_to_military,
    parse_days,
    build_busy_mask,
    generate_valid_schedules,
    score_professor_rating,
)


def test_parse_time_to_military():
    result = parse_time_to_military("4:10 PM")
    assert result == "16:10"
    print("test_parse_time_to_military passed")


def test_parse_days():
    result = parse_days("Tuesday, Thursday")
    assert result == [1, 3]
    print("test_parse_days passed")


def test_build_busy_mask_no_conflict():
    # Two sections on different days should NOT share any busy bits.
    section1 = Section(
        course_code="A 100",
        section_num="1",
        course_name="Course A",
        instructor="Instructor A",
        rating=None,
        time_slots=[TimeSlot(day=0, start_time="09:00", end_time="10:00")],
    )
    section2 = Section(
        course_code="B 100",
        section_num="1",
        course_name="Course B",
        instructor="Instructor B",
        rating=None,
        time_slots=[TimeSlot(day=1, start_time="09:00", end_time="10:00")],
    )

    mask1 = build_busy_mask(section1)
    mask2 = build_busy_mask(section2)

    assert (mask1 & mask2) == 0
    print("test_build_busy_mask_no_conflict passed")


def test_build_busy_mask_with_conflict():
    # Same day, same time - these two sections SHOULD share busy bits.
    section1 = Section(
        course_code="A 100",
        section_num="1",
        course_name="Course A",
        instructor="Instructor A",
        rating=None,
        time_slots=[TimeSlot(day=0, start_time="09:00", end_time="10:00")],
    )
    section2 = Section(
        course_code="B 100",
        section_num="1",
        course_name="Course B",
        instructor="Instructor B",
        rating=None,
        time_slots=[TimeSlot(day=0, start_time="09:50", end_time="11:00")],
    )

    mask1 = build_busy_mask(section1)
    mask2 = build_busy_mask(section2)

    assert (mask1 & mask2) != 0
    print("test_build_busy_mask_with_conflict passed")


def test_generate_valid_schedules_excludes_conflict():
    section_a = Section(
        course_code="A 100",
        section_num="1",
        course_name="Course A",
        instructor="Instructor A",
        rating=None,
        time_slots=[TimeSlot(day=0, start_time="09:00", end_time="10:00")],
    )
    section_a.busy_mask = build_busy_mask(section_a)

    # This section conflicts with section_a (same day, same time).
    section_b_conflict = Section(
        course_code="B 100",
        section_num="1",
        course_name="Course B",
        instructor="Instructor B",
        rating=None,
        time_slots=[TimeSlot(day=0, start_time="09:00", end_time="10:00")],
    )
    section_b_conflict.busy_mask = build_busy_mask(section_b_conflict)

    # This section does NOT conflict (different day).
    section_b_ok = Section(
        course_code="B 100",
        section_num="2",
        course_name="Course B",
        instructor="Instructor B",
        rating=None,
        time_slots=[TimeSlot(day=1, start_time="09:00", end_time="10:00")],
    )
    section_b_ok.busy_mask = build_busy_mask(section_b_ok)

    grouped_courses = {
        "A 100": [section_a],
        "B 100": [section_b_conflict, section_b_ok],
    }

    schedules = generate_valid_schedules(["A 100", "B 100"], grouped_courses)

    # Only one valid schedule should come out - the one using section_b_ok.
    assert len(schedules) == 1
    assert section_b_ok in schedules[0]
    print("test_generate_valid_schedules_excludes_conflict passed")


def test_score_professor_rating():
    section = Section(
        course_code="A 100",
        section_num="1",
        course_name="Course A",
        instructor="Instructor A",
        rating=5.0,
        time_slots=[],
    )

    score = score_professor_rating([section])

    assert score == 100.0
    print("test_score_professor_rating passed")


if __name__ == "__main__":
    test_parse_time_to_military()
    test_parse_days()
    test_build_busy_mask_no_conflict()
    test_build_busy_mask_with_conflict()
    test_generate_valid_schedules_excludes_conflict()
    test_score_professor_rating()

    print("\nAll tests passed!")