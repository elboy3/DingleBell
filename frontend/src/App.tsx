import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { NavBar } from "./components/NavBar";
import { Leaderboard } from "./pages/Leaderboard";
import { ListingDetail } from "./pages/ListingDetail";
import { Matches } from "./pages/Matches";
import { NeedsScan } from "./pages/NeedsScan";
import { Passed } from "./pages/Passed";
import { Swipe } from "./pages/Swipe";
import { WhoAmI } from "./pages/WhoAmI";

export default function App() {
  const [user, setUser] = useState<string | null | undefined>(undefined); // undefined = still loading

  useEffect(() => {
    api
      .whoami()
      .then((r) => setUser(r.user))
      .catch(() => setUser(null));
  }, []);

  if (user === undefined) return <p className="empty">Loading...</p>;

  return (
    <BrowserRouter>
      <NavBar user={user} />
      <main>
        <Routes>
          <Route path="/whoami" element={<WhoAmI onSet={setUser} />} />
          {!user ? (
            <Route path="*" element={<Navigate to="/whoami" replace />} />
          ) : (
            <>
              <Route path="/" element={<Swipe user={user} />} />
              <Route path="/matches" element={<Matches user={user} />} />
              <Route path="/listings/:id" element={<ListingDetail user={user} />} />
              <Route path="/passed" element={<Passed user={user} />} />
              <Route path="/leaderboard" element={<Leaderboard user={user} />} />
              <Route path="/needs-scan" element={<NeedsScan user={user} />} />
            </>
          )}
        </Routes>
      </main>
    </BrowserRouter>
  );
}
