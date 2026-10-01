import React, { useState, useEffect } from "react";
import { api, RadarOverview, Task, Lead } from "../services/api";
import { 
  Sparkles, 
  Flame, 
  AlertTriangle, 
  Clock, 
  TrendingUp, 
  ShieldCheck, 
  ArrowRight,
  PhoneCall
} from "lucide-react";

interface RadarViewProps {
  onSelectLead: (lead: Lead) => void;
}

export const RadarView: React.FC<RadarViewProps> = ({ onSelectLead }) => {
  const [radar, setRadar] = useState<RadarOverview | null>(null);
  const [overdueTasks, setOverdueTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadRadar();
  }, []);

  const loadRadar = async () => {
    setLoading(true);
    try {
      const [rData, tData] = await Promise.all([
        api.getRadarOverview(),
        api.getTasks({ status_filter: "PENDING" }),
      ]);
      setRadar(rData);
      setOverdueTasks(tData.filter((t) => t.due_at && new Date(t.due_at) < new Date()));
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleLeadClick = async (leadId: string) => {
    try {
      const lead = await api.getLeadDetail(leadId);
      onSelectLead(lead);
    } catch (e: any) {
      alert(e.message);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "64px 0", textAlign: "center", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
        Initializing JARVIS Lead Intelligence Radar...
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
      {/* Header Banner */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
            <span className="radar-pulse-dot" />
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--primary)", letterSpacing: "0.04em", textTransform: "uppercase" }}>
              Autonomous Radar Active
            </span>
          </div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            Executive Intelligence Radar
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Opportunity radar, bottleneck detection, and telemetry
          </p>
        </div>
      </div>

      {/* KPI Stats Grid */}
      <div className="grid-cols-kpi">
        <div className="stat-card stat-card-accent-emerald">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Active Pipeline Value</span>
            <div style={{ padding: "6px", borderRadius: "8px", background: "var(--emerald-light)", color: "var(--emerald)" }}>
              <TrendingUp style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <p style={{ fontSize: "1.625rem", fontWeight: 800, color: "var(--text-primary)", fontFamily: "monospace", letterSpacing: "-0.02em" }}>
            ₹{Number(radar?.total_active_pipeline_value || 0).toLocaleString("en-IN")}
          </p>
          <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--emerald-dark)", marginTop: "6px", display: "block" }}>
            In qualified sales pipeline
          </span>
        </div>

        <div className="stat-card stat-card-accent-amber">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>High-Value Deals</span>
            <div style={{ padding: "6px", borderRadius: "8px", background: "var(--amber-light)", color: "var(--amber)" }}>
              <Flame style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <p style={{ fontSize: "1.625rem", fontWeight: 800, color: "var(--amber-dark)", fontFamily: "monospace", letterSpacing: "-0.02em" }}>
            {radar?.high_value_opportunities.length || 0}
          </p>
          <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", marginTop: "6px", display: "block" }}>
            Radar score ≥ 70
          </span>
        </div>

        <div className="stat-card stat-card-accent-rose">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Overdue Follow-ups</span>
            <div style={{ padding: "6px", borderRadius: "8px", background: "var(--rose-light)", color: "var(--rose)" }}>
              <AlertTriangle style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <p style={{ fontSize: "1.625rem", fontWeight: 800, color: "var(--rose-dark)", fontFamily: "monospace", letterSpacing: "-0.02em" }}>
            {radar?.overdue_followups_count || 0}
          </p>
          <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--rose-dark)", marginTop: "6px", display: "block" }}>
            Requires immediate outreach
          </span>
        </div>

        <div className="stat-card stat-card-accent-indigo">
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Today's Activities</span>
            <div style={{ padding: "6px", borderRadius: "8px", background: "var(--primary-light)", color: "var(--primary)" }}>
              <Clock style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <p style={{ fontSize: "1.625rem", fontWeight: 800, color: "var(--primary)", fontFamily: "monospace", letterSpacing: "-0.02em" }}>
            {radar?.radar_activity_today || 0}
          </p>
          <span style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--text-muted)", marginTop: "6px", display: "block" }}>
            Calls, messages & notes logged
          </span>
        </div>
      </div>

      {/* Main Two Column Insights Layout */}
      <div className="grid-cols-radar">
        {/* Left Column: Prioritized Opportunity Feed */}
        <div className="card" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: "14px", borderBottom: "1px solid var(--border-subtle)", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "0.9375rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
              <Sparkles style={{ width: "18px", height: "18px", color: "var(--amber)" }} />
              Prioritized Opportunity Feed
            </h3>
            <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 600 }}>
              Sorted by Conversion Probability
            </span>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
            {radar?.high_value_opportunities.length === 0 ? (
              <p style={{ textAlign: "center", padding: "32px 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
                No high-value opportunities detected in pipeline.
              </p>
            ) : (
              radar?.high_value_opportunities.map((opp) => (
                <div
                  key={opp.lead_id}
                  onClick={() => handleLeadClick(opp.lead_id)}
                  style={{
                    padding: "16px",
                    borderRadius: "10px",
                    border: "1px solid var(--border-subtle)",
                    background: "var(--bg-surface)",
                    boxShadow: "var(--shadow-xs)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    borderLeft: opp.urgency === "HIGH" ? "4px solid var(--rose)" : "4px solid var(--amber)"
                  }}
                  onMouseOver={(e) => {
                    e.currentTarget.style.boxShadow = "var(--shadow-md)";
                    e.currentTarget.style.borderColor = "var(--primary-border)";
                  }}
                  onMouseOut={(e) => {
                    e.currentTarget.style.boxShadow = "var(--shadow-xs)";
                    e.currentTarget.style.borderColor = "var(--border-subtle)";
                    if (opp.urgency === "HIGH") {
                      e.currentTarget.style.borderLeft = "4px solid var(--rose)";
                    } else {
                      e.currentTarget.style.borderLeft = "4px solid var(--amber)";
                    }
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "12px" }}>
                    <div>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <span className={`badge ${opp.urgency === "HIGH" ? "badge-hot" : "badge-high"}`}>
                          {opp.urgency} URGENCY
                        </span>
                        <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)" }}>
                          {opp.company_name || "Account"}
                        </span>
                      </div>
                      <h4 style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>
                        {opp.title}
                      </h4>
                      <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px", lineHeight: "1.4" }}>
                        {opp.reason}
                      </p>
                    </div>

                    <div style={{ textAlign: "right", flexShrink: 0 }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "4px", fontSize: "1.125rem", fontWeight: 800, fontFamily: "monospace", color: "var(--amber-dark)" }}>
                        <Flame style={{ width: "16px", height: "16px", color: "var(--amber)" }} />
                        {opp.score}
                      </div>
                      <span style={{ fontSize: "0.625rem", fontWeight: 600, color: "var(--text-muted)" }}>Radar Score</span>
                    </div>
                  </div>

                  <div style={{ marginTop: "12px", paddingTop: "10px", borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", fontSize: "0.75rem" }}>
                    <span style={{ color: "var(--primary)", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
                      <ArrowRight style={{ width: "14px", height: "14px" }} />
                      Recommended: {opp.recommended_action}
                    </span>
                    <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontWeight: 600 }}>
                      Open 360° Lead →
                    </span>
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* Right Column: Overdue Follow-ups & Anti-Theft Status */}
        <div style={{ display: "flex", flexDirection: "column", gap: "24px" }}>
          {/* Overdue Follow-ups */}
          <div className="card" style={{ padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", paddingBottom: "14px", borderBottom: "1px solid var(--border-subtle)", marginBottom: "14px" }}>
              <h3 style={{ fontSize: "0.9375rem", fontWeight: 800, color: "var(--rose-dark)", display: "flex", alignItems: "center", gap: "8px" }}>
                <AlertTriangle style={{ width: "18px", height: "18px", color: "var(--rose)" }} />
                Overdue Follow-ups ({overdueTasks.length})
              </h3>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "8px", maxHeight: "240px", overflowY: "auto", paddingRight: "4px" }}>
              {overdueTasks.length === 0 ? (
                <p style={{ textAlign: "center", padding: "24px 0", fontSize: "0.8125rem", color: "var(--emerald-dark)", fontWeight: 600 }}>
                  ✓ Zero overdue follow-ups! Great momentum.
                </p>
              ) : (
                overdueTasks.map((task) => (
                  <div
                    key={task.id}
                    style={{
                      padding: "10px 12px",
                      borderRadius: "8px",
                      border: "1px solid var(--border-subtle)",
                      background: "var(--bg-surface)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "space-between",
                      gap: "12px"
                    }}
                  >
                    <div>
                      <p style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>{task.title}</p>
                      <p style={{ fontSize: "0.6875rem", color: "var(--rose)", fontWeight: 600, marginTop: "2px" }}>
                        Due {new Date(task.due_at!).toLocaleDateString()}
                      </p>
                      <p style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>Assigned: {task.assigned_to_name || "Unassigned"}</p>
                    </div>

                    <button
                      onClick={() => task.lead_id && handleLeadClick(task.lead_id)}
                      className="btn-secondary"
                      style={{ fontSize: "0.6875rem", padding: "4px 10px", whiteSpace: "nowrap" }}
                    >
                      Call Now
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Data Protection & Anti-Theft Status */}
          <div className="card" style={{ padding: "20px" }}>
            <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.9375rem", fontWeight: 800, color: "var(--purple-dark)", paddingBottom: "12px", borderBottom: "1px solid var(--border-subtle)", marginBottom: "12px" }}>
              <ShieldCheck style={{ width: "18px", height: "18px", color: "var(--purple)" }} />
              Lead Intelligence Radar Telemetry
            </div>

            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", lineHeight: "1.5", marginBottom: "14px" }}>
              Real-time audit tracking is continuously analyzing telecaller access frequency, contact view counts, and export permissions to prevent customer data leakage.
            </p>

            <div style={{
              padding: "12px",
              borderRadius: "8px",
              background: "var(--bg-surface-subtle)",
              border: "1px solid var(--border-subtle)",
              fontSize: "0.6875rem",
              display: "flex",
              flexDirection: "column",
              gap: "8px",
              fontFamily: "monospace"
            }}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Contact Data Masking:</span>
                <span style={{ color: "var(--emerald-dark)", fontWeight: 700 }}>ENFORCED</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Field-level Export Guard:</span>
                <span style={{ color: "var(--emerald-dark)", fontWeight: 700 }}>ACTIVE</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <span style={{ color: "var(--text-secondary)" }}>Access Anomaly Trigger:</span>
                <span style={{ color: "var(--primary)", fontWeight: 700 }}>0 FLAGGED</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
