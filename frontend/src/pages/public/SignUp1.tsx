import React, { useEffect, useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/api";
import { loginWithGoogle, preloadGoogleAuth } from "../../api/googleAuth";
import "../../styles/public/signup.css";

import pet1Default from "../../assets/Dogs/000.png";
import pet1Selected from "../../assets/Dogs/002.png";

import pet2Default from "../../assets/Cats/100.png";
import pet2Selected from "../../assets/Cats/102.png";

import pet3Default from "../../assets/Bunny/200.png";
import pet3Selected from "../../assets/Bunny/202.png";

type CloudConfig = {
  top: number;
  duration: number;
  delay: number;
  scale?: number;
};

type Pet = {
  id: string;
  label: string;
  petType: string;
  petTypeIndex: number;
  defaultImg: string;
  selectedImg: string;
};

type SignupUser = {
  username?: string;
  email?: string;
};

const PETS: Pet[] = [
  { id: "pet1", label: "Dog", petType: "dog", petTypeIndex: 0, defaultImg: pet1Default, selectedImg: pet1Selected },
  { id: "pet2", label: "Cat", petType: "cat", petTypeIndex: 1, defaultImg: pet2Default, selectedImg: pet2Selected },
  { id: "pet3", label: "Bunny", petType: "frog", petTypeIndex: 2, defaultImg: pet3Default, selectedImg: pet3Selected },
];
const HOME_STATE_KEY = "journaliseHomeState";

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
    form: "",
  });
  const [selectedPet, setSelectedPet] = useState<string | null>(null);
  const [petName, setPetName] = useState("");
  const [petNameError, setPetNameError] = useState("");
  const [signupError, setSignupError] = useState("");
  const [petSetupError, setPetSetupError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);
  const [googleSignupUser, setGoogleSignupUser] = useState<SignupUser | null>(null);

  const secondPageRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    preloadGoogleAuth().catch(() => undefined);
  }, []);

  const validate = () => {
    const newErrors = { username: "", email: "", password: "", form: "" };
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
    setSignupError("");
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
      setGoogleSignupUser(null);
      setCanScroll(true);

      const targetY = secondPageRef.current?.offsetTop || 0;

      smoothScrollTo(targetY, 2000);
    }
  };

  const handleLetsGo = async () => {
    if (!petName.trim()) {
      setPetNameError("Please give your pet a name!");
      return;
    }

    setPetNameError("");
    setPetSetupError("");
    setSignupError("");
    setLoading(true);

    try {
      const chosenPet = PETS.find((pet) => pet.id === selectedPet);

      if (!chosenPet) {
        setPetNameError("Please pick a pet!");
        return;
      }

      let activeUser = googleSignupUser;

      if (!activeUser) {
        const response = await api.post("auth/register/", {
          username,
          email,
          password,
        });

        activeUser = response.data.user;
        localStorage.setItem("accessToken", response.data.access_token);
        localStorage.setItem("currentUser", JSON.stringify(response.data.user));
      }

      const petsResponse = await api.get("pets/");
      const backendPet = petsResponse.data.find(
        (pet: { id: number; pet_type: string; level: number; mood?: string }) =>
          pet.pet_type === chosenPet.petType &&
          pet.level === 1 &&
          (pet.mood || "neutral") === "neutral"
      );

      if (!backendPet) {
        throw new Error("Could not find the selected pet. Please try again.");
      }

      const userResponse = await api.patch("auth/me/", {
        profile: {
          pet_name: petName.trim(),
          current_pet_id: backendPet.id,
        },
      });
      const updatedUser = userResponse.data;

      localStorage.setItem("currentUser", JSON.stringify(updatedUser));
      localStorage.setItem(
        HOME_STATE_KEY,
        JSON.stringify({
          username: updatedUser.username || activeUser?.username || username,
          email: updatedUser.email || activeUser?.email || email,
          petName: petName.trim(),
          petType: chosenPet.petTypeIndex,
          petLevel: Number(backendPet.level || 1),
        }),
      );

      navigate("/dashboard");
    } catch (error: any) {
      const data = error.response?.data;
      const accountErrors = {
        username: data?.username?.[0] || "",
        email: data?.email?.[0] || "",
        password: data?.password?.[0] || "",
        form: data?.detail || "",
      };
      const hasAccountError =
        accountErrors.username ||
        accountErrors.email ||
        accountErrors.password ||
        accountErrors.form;

      if (hasAccountError && !googleSignupUser) {
        setErrors(accountErrors);
        setSignupError(
          accountErrors.form ||
            "Please fix the highlighted signup fields and try again."
        );
        smoothScrollTo(0, 800);
      } else {
        setPetSetupError(
          data?.detail ||
            error.message ||
            "Could not save your pet. Please try again."
        );
      }
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleSignup = async () => {
    setGoogleLoading(true);
    setSignupError("");
    setPetSetupError("");
    setErrors({ username: "", email: "", password: "", form: "" });

    try {
      const response = await loginWithGoogle();
      const user = response.user || null;

      setGoogleSignupUser(user);
      setCanScroll(true);

      if (user?.username) {
        setUsername(user.username);
      }

      if (user?.email) {
        setEmail(user.email);
      }

      requestAnimationFrame(() => {
        const targetY = secondPageRef.current?.offsetTop || 0;
        smoothScrollTo(targetY, 2000);
      });
    } catch (error: any) {
      setSignupError(
        error.response?.data?.detail ||
          error.response?.data?.code?.[0] ||
          error.message ||
          "Could not sign up with Google. Please try again.",
      );
    } finally {
      setGoogleLoading(false);
    }
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

              <button
                className="btn btn-google"
                onClick={handleGoogleSignup}
                disabled={loading || googleLoading}
              >
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
                {googleLoading ? "Opening Google..." : "Sign up with Google"}
              </button>
              <span className="error">{signupError}</span>

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
                  if (selectedPet === pet.id) {
                    setSelectedPet(null); // deselect
                    setPetName("");
                    setPetNameError("");
                    setPetSetupError("");
                  } else {
                    setSelectedPet(pet.id); // select
                    setPetName("");
                    setPetNameError("");
                    setPetSetupError("");
                  }
                }}
              >
                <img
                  src={
                    selectedPet === pet.id ? pet.selectedImg : pet.defaultImg
                  }
                  alt={pet.label}
                  className="pet-img"
                />
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
              {petSetupError && <span className="error">{petSetupError}</span>}

              <button
                className="btn btn-letsgo"
                disabled={!petName.trim() || loading}
                onClick={handleLetsGo}
              >
                {loading ? "Creating..." : "Next →"}
              </button>
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

export default Signup;
