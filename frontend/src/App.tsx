import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { api } from "./api";
import { NavBar } from "./components/NavBar";
import { Feed } from "./pages/Feed";
import { Hidden } from "./pages/Hidden";
import { Leaderboard } from "./pages/Leaderboard";
import { ListingDetail } from "./pages/ListingDetail";
import { OpenHouses } from "./pages/OpenHouses";
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
              <Route path="/" element={<Feed user={user} />} />
              <Route path="/listings/:id" element={<ListingDetail user={user} />} />
              <Route path="/hidden" element={<Hidden user={user} />} />
              <Route path="/open-houses" element={<OpenHouses user={user} />} />
              <Route path="/leaderboard" element={<Leaderboard user={user} />} />
            </>
          )}
        </Routes>
      </main>
    </BrowserRouter>
  );
}
