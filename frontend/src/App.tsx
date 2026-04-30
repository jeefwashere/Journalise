import type { ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import LandingPage from "./pages/public/[0]LandingPage";
import LoginPage from "./pages/public/[1]LoginPage";
import SignupPage from "./pages/public/SignUp1";
import MainPage from "./pages/dashboard/MainPage";
import AccountPage from "./pages/dashboard/AccountPage";
import StatsPage from "./pages/dashboard/[5]StatsPage";
import JournalHistoryPage from "./pages/dashboard/JournalHistoryPage";
import { TrackingProvider } from "./contexts/TrackingContext";

function isAuthenticated() {
  return Boolean(
    localStorage.getItem("accessToken") ||
      localStorage.getItem("token") ||
      localStorage.getItem("journaliseIsAuthenticated") === "true",
  );
}

function ProtectedRoute({ children }: { children: ReactNode }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

function App() {
  return (
    <TrackingProvider>
      <BrowserRouter>
        <Routes>
          {/* Public pages */}
          <Route path="/" element={<LandingPage />} />
          <Route path="/login" element={<LoginPage />} />
          <Route path="/signup" element={<SignupPage />} />

          {/* Dashboard pages */}
          <Route
            path="/home"
            element={
              <ProtectedRoute>
                <MainPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <MainPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/stats"
            element={
              <ProtectedRoute>
                <StatsPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/account"
            element={
              <ProtectedRoute>
                <AccountPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/history"
            element={
              <ProtectedRoute>
                <JournalHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/journal-history"
            element={
              <ProtectedRoute>
                <JournalHistoryPage />
              </ProtectedRoute>
            }
          />
          <Route
            path="/journal"
            element={
              <ProtectedRoute>
                <JournalHistoryPage />
              </ProtectedRoute>
            }
          />
          {/* Fallback */}
          <Route path="*" element={<Navigate to="/login" replace />} />
        </Routes>
      </BrowserRouter>
    </TrackingProvider>
  );
}

export default App;
