import React from "react";
import { Navigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";

function ProtectedRoute({ children }) {
  const { loading, session, user } = useAuth();

  if (loading) {
    return <div className="loading-state">Checking authentication...</div>;
  }

  if (!session || !user) {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default ProtectedRoute;
