import React, { useState } from "react";
import { api, User } from "../services/api";
import { ShieldCheck, UserCheck, PhoneCall, AlertCircle, ArrowRight, Database } from "lucide-react";

interface LoginScreenProps {
  onSuccess: (user: User) => void;
}

export const LoginScreen: React.FC<LoginScreenProps> = ({ onSuccess }) => {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleLogin = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!email || !password) {
      setError("Please provide both email and password");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const res = await api.login(email, password);
      api.setToken(res.access_token);
      onSuccess(res.user);
    } catch (err: any) {
      setError(err.message || "Invalid credentials");
    } finally {
      setLoading(false);
    }
  };

  const setPreset = (e: string, p: string) => {
    setEmail(e);
    setPassword(p);
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px 16px",
      background: "var(--bg-canvas)"
    }}>
      <div className="card" style={{
        width: "100%",
        maxWidth: "440px",
        padding: "36px 32px",
        boxShadow: "var(--shadow-lg)"
      }}>
        {/* Brand Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <img
            src="/jarvis-logo.png"
            alt="JARVIS CRM"
            style={{
              height: "56px",
              maxWidth: "240px",
              objectFit: "contain",
              margin: "0 auto 12px auto",
              display: "block",
              filter: "drop-shadow(0 4px 12px rgba(6, 182, 212, 0.2))"
            }}
          />
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "4px" }}>
            Lead Intelligence Radar & Controlled Outbound
          </p>
        </div>

        {error && (
          <div style={{
            marginBottom: "20px",
            padding: "12px",
            borderRadius: "8px",
            background: "var(--rose-light)",
            border: "1px solid var(--rose-border)",
            color: "var(--rose-dark)",
            fontSize: "0.8125rem",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <AlertCircle style={{ width: "16px", height: "16px", flexShrink: 0 }} />
            <span>{error}</span>
          </div>
        )}

        <form onSubmit={handleLogin} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "6px" }}>
              Email Address
            </label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@company.com"
              className="input-text"
              required
            />
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", textTransform: "uppercase", letterSpacing: "0.04em", marginBottom: "6px" }}>
              Password
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="input-text"
              required
            />
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary"
            style={{ width: "100%", padding: "10px", fontSize: "0.875rem", marginTop: "8px" }}
          >
            {loading ? "Signing in..." : "Sign In to Workspace"}
            <ArrowRight style={{ width: "16px", height: "16px" }} />
          </button>
        </form>

        {/* Quick Demo Accounts Selection */}
        <div style={{ marginTop: "28px", paddingTop: "20px", borderTop: "1px solid var(--border-subtle)" }}>
          <p style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.05em", textAlign: "center", marginBottom: "12px" }}>
            Quick Demo Login Presets
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            <button
              onClick={() => setPreset("superadmin@jarvis.local", "JarvisAdmin@2026")}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: "8px",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <ShieldCheck style={{ width: "18px", height: "18px", color: "var(--rose)" }} />
                <div>
                  <p style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>Super Admin (Platform)</p>
                  <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>superadmin@jarvis.local</p>
                </div>
              </div>
              <span style={{ fontSize: "0.6875rem", color: "var(--primary)", fontWeight: 700 }}>Autofill</span>
            </button>

            <button
              onClick={() => setPreset("dataentry@jarvis.local", "DataEntry@2026")}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: "8px",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease"
              }}
              id="preset-dataentry-btn"
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Database style={{ width: "18px", height: "18px", color: "var(--amber)" }} />
                <div>
                  <p style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>Data Entry (Supervised Ops)</p>
                  <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>dataentry@jarvis.local</p>
                </div>
              </div>
              <span style={{ fontSize: "0.6875rem", color: "var(--primary)", fontWeight: 700 }}>Autofill</span>
            </button>

            <button
              onClick={() => setPreset("admin@apex.com", "ApexAdmin@2026")}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: "8px",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <UserCheck style={{ width: "18px", height: "18px", color: "var(--primary)" }} />
                <div>
                  <p style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>CRM Admin (Apex Corp)</p>
                  <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>admin@apex.com</p>
                </div>
              </div>
              <span style={{ fontSize: "0.6875rem", color: "var(--primary)", fontWeight: 700 }}>Autofill</span>
            </button>

            <button
              onClick={() => setPreset("telecaller@apex.com", "Telecaller@2026")}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: "8px",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease"
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <PhoneCall style={{ width: "18px", height: "18px", color: "var(--emerald)" }} />
                <div>
                  <p style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>Telecaller (Masked Phone)</p>
                  <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>telecaller@apex.com</p>
                </div>
              </div>
              <span style={{ fontSize: "0.6875rem", color: "var(--primary)", fontWeight: 700 }}>Autofill</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
