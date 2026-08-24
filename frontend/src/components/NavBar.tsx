import { NavLink } from "react-router-dom";

export function NavBar({ user }: { user: string | null }) {
  return (
    <nav className="topnav">
      <NavLink to="/">Swipe</NavLink>
      <NavLink to="/inbox">Inbox</NavLink>
      <NavLink to="/leaderboard">Leaderboard</NavLink>
      <NavLink to="/open-houses">Open Houses</NavLink>
      <NavLink to="/passed">Passed</NavLink>
      <NavLink to="/needs-scan">Needs Scan</NavLink>
      {user && <span className="whoami">{user[0].toUpperCase() + user.slice(1)}</span>}
    </nav>
  );
}
