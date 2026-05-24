import React, { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";

import { useAuth } from "../context/AuthContext.jsx";
import supabase from "../lib/supabase.js";

function Login() {
  const navigate = useNavigate();
  const { loading: authLoading, session, user } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [githubLoading, setGithubLoading] = useState(false);
  const [error, setError] = useState("");

  if (authLoading) {
    return <div className="loading-state">Checking authentication...</div>;
  }

  if (session && user) {
    return <Navigate to="/dashboard" replace />;
  }

  async function handleGitHubLogin() {
    setGithubLoading(true);
    setError("");

    const { error: oauthError } = await supabase.auth.signInWithOAuth({
      provider: "github",
      options: {
        redirectTo: `${window.location.origin}/dashboard`,
      },
    });

    if (oauthError) {
      setError(oauthError.message || "GitHub login failed. Please try again.");
      setGithubLoading(false);
    }
  }

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
          <p>Sign in to monitor GitHub repositories for leaked secrets.</p>
        </div>

        {error && <div className="alert">{error}</div>}

        <div className="oauth-section">
          <button
            className="github-button"
            disabled={githubLoading || loading}
            onClick={handleGitHubLogin}
            type="button"
          >
            {githubLoading ? "Redirecting to GitHub..." : "Continue with GitHub"}
          </button>
        </div>

        <div className="auth-divider">
          <span>or</span>
        </div>

        <form className="auth-form" onSubmit={handleSubmit}>
          <label>
            Email
            <input
              autoComplete="email"
              disabled={loading || githubLoading}
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
              disabled={loading || githubLoading}
              onChange={(event) => setPassword(event.target.value)}
              required
              type="password"
              value={password}
            />
          </label>

          <button
            className="auth-button"
            disabled={loading || githubLoading}
            type="submit"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}

export default Login;
