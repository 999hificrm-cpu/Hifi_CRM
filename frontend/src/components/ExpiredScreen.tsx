import React from "react";
import { AlertTriangle, Mail, Phone, LogOut } from "lucide-react";
import { api } from "../services/api";

export const ExpiredScreen: React.FC = () => {
  const handleLogout = () => {
    api.clearToken();
    window.location.href = "/login";
  };

  return (
    <div style={{
      minHeight: "100vh",
      background: "var(--bg-canvas)",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      padding: "24px"
    }}>
      <div className="card" style={{ maxWidth: "480px", width: "100%", textAlign: "center", padding: "48px 32px" }}>
        <div style={{
          width: "64px",
          height: "64px",
          borderRadius: "16px",
          background: "rgba(239, 68, 68, 0.1)",
          color: "var(--danger)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          margin: "0 auto 24px auto"
        }}>
          <AlertTriangle style={{ width: "32px", height: "32px" }} />
        </div>

        <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", marginBottom: "12px", letterSpacing: "-0.02em" }}>
          Subscription Expired
        </h2>
        
        <p style={{ fontSize: "0.9375rem", color: "var(--text-secondary)", lineHeight: 1.6, marginBottom: "32px" }}>
          Your 3-day trial or organization subscription has expired. You no longer have access to JARVIS CRM.
          Please contact support or your organization administrator to upgrade and restore your access.
        </p>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginBottom: "32px" }}>
          <a href="mailto:admin@jarviscrm.com" className="btn-primary" style={{ width: "100%", justifyContent: "center", padding: "12px", textDecoration: "none" }}>
            <Mail style={{ width: "18px", height: "18px" }} /> Email Support
          </a>
          <a href="tel:+919876543210" className="btn-secondary" style={{ width: "100%", justifyContent: "center", padding: "12px", textDecoration: "none" }}>
            <Phone style={{ width: "18px", height: "18px" }} /> Call +91 98765 43210
          </a>
        </div>

        <button onClick={handleLogout} style={{ background: "transparent", border: "none", color: "var(--text-secondary)", fontSize: "0.8125rem", cursor: "pointer", display: "inline-flex", alignItems: "center", gap: "6px", fontWeight: 600 }}>
          <LogOut style={{ width: "14px", height: "14px" }} /> Sign Out
        </button>
      </div>
    </div>
  );
};
