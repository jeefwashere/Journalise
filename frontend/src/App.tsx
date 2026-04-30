import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

import LandingPage from "./pages/public/[0]LandingPage";
import LoginPage from "./pages/public/[1]LoginPage";
import SignupPage from "./pages/public/SignUp1";

import StatsPage from "./pages/dashboard/[5]StatsPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        {/* Public pages */}
        <Route path="/" element={<LandingPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />

        {/* Dashboard pages */}
        <Route path="/dashboard" element={<StatsPage />} />
        <Route path="/stats" element={<StatsPage />} />

        {/* Coming soon pages */}
        <Route path="/journal" element={<StatsPage />} />
        <Route path="/pet-room" element={<StatsPage />} />
        <Route path="/account" element={<StatsPage />} />
        <Route path="/settings" element={<StatsPage />} />

        {/* Fallback */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
