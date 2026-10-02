import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { apiErrorMessage } from "../api/client";
import { useAuth } from "../auth/AuthContext";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const from =
    (location.state as { from?: string } | null)?.from ?? "/dashboard";

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setSubmitting(true);
    setError(null);
    try {
      await login(username.trim(), password);
      navigate(from, { replace: true });
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="container container-narrow">
      <section className="card auth-card">
        <div className="card-body">
          <h1>Log in</h1>
          <p className="muted">Welcome back — pick up where you left off.</p>

          {error && (
            <div className="alert alert-error" role="alert">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            <div className="field">
              <label htmlFor="login-username">Username</label>
              <input
                id="login-username"
                type="text"
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoComplete="username"
                required
              />
            </div>
            <div className="field">
              <label htmlFor="login-password">Password</label>
              <input
                id="login-password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="current-password"
                required
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary btn-block"
              disabled={submitting}
            >
              {submitting ? "Logging in…" : "Log in"}
            </button>
          </form>

          <p className="auth-switch">
            New here? <Link to="/register">Create an account</Link>
          </p>
        </div>
      </section>
    </div>
  );
}
