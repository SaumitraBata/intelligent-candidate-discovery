// src/App.jsx
import { Routes, Route } from "react-router-dom";
import Header from "./components/Header";
import HomePage from "./pages/HomePage";
import ResultsPage from "./pages/ResultsPage";
import CandidateDetailPage from "./pages/CandidateDetailPage";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950">
      <Header />
      <Routes>
        <Route path="/"                    element={<HomePage />} />
        <Route path="/results"             element={<ResultsPage />} />
        <Route path="/candidate/:id"       element={<CandidateDetailPage />} />
      </Routes>
    </div>
  );
}