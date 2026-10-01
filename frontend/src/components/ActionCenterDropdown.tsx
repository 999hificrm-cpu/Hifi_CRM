import React, { useState, useEffect, useRef } from "react";
import { api, AdminAlert } from "../services/api";
import { Bell, AlertTriangle, CheckCircle, Info, X } from "lucide-react";

export const ActionCenterDropdown: React.FC = () => {
  const [alerts, setAlerts] = useState<AdminAlert[]>([]);
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    fetchAlerts();
    const interval = setInterval(fetchAlerts, 60000); // Poll every 60s
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const fetchAlerts = async () => {
    try {
      const res = await api.getAdminAlerts();
      setAlerts(res || []);
    } catch (e) {
      console.error("Failed to fetch alerts", e);
    }
  };

  const handleDismiss = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.dismissAdminAlert(id);
      setAlerts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      console.error("Failed to dismiss alert", err);
    }
  };

  const unreadCount = alerts.length;

  const getSeverityIcon = (severity: string) => {
    switch (severity) {
      case "CRITICAL": return <AlertTriangle style={{ width: "16px", height: "16px", color: "var(--danger)" }} />;
      case "WARNING": return <AlertTriangle style={{ width: "16px", height: "16px", color: "var(--warning)" }} />;
      case "INFO": return <Info style={{ width: "16px", height: "16px", color: "var(--primary)" }} />;
      default: return <Info style={{ width: "16px", height: "16px" }} />;
    }
  };

  return (
    <div style={{ position: "relative" }} ref={dropdownRef}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        style={{
          background: "transparent",
          border: "none",
          cursor: "pointer",
          position: "relative",
          padding: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          borderRadius: "50%",
          transition: "background 0.2s"
        }}
        onMouseEnter={(e) => e.currentTarget.style.background = "rgba(148, 163, 184, 0.1)"}
        onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
      >
        <Bell style={{ width: "20px", height: "20px", color: "var(--text-secondary)" }} />
        {unreadCount > 0 && (
          <span style={{
            position: "absolute",
            top: "4px",
            right: "4px",
            background: "var(--danger)",
            color: "white",
            fontSize: "0.6rem",
            fontWeight: 800,
            width: "16px",
            height: "16px",
            borderRadius: "50%",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            border: "2px solid var(--bg-panel)"
          }}>
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 8px)",
          right: 0,
          width: "360px",
          background: "var(--bg-panel)",
          border: "1px solid var(--border-color)",
          borderRadius: "12px",
          boxShadow: "0 10px 25px rgba(0,0,0,0.1)",
          zIndex: 50,
          overflow: "hidden",
          display: "flex",
          flexDirection: "column",
          maxHeight: "480px"
        }}>
          <div style={{ padding: "16px", borderBottom: "1px solid var(--border-color)", display: "flex", justifyContent: "space-between", alignItems: "center", background: "var(--bg-canvas)" }}>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 800, margin: 0, color: "var(--text-primary)" }}>Action Center</h3>
            {unreadCount > 0 && <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{unreadCount} new alerts</span>}
          </div>
          
          <div style={{ overflowY: "auto", flex: 1 }}>
            {alerts.length === 0 ? (
              <div style={{ padding: "32px", textAlign: "center", color: "var(--text-tertiary)" }}>
                <CheckCircle style={{ width: "32px", height: "32px", margin: "0 auto 8px auto", color: "var(--success)" }} />
                <p style={{ margin: 0, fontSize: "0.875rem" }}>You're all caught up!</p>
              </div>
            ) : (
              <div style={{ display: "flex", flexDirection: "column" }}>
                {alerts.map((alert) => (
                  <div key={alert.id} style={{
                    padding: "16px",
                    borderBottom: "1px solid var(--border-color)",
                    display: "flex",
                    gap: "12px",
                    background: alert.severity === "CRITICAL" ? "rgba(239, 68, 68, 0.03)" : "transparent",
                    transition: "background 0.2s"
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = "var(--bg-canvas)"}
                  onMouseLeave={(e) => e.currentTarget.style.background = alert.severity === "CRITICAL" ? "rgba(239, 68, 68, 0.03)" : "transparent"}
                  >
                    <div style={{ marginTop: "2px" }}>
                      {getSeverityIcon(alert.severity)}
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                        <h4 style={{ margin: "0 0 4px 0", fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>{alert.title}</h4>
                        <button 
                          onClick={(e) => handleDismiss(alert.id, e)}
                          style={{ background: "transparent", border: "none", cursor: "pointer", color: "var(--text-tertiary)", padding: "2px" }}
                          title="Dismiss"
                        >
                          <X style={{ width: "14px", height: "14px" }} />
                        </button>
                      </div>
                      <p style={{ margin: "0 0 8px 0", fontSize: "0.8125rem", color: "var(--text-secondary)", lineHeight: 1.4 }}>{alert.message}</p>
                      <span style={{ fontSize: "0.7rem", color: "var(--text-tertiary)" }}>
                        {new Date(alert.created_at).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
