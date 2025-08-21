import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import Workouts from "./Workouts";
import WorkoutDetail from "./WorkoutDetail";
import Login from "./Login";

ReactDOM.createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/" element={<Workouts />} />
        <Route path="/workouts/:id" element={<WorkoutDetail />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>
);
