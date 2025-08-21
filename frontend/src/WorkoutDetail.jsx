import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

function WorkoutDetail() {
  const { id } = useParams();
  const [workout, setWorkout] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    const fetchWorkout = async () => {
      try {
        const res = await fetch(`http://127.0.0.1:8000/api/workouts/${id}/insights/`, {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.ok) {
          const data = await res.json();
          setWorkout(data);
        } else {
          console.error("Failed to fetch workout detail:", res.status);
        }
      } catch (err) {
        console.error("Error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkout();
  }, [id]);

  if (loading) return <p>Loading workout details...</p>;
  if (!workout) return <p>Workout not found</p>;

  return (
    <div>
      <h2>Workout Details</h2>
      <p>Date: {workout.date}</p>
      <p>Distance: {workout.distance_miles} miles</p>
      <p>Duration: {workout.duration_minutes} minutes</p>
      <p>Avg HR: {workout.avg_heart_rate}</p>
      <p>Avg Pace: {workout.avg_pace_min_per_mile}</p>

      <h3>AI Insights</h3>
      <pre style={{ whiteSpace: "pre-wrap" }}>{workout.insights}</pre>
    </div>
  );
}

export default WorkoutDetail;
