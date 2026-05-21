import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import Dashboard from "./pages/Dashboard.jsx";
import Login from "./pages/Login.jsx";

function App() {
  // TODO(V2): Add Supabase Auth session handling and route users through
  // login, onboarding, repositories, integrations, and the scoped dashboard.
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
