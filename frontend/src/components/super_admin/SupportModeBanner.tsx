import React, { useState, useEffect } from "react";
import { LifeBuoy, XCircle, Clock, ShieldAlert } from "lucide-react";
import { api, SupportSessionResponse } from "../../services/api";

interface SupportModeBannerProps {
  session: SupportSessionResponse | null;
  orgName?: string;
  onSessionEnded: () => void;
}

export const SupportModeBanner: React.FC<SupportModeBannerProps> = ({
  session,
  orgName,
  onSessionEnded,
}) => {
  const [timeLeft, setTimeLeft] = useState<string>("");
  const [isExpired, setIsExpired] = useState(false);
  const [ending, setEnding] = useState(false);

  useEffect(() => {
    if (!session?.expires_at) return;

    const updateTimer = () => {
      const expiry = new Date(session.expires_at).getTime();
      const now = new Date().getTime();
      const diff = expiry - now;

      if (diff <= 0) {
        setTimeLeft("00:00 (Expired)");
        setIsExpired(true);
      } else {
        const minutes = Math.floor(diff / (1000 * 60));
        const seconds = Math.floor((diff % (1000 * 60)) / 1000);
        setTimeLeft(`${minutes.toString().padStart(2, "0")}:${seconds.toString().padStart(2, "0")}`);
      }
    };

    updateTimer();
    const interval = setInterval(updateTimer, 1000);
    return () => clearInterval(interval);
  }, [session]);

  if (!session) return null;

  const handleEndSession = async () => {
    setEnding(true);
    try {
      await api.revokeSupportSession(session.support_session_id, "Platform operator concluded support session");
    } catch (e) {
      console.warn("Notice terminating support session:", e);
    } finally {
      localStorage.removeItem("jarvis_support_session");
      onSessionEnded();
      setEnding(false);
    }
  };

  return (
    <div
      style={{
        background: "linear-gradient(90deg, #92400e 0%, #78350f 100%)",
        color: "#fef3c7",
        padding: "12px 20px",
        borderRadius: "10px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        border: "1px solid #f59e0b",
        boxShadow: "0 4px 16px rgba(245, 158, 11, 0.25)",
        marginBottom: "16px",
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: "rgba(254, 243, 199, 0.15)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <LifeBuoy style={{ width: "18px", height: "18px", color: "#fef08a" }} />
        </div>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <span style={{ fontWeight: 800, fontSize: "0.875rem", letterSpacing: "0.02em" }}>
              ACTIVE SUPPORT SESSION
            </span>
            <span
              style={{
                fontSize: "0.6875rem",
                fontWeight: 700,
                padding: "2px 8px",
                borderRadius: "4px",
                background: "#fef3c7",
                color: "#78350f",
              }}
            >
              DUAL-IDENTITY AUDITED
            </span>
          </div>
          <p style={{ fontSize: "0.75rem", color: "#fef3c7", opacity: 0.9, marginTop: "2px" }}>
            Viewing tenant context for <strong>{orgName || session.organization_id}</strong>. All mutations are tagged with support context and session ID.
          </p>
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "rgba(0,0,0,0.3)",
            padding: "6px 12px",
            borderRadius: "6px",
            fontSize: "0.8125rem",
            fontFamily: "monospace",
            fontWeight: 700,
            color: isExpired ? "#fca5a5" : "#fef08a",
          }}
        >
          <Clock style={{ width: "14px", height: "14px" }} />
          <span>{timeLeft || "15:00"}</span>
        </div>

        <button
          onClick={handleEndSession}
          disabled={ending}
          className="btn-secondary"
          style={{
            background: "#fef3c7",
            color: "#78350f",
            fontWeight: 800,
            fontSize: "0.75rem",
            padding: "8px 14px",
            border: "none",
            display: "flex",
            alignItems: "center",
            gap: "6px",
            cursor: "pointer",
          }}
        >
          <XCircle style={{ width: "14px", height: "14px" }} />
          {ending ? "Ending..." : "End Support Mode"}
        </button>
      </div>
    </div>
  );
};
