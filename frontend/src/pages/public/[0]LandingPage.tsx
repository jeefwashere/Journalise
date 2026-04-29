import { Link } from "react-router-dom";
import "../../styles/public/[0]LandingPage.css";

export default function LandingPage() {
  return (
    <div className="landing-page">
      <nav className="landing-navbar">
        <div className="logo-box">Journalise</div>

        <div className="nav-actions">
          <Link to="/login" className="sketch-button">
            Log In
          </Link>
          <Link to="/signup" className="sketch-button filled">
            Sign Up
          </Link>
        </div>
      </nav>

      <main className="landing-content">
        <section className="hero-card">
          <p className="eyebrow">AI Desktop Journal</p>

          <h1>Welcome to Journalise</h1>

          <p className="hero-text">
            Journalise quietly tracks your desktop activity and turns your day
            into a clean, readable journal with hourly AI summaries.
          </p>

          <div className="hero-buttons">
            <Link to="/signup" className="sketch-button filled large">
              Start Journaling
            </Link>

            <a href="#explain" className="sketch-button large">
              Explain the App
            </a>
          </div>
        </section>

        <section id="explain" className="features-grid">
          <div className="feature-card">
            <h3>Hourly Summaries</h3>
            <p>See what you worked on each hour without writing anything.</p>
          </div>

          <div className="feature-card">
            <h3>AI Journal</h3>
            <p>Gemini turns your activity into natural journal entries.</p>
          </div>

          <div className="feature-card">
            <h3>Desktop Pet</h3>
            <p>
              Your pet grows as you stay focused and complete work sessions.
            </p>
          </div>
        </section>
      </main>

      <div className="doodle doodle-one">✦</div>
      <div className="doodle doodle-two">☁</div>
      <div className="doodle doodle-three">❀</div>
    </div>
  );
}
