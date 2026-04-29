import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/public/[0]LandingPage";
import Signup from "./pages/public/SignUp1";
import Login from "./pages/public/[1]LoginPage";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<Signup />} />
        <Route path="/login" element={<Login />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
