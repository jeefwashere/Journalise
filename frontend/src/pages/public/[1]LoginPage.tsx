import React, { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import api from "../../api/api";
import { loginWithGoogle, preloadGoogleAuth } from "../../api/googleAuth";
import "../../styles/public/login.css";

const Login: React.FC = () => {
  const navigate = useNavigate();

  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState({
    username: "",
    password: "",
    form: "",
  });
  const [formError, setFormError] = useState("");
  const [loading, setLoading] = useState(false);
  const [googleLoading, setGoogleLoading] = useState(false);

  useEffect(() => {
    preloadGoogleAuth().catch(() => undefined);
  }, []);

  const validate = () => {
    const newErrors = { username: "", password: "", form: "" };
    let valid = true;

    if (!username) {
      newErrors.username = "Username is required";
      valid = false;
    }

    if (!password) {
      newErrors.password = "Password is required";
      valid = false;
    }

    setErrors(newErrors);
    return valid;
  };

  const handleLogin = async () => {
    if (!validate()) {
      return;
    }

    setLoading(true);
    setFormError("");

    try {
      const response = await api.post("auth/login/", {
        username,
        password,
      });

      localStorage.setItem("accessToken", response.data.access_token);
      localStorage.setItem("currentUser", JSON.stringify(response.data.user));
      navigate("/dashboard");
    } catch (error: any) {
      setFormError(
        error.response?.data?.detail || "Could not log in. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    setGoogleLoading(true);
    setFormError("");

    try {
      await loginWithGoogle();
      navigate("/dashboard");
    } catch (error: any) {
      setFormError(
        error.response?.data?.detail ||
          error.response?.data?.code?.[0] ||
          error.message ||
          "Could not log in with Google. Please try again.",
      );
    } finally {
      setGoogleLoading(false);
    }
  };

  return (
    <div className="login-wrapper">
      <button className="back-button" onClick={() => navigate("/")}>
        ← Back
      </button>

      <section className="page page-sky">
        <div className="sky">
          {[
            { top: 10, duration: 70, delay: 10, scale: 1.1 },
            { top: 28, duration: 90, delay: 35, scale: 0.85 },
            { top: 50, duration: 60, delay: 55, scale: 1.3 },
            { top: 16, duration: 80, delay: 20, scale: 0.95 },
            { top: 65, duration: 100, delay: 45, scale: 1.0 },
          ].map((cloud, i) => (
            <div
              key={i}
              className="cloud"
              style={{
                top: `${cloud.top}%`,
                animationDuration: `${cloud.duration}s`,
                animationDelay: `-${cloud.delay}s`,
                transform: `scale(${cloud.scale})`,
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
          <div className="journal-content">
            <h1 className="title">Welcome Back!</h1>

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

              <label htmlFor="password">Password</label>
              <input
                id="password"
                type="password"
                value={password}
                placeholder="••••••••"
                onChange={(e) => setPassword(e.target.value)}
              />
              <span className="error">{errors.password}</span>
              <span className="error">{formError}</span>

              <button className="btn btn-login" onClick={handleLogin} disabled={loading}>
                {loading ? "Logging in..." : "Log In"}
              </button>
              <span className="error">{errors.form}</span>

              <div className="divider">
                <span>or</span>
              </div>

              <button
                className="btn btn-google"
                onClick={handleGoogleLogin}
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
                {googleLoading ? "Opening Google..." : "Log in with Google"}
              </button>

              <p className="login-link">
                No account? <a href="/signup">Sign up!</a>
              </p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};

export default Login;
