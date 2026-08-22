import { NavLink } from "react-router-dom";

export function NavBar({ user }: { user: string | null }) {
  return (
    <nav className="topnav">
      <NavLink to="/">Feed</NavLink>
      <NavLink to="/leaderboard">Leaderboard</NavLink>
      <NavLink to="/open-houses">Open Houses</NavLink>
      <NavLink to="/hidden">Hidden</NavLink>
      {user && <span className="whoami">{user[0].toUpperCase() + user.slice(1)}</span>}
    </nav>
  );
}
