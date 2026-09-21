"use client";

import { useState, useEffect } from "react";

export default function Home() {
  const [courses, setCourses] = useState([]);
  const [selected, setSelected] = useState([]);
  const [inputValue, setInputValue] = useState("");

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

      <h2>Selected:</h2>
      <ul>
        {selected.map((code) => (
          <li key={code}>{code}</li>
        ))}
      </ul>
    </div>
  );
}