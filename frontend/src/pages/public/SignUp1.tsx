import React, { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import "../../styles/public/signup.css";
import placeholder from "../../assets/placeholder.jpg";

type CloudConfig = {
  top: number;
  duration: number;
  delay: number;
  scale?: number;
};

type Pet = {
  id: string;
  label: string;
  image?: string;
};

const PETS: Pet[] = [
  { id: "pet1", label: "Pet 1" },
  { id: "pet2", label: "Pet 2" },
  { id: "pet3", label: "Pet 3" },
  { id: "pet4", label: "Pet 4" },
];

const Signup: React.FC = () => {
  const navigate = useNavigate();

  const [canScroll, setCanScroll] = useState(false);
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({
    username: "",
    email: "",
    password: "",
  });

  const [selectedPet, setSelectedPet] = useState<string | null>(null);
  const [petName, setPetName] = useState("");
  const [petNameError, setPetNameError] = useState("");

  const secondPageRef = useRef<HTMLDivElement>(null);

  const validate = () => {
    const newErrors = { username: "", email: "", password: "" };
    let valid = true;
    if (!username) {
      newErrors.username = "Username is required";
      valid = false;
    }
    if (!email) {
      newErrors.email = "Email is required";
      valid = false;
    }
    if (!password) {
      newErrors.password = "Password is required";
      valid = false;
    }
    setErrors(newErrors);
    return valid;
  };

  const smoothScrollTo = (targetY: number, duration: number) => {
    const startY = window.scrollY;
    const distance = targetY - startY;
    let startTime: number | null = null;

    const easeInOut = (t: number) =>
      t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;

    const animation = (currentTime: number) => {
      if (!startTime) startTime = currentTime;
      const time = currentTime - startTime;
      const progress = Math.min(time / duration, 1);

      window.scrollTo(0, startY + distance * easeInOut(progress));

      if (time < duration) {
        requestAnimationFrame(animation);
      }
    };

    requestAnimationFrame(animation);
  };

  const handleSignup = () => {
    if (validate()) {
      setCanScroll(true);

      const targetY = secondPageRef.current?.offsetTop || 0;

      smoothScrollTo(targetY, 2000);
    }
  };

  const handleLetsGo = () => {
    if (!petName.trim()) {
      setPetNameError("Please give your pet a name!");
      return;
    }
    setPetNameError("");
    console.log("All done!", { username, email, selectedPet, petName });
  };

  const clouds: CloudConfig[] = [
    { top: 10, duration: 70, delay: 10, scale: 1.1 },
    { top: 28, duration: 90, delay: 35, scale: 0.85 },
    { top: 50, duration: 60, delay: 55, scale: 1.3 },
    { top: 16, duration: 80, delay: 20, scale: 0.95 },
    { top: 65, duration: 100, delay: 45, scale: 1.0 },
  ];

  return (
    <div className={`signup-wrapper ${!canScroll ? "no-scroll" : ""}`}>
      <button className="back-button" onClick={() => navigate("/")}>
        ← Back
      </button>

      {/* ── PAGE 1: SKY + FORM ── */}
      <section className="page page-sky">
        <div className="sky">
          {clouds.map((cloud, i) => (
            <div
              key={i}
              className="cloud"
              style={{
                top: `${cloud.top}%`,
                animationDuration: `${cloud.duration}s`,
                animationDelay: `-${cloud.delay}s`,
                transform: `scale(${cloud.scale ?? 1})`,
              }}
            >
              <div className="cloud-body" />
              <div className="cloud-bump cloud-bump--sm" />
              <div className="cloud-bump cloud-bump--lg" />
              <div className="cloud-bump cloud-bump--md" />
            </div>
          ))}
        </div>

        <div className="journal">
          <div className="journal-margin" />
          <div className="journal-lines">
            {Array.from({ length: 18 }).map((_, i) => (
              <div key={i} className="journal-rule" />
            ))}
          </div>

          <div className="journal-content">
            <h1 className="title">Welcome!</h1>

            <div className="form">
              <label htmlFor="username">Username</label>
              <input
                id="username"
                type="text"
                value={username}
                placeholder="your_name"
                onChange={(e) => setUsername(e.target.value)}
              />
              <span className="error">{errors.username}</span>

              <label htmlFor="email">Email</label>
              <input
                id="email"
                type="email"
                value={email}
                placeholder="you@example.com"
                onChange={(e) => setEmail(e.target.value)}
              />
              <span className="error">{errors.email}</span>

              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                placeholder="••••••••"
                onChange={(e) => setPassword(e.target.value)}
              />
              <span className="error">{errors.password}</span>

              <button className="btn btn-signup" onClick={handleSignup}>
                Sign Up!
              </button>

              <div className="divider">
                <span>or</span>
              </div>

              <button className="btn btn-google">
                <svg
                  className="google-icon"
                  viewBox="0 0 18 18"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M17.64 9.2c0-.637-.057-1.251-.164-1.84H9v3.481h4.844a4.14 4.14 0 0 1-1.796 2.716v2.259h2.908c1.702-1.567 2.684-3.875 2.684-6.615Z"
                    fill="#4285F4"
                  />
                  <path
                    d="M9 18c2.43 0 4.467-.806 5.956-2.18l-2.908-2.259c-.806.54-1.837.86-3.048.86-2.344 0-4.328-1.584-5.036-3.711H.957v2.332A8.997 8.997 0 0 0 9 18Z"
                    fill="#34A853"
                  />
                  <path
                    d="M3.964 10.71A5.41 5.41 0 0 1 3.682 9c0-.593.102-1.17.282-1.71V4.958H.957A8.996 8.996 0 0 0 0 9c0 1.452.348 2.827.957 4.042l3.007-2.332Z"
                    fill="#FBBC05"
                  />
                  <path
                    d="M9 3.58c1.321 0 2.508.454 3.44 1.345l2.582-2.58C13.463.891 11.426 0 9 0A8.997 8.997 0 0 0 .957 4.958L3.964 7.29C4.672 5.163 6.656 3.58 9 3.58Z"
                    fill="#EA4335"
                  />
                </svg>
                Sign up with Google
              </button>

              <p className="login-link">
                Already have an account? <a href="/login">Log in</a>
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ── PAGE 2: GRASSY HILL + PET PICKER ── */}
      <section className="page page-grass" ref={secondPageRef}>
        <div className="sky-peek" />

        <div className="hills">
          <div className="hill hill--back"></div>
          <div className="hill hill--front"></div>
        </div>

        <div className="grass-content">
          <div className="hill-card">
            <h2 className="hill-title">PICK YOUR PET!</h2>
            <p className="hill-subtitle">
              Your pet will be your companion on this journaling journey - they
              grow as your garden of productivity grows!
            </p>
            <p className="hill-subtitle">
              Pick carefully - you can't change this later!
            </p>
          </div>

          <div className="pet-row">
            {PETS.map((pet) => (
              <button
                key={pet.id}
                className={`pet-btn ${selectedPet === pet.id ? "pet-btn--selected" : ""}`}
                onClick={() => {
                  setSelectedPet(pet.id);
                  setPetName("");
                  setPetNameError("");
                }}
              >
                <img src={placeholder} alt={pet.label} className="pet-img" />
              </button>
            ))}
          </div>

          {selectedPet && (
            <div className="pet-name-section">
              <label className="pet-name-label">
                What would you like to name your pet?
              </label>

              <input
                type="text"
                value={petName}
                onChange={(e) => setPetName(e.target.value)}
                placeholder="Give them a name..."
              />

              {petNameError && <span className="error">{petNameError}</span>}

              <button
                className="btn btn-letsgo"
                disabled={!petName.trim()}
                onClick={handleLetsGo}
              >
                Next →
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default Signup;