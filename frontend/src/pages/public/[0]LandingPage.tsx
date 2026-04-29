import { Link } from "react-router-dom";
import "../../styles/public/[0]LandingPage.css";

export default function LandingPage() {
  return (
    <div className="landing-page">
      <nav className="sketch-nav">
        <Link to="/" className="brand">
          Journalise
        </Link>

        <div className="nav-buttons">
          <Link to="/login" className="sketch-btn small login-btn">
            Log In
          </Link>
          <Link to="/signup" className="sketch-btn small signup-btn">
            Sign Up
          </Link>
        </div>
      </nav>

      <main className="hero">
        <div className="doodle cat">🐱</div>
        <div className="doodle frog">🐸</div>
        <div className="doodle flower">✿</div>
        <div className="doodle paw">🐾</div>

        <p className="eyebrow">Time, made visible</p>

        <h1>
          A journal app that writes
          <br />
          your day for you!
        </h1>

        <p className="subtitle">
          Journalise observes the rhythm of your desktop activity and reshapes it into
          readable hourly entries, helping you understand how your time was truly spent.
        </p>

        <div className="hero-actions">
          <Link to="/signup" className="sketch-btn big signup-btn">
            New? Sign up today!
          </Link>
        </div>
      </main>
    </div>
  );
}