import type { ReactNode } from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import LandingPage from "./pages/public/[0]LandingPage";
import LoginPage from "./pages/public/[1]LoginPage";
import SignupPage from "./pages/public/SignUp1";
import StatsPage from "./pages/dashboard/[5]StatsPage";
import JournalHistoryPage from "./pages/dashboard/JournalHistoryPage";
function App() {
  return (
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
              <StatsPage />
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

        <Route path="/history" element={<JournalHistoryPage />} />
        <Route path="/journal-history" element={<JournalHistoryPage />} />
        <Route path="/journal" element={<JournalHistoryPage />} />
        {/* Fallback */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
