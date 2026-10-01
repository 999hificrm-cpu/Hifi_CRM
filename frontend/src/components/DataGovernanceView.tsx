import React, { useState, useEffect } from "react";
import { api, DedupeCandidate, DataQualityIssue } from "../services/api";
import { ShieldCheck, ShieldAlert, GitMerge, FileX, Shield, RefreshCw, AlertTriangle } from "lucide-react";

export const DataGovernanceView: React.FC = () => {
  const [activeTab, setActiveTab] = useState<"dedupe" | "quality">("dedupe");
  const [candidates, setCandidates] = useState<DedupeCandidate[]>([]);
  const [issues, setIssues] = useState<DataQualityIssue[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchData();
  }, [activeTab]);

  const fetchData = async () => {
    setLoading(true);
    try {
      if (activeTab === "dedupe") {
        const res = await api.getDedupeCandidates("PENDING");
        setCandidates(res || []);
      } else {
        const res = await api.getDataQualityIssues();
        setIssues(res || []);
      }
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleResolveDedupe = async (id: string, action: string) => {
    try {
      await api.resolveDedupeCandidate(id, action);
      fetchData(); // Refresh list
    } catch (e: any) {
      alert(e.message || "Failed to resolve");
    }
  };

  const handleRunScan = async () => {
    try {
      await api.triggerDedupeScan();
      alert("Background scan triggered successfully.");
    } catch (e: any) {
      alert(e.message || "Failed to trigger scan");
    }
  };

  return (
    <div style={{ maxWidth: "1200px", margin: "0 auto" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
            <Shield style={{ width: "24px", height: "24px", color: "var(--primary)" }} />
            Data Governance Hub
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "4px" }}>
            Monitor and resolve data quality issues and duplicate records to maintain CRM health.
          </p>
        </div>
        <button className="btn-secondary" onClick={handleRunScan}>
          <RefreshCw style={{ width: "16px", height: "16px" }} />
          Run Data Scan Now
        </button>
      </div>

      <div style={{ display: "flex", gap: "12px", marginBottom: "24px" }}>
        <button
          className={`nav-tab-btn ${activeTab === "dedupe" ? "active" : ""}`}
          onClick={() => setActiveTab("dedupe")}
          style={{ padding: "8px 16px", borderRadius: "8px" }}
        >
          <GitMerge style={{ width: "16px", height: "16px" }} />
          Deduplication Candidates
        </button>
        <button
          className={`nav-tab-btn ${activeTab === "quality" ? "active" : ""}`}
          onClick={() => setActiveTab("quality")}
          style={{ padding: "8px 16px", borderRadius: "8px" }}
        >
          <ShieldAlert style={{ width: "16px", height: "16px" }} />
          Data Quality Issues
        </button>
      </div>

      <div className="card">
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>Loading...</div>
        ) : activeTab === "dedupe" ? (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Match Basis</th>
                  <th>Confidence</th>
                  <th>Record A</th>
                  <th>Record B</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {candidates.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "40px", color: "var(--text-tertiary)" }}>
                      <ShieldCheck style={{ width: "32px", height: "32px", margin: "0 auto 12px auto", color: "var(--success)" }} />
                      No duplicate candidates found. Your data is clean.
                    </td>
                  </tr>
                ) : (
                  candidates.map((c) => (
                    <tr key={c.id}>
                      <td>
                        <span style={{ fontSize: "0.75rem", fontWeight: 700, padding: "4px 8px", background: "var(--bg-canvas)", borderRadius: "4px", border: "1px solid var(--border-color)" }}>
                          {c.match_basis?.replace(/_/g, " ")}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <div style={{ flex: 1, height: "6px", background: "var(--bg-canvas)", borderRadius: "3px", overflow: "hidden" }}>
                            <div style={{ width: `${c.match_confidence * 100}%`, height: "100%", background: c.match_confidence > 0.9 ? "var(--success)" : "var(--warning)" }} />
                          </div>
                          <span style={{ fontSize: "0.75rem", fontWeight: 700 }}>{Math.round(c.match_confidence * 100)}%</span>
                        </div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{c.lead_a?.contact_name || c.lead_a?.title}</div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{c.lead_a?.contact_email || "No Email"}</div>
                      </td>
                      <td>
                        <div style={{ fontWeight: 600, fontSize: "0.875rem" }}>{c.lead_b?.contact_name || c.lead_b?.title}</div>
                        <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>{c.lead_b?.contact_email || "No Email"}</div>
                      </td>
                      <td style={{ textAlign: "right" }}>
                        <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                          <button onClick={() => handleResolveDedupe(c.id, "MERGE")} className="btn-primary" style={{ padding: "6px 12px", fontSize: "0.75rem" }}>
                            <GitMerge style={{ width: "12px", height: "12px" }} /> Merge
                          </button>
                          <button onClick={() => handleResolveDedupe(c.id, "KEEP_SEPARATE")} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "0.75rem" }}>
                            <FileX style={{ width: "12px", height: "12px" }} /> Keep Separate
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Entity</th>
                  <th>Issue Type</th>
                  <th>Severity</th>
                  <th>Description</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {issues.length === 0 ? (
                  <tr>
                    <td colSpan={5} style={{ textAlign: "center", padding: "40px", color: "var(--text-tertiary)" }}>
                      <ShieldCheck style={{ width: "32px", height: "32px", margin: "0 auto 12px auto", color: "var(--success)" }} />
                      No data quality issues found.
                    </td>
                  </tr>
                ) : (
                  issues.map((i) => (
                    <tr key={i.id}>
                      <td style={{ fontWeight: 600 }}>{i.entity_type} <span style={{ fontSize: "0.7rem", color: "var(--text-tertiary)", fontWeight: 400 }}>({i.entity_id.substring(0, 8)})</span></td>
                      <td>
                        <span style={{ fontSize: "0.75rem", fontWeight: 700, padding: "4px 8px", background: "var(--bg-canvas)", borderRadius: "4px", border: "1px solid var(--border-color)" }}>
                          {i.issue_type}
                        </span>
                      </td>
                      <td>
                        {i.severity === "CRITICAL" ? (
                          <span style={{ color: "var(--danger)", display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem", fontWeight: 700 }}>
                            <AlertTriangle style={{ width: "14px", height: "14px" }} /> CRITICAL
                          </span>
                        ) : (
                          <span style={{ color: "var(--warning)", display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem", fontWeight: 700 }}>
                            <AlertTriangle style={{ width: "14px", height: "14px" }} /> WARNING
                          </span>
                        )}
                      </td>
                      <td style={{ fontSize: "0.875rem", color: "var(--text-secondary)" }}>{i.description}</td>
                      <td>
                        <span style={{ fontSize: "0.75rem", fontWeight: 700, padding: "4px 8px", borderRadius: "12px", background: i.status === "OPEN" ? "rgba(239,68,68,0.1)" : "rgba(34,197,94,0.1)", color: i.status === "OPEN" ? "var(--danger)" : "var(--success)" }}>
                          {i.status}
                        </span>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};
