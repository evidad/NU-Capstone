import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

function Workouts() {
  const [workouts, setWorkouts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("access");
    if (!token) {
      window.location.href = "/login";
      return;
    }

    const fetchWorkouts = async () => {
      try {
        const res = await fetch("http://127.0.0.1:8000/api/workouts/", {
          headers: { Authorization: `Bearer ${token}` },
        });

        if (res.ok) {
          const data = await res.json();
          setWorkouts(data);
        } else {
          console.error("Fetch failed:", res.status);
        }
      } catch (err) {
        console.error("Error:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchWorkouts();
  }, []);

  if (loading) return <p>Loading workouts...</p>;

  return (
    <div>
      <h2>Your Workouts</h2>
      {workouts.length === 0 ? (
        <p>No workouts found.</p>
      ) : (
        <ul>
          {workouts.map((w) => (
            <li key={w.id}>
              {w.date} - {w.distance_miles} miles{" "}
              <Link to={`/workouts/${w.id}`}>View</Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

export default Workouts;
