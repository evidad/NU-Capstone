import { useState } from "react";
import Login from "./Login";
import Workouts from "./Workouts";

function App() {
  const [auth, setAuth] = useState(!!localStorage.getItem("access"));

  return (
    <div>
      {auth ? <Workouts /> : <Login setAuth={setAuth} />}
    </div>
  );
}

export default App;
