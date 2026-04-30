import { Link } from "react-router-dom";

export default function Sidebar() {
  return (
    <aside
      style={{
        width: "240px",
        background: "#111827",
        color: "white",
        padding: "20px",
      }}
    >
      <h1>Journalise</h1>

      <nav style={{ display: "grid", gap: "12px", marginTop: "30px" }}>
        <Link to="/">Dashboard</Link>
        <Link to="/journal">Journal</Link>
        <Link to="/stats">Stats</Link>
        <Link to="/settings">Settings</Link>
      </nav>
    </aside>
  );
}
