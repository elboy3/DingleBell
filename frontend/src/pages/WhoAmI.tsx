import { useNavigate } from "react-router-dom";
import { api } from "../api";

export function WhoAmI({ onSet }: { onSet: (u: string) => void }) {
  const navigate = useNavigate();

  const pick = async (user: string) => {
    await api.setWhoami(user);
    onSet(user);
    navigate("/");
  };

  return (
    <div className="whoami-page">
      <h1>Who's this?</h1>
      <div className="whoami-buttons">
        <button className="whoami-button" onClick={() => pick("elliott")}>
          I'm Elliott
        </button>
        <button className="whoami-button" onClick={() => pick("madison")}>
          I'm Madison
        </button>
      </div>
    </div>
  );
}
