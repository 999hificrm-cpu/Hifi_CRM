import React, { useState } from "react";
import { AlertTriangle, X, ShieldAlert, PauseCircle } from "lucide-react";
import { api } from "../../services/api";

interface SuspendOrgModalProps {
  organization: { id: string; name: string } | null;
  onClose: () => void;
  onSuspended: () => void;
}

export const SuspendOrgModal: React.FC<SuspendOrgModalProps> = ({
  organization,
  onClose,
  onSuspended,
}) => {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  if (!organization) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) {
      setError("A suspension reason is mandatory for compliance and auditing.");
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      const idempotencyKey = `suspend-org-${organization.id}-${Date.now()}`;
      await api.suspendOrganization(organization.id, reason.trim(), idempotencyKey);
      onSuspended();
      onClose();
    } catch (err: any) {
      setError(err.message || "Failed to suspend organization.");
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
          maxWidth: "500px",
          background: "var(--bg-surface)",
          borderRadius: "16px",
          boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.3)",
          overflow: "hidden",
          border: "1px solid var(--border-subtle)",
        }}
      >
        <div
          style={{
            padding: "20px 24px",
            borderBottom: "1px solid var(--border-subtle)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            background: "linear-gradient(90deg, rgba(239, 68, 68, 0.08) 0%, rgba(185, 28, 28, 0.02) 100%)",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "8px",
                background: "rgba(239, 68, 68, 0.15)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#dc2626",
              }}
            >
              <PauseCircle style={{ width: "20px", height: "20px" }} />
            </div>
            <div>
              <h3 style={{ fontSize: "1.0625rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Suspend Organization Workspace
              </h3>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                High-Risk Administrative Action
              </p>
            </div>
          </div>
          <button onClick={onClose} className="btn-secondary" style={{ padding: "6px", borderRadius: "8px" }}>
            <X style={{ width: "16px", height: "16px" }} />
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: "24px", display: "flex", flexDirection: "column", gap: "16px" }}>
          <div
            style={{
              padding: "12px 14px",
              borderRadius: "8px",
              background: "#fee2e2",
              border: "1px solid #fecaca",
              color: "#991b1b",
              fontSize: "0.75rem",
              display: "flex",
              alignItems: "flex-start",
              gap: "8px",
            }}
          >
            <AlertTriangle style={{ width: "16px", height: "16px", flexShrink: 0, marginTop: "2px" }} />
            <div>
              <strong>Immediate Access Lockdown:</strong> Suspending <strong>{organization.name}</strong> will instantly increment all tenant users' session versions, revoking all active JWTs immediately.
            </div>
          </div>

          <div>
            <label style={{ display: "block", fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
              Suspension Reason & Justification <span style={{ color: "#ef4444" }}>*</span>
            </label>
            <textarea
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="e.g. Delinquent account / Terms of service non-compliance / Payment dispute..."
              className="input-text"
              rows={3}
              required
              style={{ width: "100%", fontSize: "0.8125rem", resize: "vertical" }}
            />
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

          <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
            <button type="button" onClick={onClose} className="btn-secondary" style={{ padding: "8px 16px", fontSize: "0.8125rem" }}>
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !reason.trim()}
              className="btn-primary"
              style={{
                padding: "8px 20px",
                fontSize: "0.8125rem",
                background: "#dc2626",
                color: "#ffffff",
                border: "none",
              }}
            >
              {submitting ? "Locking down..." : "Confirm Suspension"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
