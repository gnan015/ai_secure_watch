import React, { useState } from "react";
import { NavLink, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";

const navItems = [
  { label: "Dashboard", path: "/dashboard" },
  { label: "Repositories", path: "/repositories" },
  { label: "Discord", path: "/integrations/discord" },
  { label: "Scan Events", path: "/scan-events" },
  { label: "Detections", path: "/detections" },
];

function AppShell({ title, description, actions, children }) {
  const navigate = useNavigate();
  const { signOut, user } = useAuth();
  const [signingOut, setSigningOut] = useState(false);

  async function handleSignOut() {
    setSigningOut(true);
    const { error } = await signOut();
    if (error) {
      setSigningOut(false);
      return;
    }
    navigate("/login", { replace: true });
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">AS</span>
          <div>
            <strong>AI SecureWatch</strong>
            <span>V2 security</span>
          </div>
        </div>

        <nav className="sidebar-nav" aria-label="Primary navigation">
          {navItems.map((item) => (
            <NavLink
              className={({ isActive }) =>
                isActive ? "sidebar-link active" : "sidebar-link"
              }
              key={item.path}
              to={item.path}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="user-email">{user?.email || "Authenticated"}</span>
          <button
            className="button button-secondary full-width"
            disabled={signingOut}
            onClick={handleSignOut}
            type="button"
          >
            {signingOut ? "Signing out..." : "Sign out"}
          </button>
        </div>
      </aside>

      <main className="main-content">
        <header className="page-header">
          <div>
            <h1>{title}</h1>
            {description && <p>{description}</p>}
          </div>
          {actions && <div className="page-actions">{actions}</div>}
        </header>

        {children}
      </main>
    </div>
  );
}

export default AppShell;
