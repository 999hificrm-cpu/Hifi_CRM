import React, { useState } from "react";
import { LifeBuoy, X, ShieldAlert, Clock, AlertTriangle } from "lucide-react";
import { api, SupportSessionResponse } from "../../services/api";

interface SupportSessionModalProps {
  organization: { id: string; name: string } | null;
  onClose: () => void;
  onSessionCreated: (session: SupportSessionResponse, orgName: string) => void;
}

export const SupportSessionModal: React.FC<SupportSessionModalProps> = ({
  organization,
  onClose,
  onSessionCreated,
}) => {
  const [reason, setReason] = useState("");
  const [durationMinutes, setDurationMinutes] = useState(15);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!organization) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("Please provide an explicit technical justification reason for entering this tenant workspace.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const res = await api.createSupportSession({
        organization_id: organization.id,
        reason: reason.trim(),
        duration_minutes: durationMinutes,
      });

      // Save to localStorage
      localStorage.setItem(
        "jarvis_support_session",
        JSON.stringify({
          ...res,
          org_name: organization.name,
          reason: reason.trim(),
        })
      );

      onSessionCreated(res, organization.name);
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to initiate support session.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        backgroundColor: "rgba(15, 23, 42, 0.75)",
        backdropFilter: "blur(4px)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 1000,
        padding: "20px",
      }}
    >
      <div
        className="card"
        style={{
          width: "100%",
          maxWidth: "520px",
          background: "var(--bg-surface)",
          borderRadius: "16px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.3)",
          overflow: "hidden",
          border: "1px solid var(--border-subtle)",
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(90deg, rgba(245, 158, 11, 0.08) 0%, rgba(217, 119, 6, 0.02) 100%)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(245, 158, 11, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#d97706",
              }}
            >
              <LifeBuoy style={{ width: "20px", height: "20px" }} />
            </div>
            <div>
              <h3 style={{ fontSize: "1.0625rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Start Support Session
              </h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                Scoped Impersonation & Dual-Identity Context
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="btn-secondary"
            style={{ padding: "6px", borderRadius: "8px" }}
          >
            <X style={{ width: "16px", height: "16px" }} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
          {/* Target Org Info */}
          <div
            style={{
              padding: "12px 16px",
              borderRadius: "10px",
              background: "var(--bg-canvas)",
              border: "1px solid var(--border-subtle)",
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
            }}
          >
            <div>
              <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", textTransform: "uppercase", fontWeight: 700 }}>
                Target Organization
              </span>
              <p style={{ fontSize: "0.9375rem", fontWeight: 800, color: "var(--text-primary)" }}>
                {organization.name}
              </p>
            </div>
            <span style={{ fontSize: "0.6875rem", fontFamily: "monospace", color: "var(--text-muted)" }}>
              {organization.id.substring(0, 12)}...
            </span>
          </div>

          {/* Audit Notice */}
          <div
            style={{
              padding: "12px 14px",
              borderRadius: "8px",
              background: "#fffbeb",
              border: "1px solid #fef3c7",
              color: "#92400e",
              fontSize: "0.75rem",
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
            }}
          >
            <ShieldAlert style={{ width: "16px", height: "16px", flexShrink: 0, marginTop: "2px" }} />
            <div>
              <strong>Security Protocol Notice:</strong> A short-lived support token will be created. Every read and mutation will record your platform user identity alongside the tenant workspace in the cryptographic audit log.
            </div>
          </div>

          {/* Reason */}
          <div>
            <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
              Justification Reason <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Investigating CRM pipeline stage migration error reported by tenant admin..."
              className="input-text"
              rows={3}
              required
              style={{ width: "100%", fontSize: "0.8125rem", resize: "vertical" }}
            />
          </div>

          {/* Duration Selector */}
          <div>
            <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
              Session Duration
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "8px" }}>
              {[15, 30, 60].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDurationMinutes(d)}
                  style={{
                    padding: "8px 12px",
                    borderRadius: "8px",
                    border: durationMinutes === d ? "2px solid #f59e0b" : "1px solid var(--border-subtle)",
                    background: durationMinutes === d ? "rgba(245, 158, 11, 0.1)" : "var(--bg-canvas)",
                    color: durationMinutes === d ? "#b45309" : "var(--text-primary)",
                    fontWeight: 700,
                    fontSize: "0.8125rem",
                    cursor: "pointer",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "6px",
                  }}
                >
                  <Clock style={{ width: "13px", height: "13px" }} />
                  {d} Minutes
                </button>
              ))}
            </div>
          </div>

          {error && (
            <div
              style={{
                padding: "10px 14px",
                borderRadius: "8px",
                background: "#fee2e2",
                color: "#991b1b",
                fontSize: "0.75rem",
                display: "flex",
                alignItems: "center",
                gap: "8px",
              }}
            >
              <AlertTriangle style={{ width: "14px", height: "14px", flexShrink: 0 }} />
              <span>{error}</span>
            </div>
          )}

          {/* Actions */}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
            <button
              type="button"
              onClick={onClose}
              className="btn-secondary"
              style={{ padding: "8px 16px", fontSize: "0.8125rem" }}
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !reason.trim()}
              className="btn-primary"
              style={{
                padding: "8px 20px",
                fontSize: "0.8125rem",
                background: "#d97706",
                color: "#ffffff",
                border: "none",
              }}
            >
              {submitting ? "Initiating..." : "Start Audited Session"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
