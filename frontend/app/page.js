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
  const [maxResults, setMaxResults] = useState(5);

  useEffect(() => {
    async function loadCourses() {
      const res = await fetch("https://opti-class.onrender.com/courses");
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
    if (selected.length === 0) {
      alert("Please select at least one course.");
      return;
    }

    const res = await fetch("https://opti-class.onrender.com/schedules", {
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
        max_results: maxResults === "" ? 5 : Number(maxResults),
      }),
    });
    const data = await res.json();
    setResults(data);
  }

  return (
    <div className="container">
      <h1>Course Scheduler</h1>

      <div className="course-picker">
        <input
          type="text"
          list="course-options"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          placeholder="Type a course code..."
        />
        <datalist id="course-options">
          {courses.map((code) => (
            <option key={code} value={code} />
          ))}
        </datalist>
        <button onClick={addCourse}>Add</button>
      </div>

      <ul className="selected-list">
        {selected.map((code) => (
          <li key={code}>
            {code}
            <button className="remove-btn" onClick={() => removeCourse(code)}>
              Remove
            </button>
          </li>
        ))}
      </ul>

      <h2>Constraints</h2>

      <div className="checkbox-row">
        <label>
          <input
            type="checkbox"
            checked={allowUnrated}
            onChange={(e) => setAllowUnrated(e.target.checked)}
          />
          Allow unrated professors
        </label>
      </div>

      <div className="field-row">
        <label>Minimum professor rating</label>
        <input
          type="number"
          step="0.1"
          value={minRating}
          onChange={(e) => setMinRating(e.target.value)}
        />
      </div>

      <div className="field-row">
        <label>Exclude days</label>
        <div className="checkbox-row">
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
        </div>
      </div>

      <div className="field-row">
        <label>Max days on campus</label>
        <input
          type="number"
          value={maxDays}
          onChange={(e) => setMaxDays(e.target.value)}
        />
      </div>

      <div className="field-row">
        <label>Earliest start time</label>
        <input
          type="time"
          value={earliestStart}
          onChange={(e) => setEarliestStart(e.target.value)}
        />
      </div>

      <h2>Preferences</h2>

      <div className="field-row">
        <label>Professor rating importance: {professorRating}</label>
        <input
          type="range"
          min="1"
          max="10"
          value={professorRating}
          onChange={(e) => setProfessorRating(Number(e.target.value))}
        />
      </div>

      <div className="field-row">
        <label>Fewer days on campus importance: {daysOnCampus}</label>
        <input
          type="range"
          min="1"
          max="10"
          value={daysOnCampus}
          onChange={(e) => setDaysOnCampus(Number(e.target.value))}
        />
      </div>

      <div className="field-row">
        <label>Compactness importance: {compactness}</label>
        <input
          type="range"
          min="1"
          max="10"
          value={compactness}
          onChange={(e) => setCompactness(Number(e.target.value))}
        />
      </div>

      <div className="field-row">
        <label>How many results do you want?</label>
        <input
          type="number"
          min="1"
          value={maxResults}
          onChange={(e) => setMaxResults(e.target.value)}
        />
      </div>

      <button className="get-schedules-btn" onClick={getSchedules}>
        Get Schedules
      </button>

      <h2>Results</h2>
      {results && results.length === 0 && (
        <p className="empty-note">No valid schedules found.</p>
      )}

      {results &&
        results.map((schedule, i) => (
          <div key={i} className="schedule-card">
            <div style={{ flex: 1 }}>
              <h3>Option {i + 1}</h3>
              {schedule.sections.map((section) => (
                <div key={section.course_code} className="section-entry">
                  <div className="section-title">
                    {section.course_code} — {section.course_name}
                  </div>
                  <div className="section-meta">
                    {section.instructor}, rating: {section.rating ?? "N/A"}
                  </div>
                  {section.time_slots.map((slot, j) => (
                    <div key={j} className="time-slot">
                      {slot.day}: {slot.start_time}–{slot.end_time}
                    </div>
                  ))}
                </div>
              ))}
            </div>
            <div className="schedule-score">{schedule.score.toFixed(1)}</div>
          </div>
        ))}
    </div>
  );
}