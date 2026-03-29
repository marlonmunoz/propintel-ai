import { Routes, Route } from "react-router-dom";
import Home from "./pages/Home";
import Analyze from "./pages/Analyze";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/analyze" element={<Analyze />} />
    </Routes>
  )
}