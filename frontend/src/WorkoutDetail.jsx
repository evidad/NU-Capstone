import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";

function WorkoutDetail() {
  const { id } = useParams();
  const [workout, setWorkout] = useState(null);
  const [insights, setInsights] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    const fetchWorkout = async () => {
      try {
        const res = await fetch(
          `http://127.0.0.1:8000/api/workouts/${id}/insights/`,
          {
            headers: { Authorization: `Bearer ${token}` },
          }
        );

        if (res.ok) {
          const data = await res.json();
          setWorkout(data.workout); // ✅ store nested workout object
          setInsights(data.insights); // ✅ store AI insights separately
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
      <p><strong>Date:</strong> {new Date(workout.date).toLocaleString()}</p>
      <p><strong>Distance:</strong> {workout.distance} miles</p>
      <p><strong>Duration:</strong> {workout.duration} minutes</p>
      <p><strong>Avg HR:</strong> {workout.avg_heart_rate}</p>
      <p><strong>Avg Pace:</strong> {workout.avg_pace} min/mi</p>

      <h3>AI Insights</h3>
      <pre style={{ whiteSpace: "pre-wrap" }}>{insights}</pre>
    </div>
  );
}

export default WorkoutDetail;
