import React, { useState } from "react";
import { useNavigate } from "react-router-dom";

import supabase from "../lib/supabase.js";

function Login() {
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event) {
    event.preventDefault();
    setLoading(true);
    setError("");

    const { error: loginError } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    setLoading(false);

    if (loginError) {
      setError(loginError.message || "Login failed. Please try again.");
      return;
    }

    navigate("/dashboard", { replace: true });
  }

  return (
    <main className="auth-page">
      <section className="auth-panel" aria-labelledby="login-title">
        <div className="auth-heading">
          <h1 id="login-title">AI SecureWatch</h1>
          <p>Sign in to continue monitoring repository security.</p>
        </div>

        {error && <div className="alert">{error}</div>}

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              disabled={loading}
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>

          <label>
            Password
            <input
              autoComplete="current-password"
              disabled={loading}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          <button className="auth-button" disabled={loading} type="submit">
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default Login;
