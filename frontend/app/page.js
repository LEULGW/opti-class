"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [courses, setCourses] = useState([]);
  const [selected, setSelected] = useState([]);
  const [inputValue, setInputValue] = useState("");
  const [professorRating, setProfessorRating] = useState(5);
  const [daysOnCampus, setDaysOnCampus] = useState(5);
  const [compactness, setCompactness] = useState(5);
  const [results, setResults] = useState(null);
  const [allowUnrated, setAllowUnrated] = useState(true);
  const [minRating, setMinRating] = useState("");
  const [excludedDays, setExcludedDays] = useState([]);
  const [maxDays, setMaxDays] = useState("");
  const [earliestStart, setEarliestStart] = useState("");

  useEffect(() => {
    async function loadCourses() {
      const res = await fetch("http://localhost:8000/courses");
      const data = await res.json();
      setCourses(data);
    }
    loadCourses();
  }, []);

  function addCourse() {
    if (courses.includes(inputValue) && !selected.includes(inputValue)) {
      setSelected([...selected, inputValue]);
      setInputValue("");
    }
  }

  function removeCourse(code) {
    setSelected(selected.filter((c) => c !== code));
  }

  function toggleDay(day) {
    if (excludedDays.includes(day)) {
      setExcludedDays(excludedDays.filter((d) => d !== day));
    } else {
      setExcludedDays([...excludedDays, day]);
    }
  }

  async function getSchedules() {
    const res = await fetch("http://localhost:8000/schedules", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        selected_courses: selected,
        constraints: {
          allow_unrated_professors: allowUnrated,
          min_prof_rating: minRating === "" ? null : Number(minRating),
          excluded_days: excludedDays,
          max_days_on_campus: maxDays === "" ? null : Number(maxDays),
          earliest_start_time: earliestStart === "" ? null : earliestStart,
        },
        preferences: {
          professor_rating: professorRating,
          days_on_campus: daysOnCampus,
          compactness: compactness,
        },
      }),
    });
    const data = await res.json();
    setResults(data);
  }

  return (
    <div>
      <h1>Pick your courses</h1>

      <input
        list="course-options"
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
      />
      <datalist id="course-options">
        {courses.map((code) => (
          <option key={code} value={code} />
        ))}
      </datalist>
      <button onClick={addCourse}>Add</button>

      <ul>
        {selected.map((code) => (
          <li key={code}>
            {code} <button onClick={() => removeCourse(code)}>Remove</button>
          </li>
        ))}
      </ul>

      <h2>Constraints</h2>

      <label>
        <input
          type="checkbox"
          checked={allowUnrated}
          onChange={(e) => setAllowUnrated(e.target.checked)}
        />
        Allow unrated professors
      </label>
      <br />

      <label>
        Minimum professor rating:
        <input
          type="number"
          step="0.1"
          value={minRating}
          onChange={(e) => setMinRating(e.target.value)}
        />
      </label>
      <br />

      <p>Exclude days:</p>
      {/* The index (0-4) is what gets stored and sent. Confirm this matches
          how scheduler.py represents days (0 = Mon?). If it uses names like
          "Mon", change toggleDay/excludedDays to use `label` instead of `day`. */}
      {["Mon", "Tue", "Wed", "Thu", "Fri"].map((label, day) => (
        <label key={day}>
          <input
            type="checkbox"
            checked={excludedDays.includes(day)}
            onChange={() => toggleDay(day)}
          />
          {label}
        </label>
      ))}
      <br />

      <label>
        Max days on campus:
        <input
          type="number"
          value={maxDays}
          onChange={(e) => setMaxDays(e.target.value)}
        />
      </label>
      <br />

      <label>
        Earliest start time:
        <input
          type="time"
          value={earliestStart}
          onChange={(e) => setEarliestStart(e.target.value)}
        />
      </label>

      <h2>Preferences</h2>
      <label>
        Professor rating importance: {professorRating}
        <input
          type="range"
          min="1"
          max="10"
          value={professorRating}
          onChange={(e) => setProfessorRating(Number(e.target.value))}
        />
      </label>
      <br />
      <label>
        Fewer days on campus importance: {daysOnCampus}
        <input
          type="range"
          min="1"
          max="10"
          value={daysOnCampus}
          onChange={(e) => setDaysOnCampus(Number(e.target.value))}
        />
      </label>
      <br />
      <label>
        Compactness importance: {compactness}
        <input
          type="range"
          min="1"
          max="10"
          value={compactness}
          onChange={(e) => setCompactness(Number(e.target.value))}
        />
      </label>

      <br />
      <button onClick={getSchedules}>Get Schedules</button>

      <h2>Results</h2>
      {results && results.length === 0 && <p>No valid schedules found.</p>}

      {results &&
        results.map((schedule, i) => (
          <div
            key={i}
            style={{ border: "1px solid black", margin: "10px", padding: "10px" }}
          >
            <h3>
              Option {i + 1} — Score: {schedule.score.toFixed(1)}
            </h3>
            <ul>
              {schedule.sections.map((section) => (
                <li key={section.course_code}>
                  {section.course_code} — {section.course_name} (
                  {section.instructor}, rating: {section.rating ?? "N/A"})
                  <ul>
                    {section.time_slots.map((slot, j) => (
                      <li key={j}>
                        Day {slot.day}: {slot.start_time}–{slot.end_time}
                      </li>
                    ))}
                  </ul>
                </li>
              ))}
            </ul>
          </div>
        ))}
    </div>
  );
}