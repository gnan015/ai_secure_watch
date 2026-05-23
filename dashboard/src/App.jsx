import React from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { useAuth } from "./context/AuthContext.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Detections from "./pages/Detections.jsx";
import DiscordSettings from "./pages/DiscordSettings.jsx";
import Login from "./pages/Login.jsx";
import Repositories from "./pages/Repositories.jsx";
import ScanEvents from "./pages/ScanEvents.jsx";

function RootRedirect() {
  const { loading, session, user } = useAuth();

  if (loading) {
    return <div className="loading-state">Checking authentication...</div>;
  }

  return session && user ? (
    <Navigate to="/dashboard" replace />
  ) : (
    <Navigate to="/login" replace />
  );
}

function App() {
  // TODO(V2): Add onboarding, repositories, integrations, and scoped V2
  // dashboard routes after the multi-user schema is ready.
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<RootRedirect />} />
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/repositories"
          element={
            <ProtectedRoute>
              <Repositories />
            </ProtectedRoute>
          }
        />
        <Route
          path="/integrations/discord"
          element={
            <ProtectedRoute>
              <DiscordSettings />
            </ProtectedRoute>
          }
        />
        <Route
          path="/scan-events"
          element={
            <ProtectedRoute>
              <ScanEvents />
            </ProtectedRoute>
          }
        />
        <Route
          path="/detections"
          element={
            <ProtectedRoute>
              <Detections />
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
