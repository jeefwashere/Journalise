import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/public/[0]LandingPage";
import Signup from "./pages/SignUp1";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/signup" element={<Signup />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
