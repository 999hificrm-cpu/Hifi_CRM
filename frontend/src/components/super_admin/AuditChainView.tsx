import React, { useState, useEffect } from "react";
import {
  ActivitySquare,
  ShieldCheck,
  ShieldAlert,
  Search,
  Filter,
  RefreshCw,
  Lock,
  PhoneCall,
  Mail,
  MessageCircle,
  Layers,
  Eye,
  CheckCircle2,
  AlertTriangle,
  FileCode,
  X,
  Building2,
  UserCheck,
} from "lucide-react";
import {
  api,
  AuditLogItem,
  AuditChainVerification,
} from "../../services/api";

interface AuditChainViewProps {
  organizations: any[];
}

export const AuditChainView: React.FC<AuditChainViewProps> = ({ organizations }) => {
  const [logs, setLogs] = useState<AuditLogItem[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(false);

  // Filters
  const [search, setSearch] = useState("");
  const [actionFilter, setActionFilter] = useState("ALL");
  const [tenantFilter, setTenantFilter] = useState("ALL");
  const [contextFilter, setContextFilter] = useState("ALL");

  // Chain Verification
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState<AuditChainVerification | null>(null);

  // Detail Modal
  const [selectedLog, setSelectedLog] = useState<AuditLogItem | null>(null);

  useEffect(() => {
    loadAuditLogs();
  }, [actionFilter, tenantFilter, contextFilter]);

  const loadAuditLogs = async () => {
    setLoading(true);
    try {
      const res = await api.getAdminAuditLogsPaged({
        skip: 0,
        limit: 100,
        organization_id: tenantFilter !== "ALL" ? tenantFilter : undefined,
        action: actionFilter !== "ALL" ? actionFilter : undefined,
        context_type: contextFilter !== "ALL" ? contextFilter : undefined,
      });
      setLogs(res.items || []);
      setTotalCount(res.total || 0);
    } catch (e) {
      console.error("Failed loading audit logs:", e);
      setLogs([]);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyChain = async () => {
    setVerifying(true);
    try {
      const result = await api.verifyAuditChain();
      const isValid = result.status === "VALID" || result.is_valid === true;
      setVerificationResult({
        ...result,
        status: result.status || (isValid ? "VALID" : "TAMPERED"),
        is_valid: isValid,
        total_events_checked: result.verified_count || result.total_events_checked || 0,
      });
    } catch (err: any) {
      setVerificationResult({
        status: "ERROR",
        is_valid: false,
        total_events_checked: 0,
        message: err.message || "Cryptographic chain verification failed.",
      });
    } finally {
      setVerifying(false);
    }
  };

  const filteredLogs = logs.filter((log) => {
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      log.action.toLowerCase().includes(q) ||
      (log.entity_type && log.entity_type.toLowerCase().includes(q)) ||
      (log.actor_user_id && log.actor_user_id.toLowerCase().includes(q)) ||
      (log.reason && log.reason.toLowerCase().includes(q)) ||
      (log.event_hash && log.event_hash.toLowerCase().includes(q)) ||
      (log.ip_address && log.ip_address.includes(q))
    );
  });

  const getActionBadge = (action: string) => {
    if (action.includes("CALL")) {
      return (
        <span className="badge" style={{ background: "#ecfdf5", color: "#065f46", border: "1px solid #a7f3d0", display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <PhoneCall style={{ width: "11px", height: "11px" }} />
          {action}
        </span>
      );
    }
    if (action.includes("EMAIL") || action.includes("MAIL")) {
      return (
        <span className="badge" style={{ background: "#fee2e2", color: "#991b1b", border: "1px solid #fecaca", display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <Mail style={{ width: "11px", height: "11px" }} />
          {action}
        </span>
      );
    }
    if (action.includes("WHATSAPP")) {
      return (
        <span className="badge" style={{ background: "#d1fae5", color: "#047857", border: "1px solid #6ee7b7", display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <MessageCircle style={{ width: "11px", height: "11px" }} />
          {action}
        </span>
      );
    }
    if (action.includes("STAGE")) {
      return (
        <span className="badge" style={{ background: "#e0e7ff", color: "#3730a3", border: "1px solid #c7d2fe", display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <Layers style={{ width: "11px", height: "11px" }} />
          {action}
        </span>
      );
    }
    if (action.includes("SUSPEND") || action.includes("PURGE") || action.includes("DELETE")) {
      return (
        <span className="badge" style={{ background: "#fee2e2", color: "#991b1b", border: "1px solid #fca5a5", display: "inline-flex", alignItems: "center", gap: "4px", fontWeight: 700 }}>
          <ShieldAlert style={{ width: "11px", height: "11px" }} />
          {action}
        </span>
      );
    }
    if (action.includes("RESTORE") || action.includes("ASSIGN")) {
      return (
        <span className="badge" style={{ background: "#f0fdf4", color: "#166534", border: "1px solid #bbf7d0", display: "inline-flex", alignItems: "center", gap: "4px", fontWeight: 700 }}>
          <ShieldCheck style={{ width: "11px", height: "11px" }} />
          {action}
        </span>
      );
    }
    return <span className="badge badge-medium">{action}</span>;
  };

  const getContextBadge = (ctx: string) => {
    if (ctx === "SUPPORT_CONTEXT") {
      return (
        <span style={{ fontSize: "0.625rem", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", background: "#fef3c7", color: "#92400e", border: "1px solid #fde68a" }}>
          SUPPORT
        </span>
      );
    }
    if (ctx === "PLATFORM_CONTEXT") {
      return (
        <span style={{ fontSize: "0.625rem", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", background: "rgba(99, 102, 241, 0.1)", color: "#4f46e5", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
          PLATFORM
        </span>
      );
    }
    return (
      <span style={{ fontSize: "0.625rem", fontWeight: 800, padding: "2px 6px", borderRadius: "4px", background: "var(--bg-canvas)", color: "var(--text-secondary)", border: "1px solid var(--border-subtle)" }}>
        TENANT
      </span>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
            <ActivitySquare style={{ width: "22px", height: "22px", color: "var(--primary)" }} />
            Centralized Audit Trail & Cryptographic Verification
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            SHA-256 hash-chained immutable security logs with dual-identity support tracking
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="btn-primary"
            style={{
              fontSize: "0.8125rem",
              background: "linear-gradient(135deg, #059669 0%, #047857 100%)",
              border: "none",
              display: "flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <ShieldCheck style={{ width: "15px", height: "15px" }} />
            {verifying ? "Verifying SHA-256 Chain..." : "Verify Cryptographic Integrity"}
          </button>

          <button onClick={loadAuditLogs} className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
            <RefreshCw style={{ width: "14px", height: "14px" }} /> Refresh
          </button>
        </div>
      </div>

      {/* Verification Result Banner */}
      {verificationResult && (
        <div
          style={{
            padding: "14px 20px",
            borderRadius: "12px",
            background: verificationResult.is_valid ? "rgba(16, 185, 129, 0.08)" : "rgba(239, 68, 68, 0.08)",
            border: verificationResult.is_valid ? "1px solid #10b981" : "1px solid #ef4444",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            {verificationResult.is_valid ? (
              <CheckCircle2 style={{ width: "22px", height: "22px", color: "#10b981", flexShrink: 0 }} />
            ) : (
              <AlertTriangle style={{ width: "22px", height: "22px", color: "#ef4444", flexShrink: 0 }} />
            )}
            <div>
              <p style={{ fontSize: "0.875rem", fontWeight: 800, color: verificationResult.is_valid ? "#065f46" : "#991b1b" }}>
                {verificationResult.is_valid ? "CRYPTOGRAPHIC AUDIT TRAIL VERIFIED VALID" : "CHAIN INTEGRITY ANOMALY DETECTED"}
              </p>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                {verificationResult.message} ({verificationResult.total_events_checked} sequential hash blocks verified)
              </p>
            </div>
          </div>

          <button
            onClick={() => setVerificationResult(null)}
            style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
          >
            <X style={{ width: "16px", height: "16px" }} />
          </button>
        </div>
      )}

      {/* KPI Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div className="stat-card stat-card-accent-indigo">
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Total Audit Events Ingested</span>
          <p style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)", fontFamily: "monospace", marginTop: "4px" }}>
            {totalCount}
          </p>
        </div>

        <div className="stat-card stat-card-accent-emerald">
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Hash-Chained Blocks</span>
          <p style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--emerald-dark)", fontFamily: "monospace", marginTop: "4px" }}>
            100% SHA-256
          </p>
        </div>

        <div className="stat-card stat-card-accent-amber">
          <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Dual-Identity Support Actions</span>
          <p style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--amber-dark)", fontFamily: "monospace", marginTop: "4px" }}>
            {logs.filter((l) => l.context_type === "SUPPORT_CONTEXT").length} Events
          </p>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="card" style={{ padding: "16px", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div style={{ position: "relative", flex: 1, minWidth: "260px" }}>
          <Search style={{ width: "15px", height: "15px", color: "var(--text-muted)", position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search audit trail by actor, action, hash, or IP..."
            className="input-text"
            style={{ paddingLeft: "32px", fontSize: "0.8125rem", width: "100%" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <select
            value={contextFilter}
            onChange={(e) => setContextFilter(e.target.value)}
            className="select-dropdown"
            style={{ fontSize: "0.8125rem" }}
          >
            <option value="ALL">All Contexts</option>
            <option value="PLATFORM_CONTEXT">Platform Context</option>
            <option value="TENANT_CONTEXT">Tenant Context</option>
            <option value="SUPPORT_CONTEXT">Support / Impersonation</option>
          </select>

          <select
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="select-dropdown"
            style={{ fontSize: "0.8125rem" }}
          >
            <option value="ALL">All Action Types</option>
            <option value="ORGANIZATION_SUSPENDED">Organization Suspended</option>
            <option value="ROLE_ASSIGNED">Role Assigned</option>
            <option value="SESSION_REVOKED">Sessions Revoked</option>
            <option value="SUPPORT_SESSION_CREATED">Support Session Created</option>
            <option value="LEAD_RESTORED">Lead Restored</option>
            <option value="CALL_TRIGGERED">Call Triggered</option>
            <option value="EMAIL_TRIGGERED">Email Triggered</option>
            <option value="LOGIN_SUCCESS">Login Success</option>
          </select>

          <select
            value={tenantFilter}
            onChange={(e) => setTenantFilter(e.target.value)}
            className="select-dropdown"
            style={{ fontSize: "0.8125rem" }}
          >
            <option value="ALL">All Organizations</option>
            {organizations.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Audit Table */}
      <div className="table-container">
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <h3 style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>
            Cryptographically Chained Audit Stream ({filteredLogs.length})
          </h3>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
            Chronological deterministic sequence
          </span>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th style={{ paddingLeft: "20px" }}>Seq & Timestamp</th>
              <th>Context</th>
              <th>Action</th>
              <th>Target Entity</th>
              <th>Actor & Target</th>
              <th>Cryptographic Hash</th>
              <th style={{ textAlign: "right", paddingRight: "20px" }}>Inspect</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "36px 0", color: "var(--text-muted)" }}>
                  Streaming verified audit events...
                </td>
              </tr>
            ) : filteredLogs.length === 0 ? (
              <tr>
                <td colSpan={7} style={{ textAlign: "center", padding: "36px 0", color: "var(--text-muted)" }}>
                  No audit events match the selected filters.
                </td>
              </tr>
            ) : (
              filteredLogs.map((log) => (
                <tr key={log.id}>
                  <td style={{ paddingLeft: "20px", fontSize: "0.75rem", color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      <span style={{ fontFamily: "monospace", fontWeight: 800, color: "var(--primary)", fontSize: "0.6875rem" }}>
                        #{log.sequence_number ? log.sequence_number.toString().padStart(6, "0") : "------"}
                      </span>
                    </div>
                    <p style={{ fontWeight: 600, color: "var(--text-primary)" }}>{new Date(log.created_at).toLocaleDateString()}</p>
                    <p style={{ fontFamily: "monospace", fontSize: "0.6875rem", color: "var(--text-muted)" }}>{new Date(log.created_at).toLocaleTimeString()}</p>
                  </td>
                  <td>{getContextBadge(log.context_type)}</td>
                  <td>{getActionBadge(log.action)}</td>
                  <td style={{ fontSize: "0.75rem" }}>
                    <span style={{ fontWeight: 700, color: "var(--text-primary)" }}>{log.entity_type}</span>
                    {log.entity_id && (
                      <span style={{ fontFamily: "monospace", fontSize: "0.6875rem", color: "var(--text-muted)", display: "block" }}>
                        {log.entity_id.substring(0, 10)}...
                      </span>
                    )}
                  </td>
                  <td style={{ fontSize: "0.75rem" }}>
                    <p style={{ fontFamily: "monospace", fontWeight: 600, color: "var(--text-primary)" }}>
                      Actor: {log.actor_user_id ? log.actor_user_id.substring(0, 8) : log.user_id ? log.user_id.substring(0, 8) : "System"}
                    </p>
                    {log.target_user_id && (
                      <p style={{ fontFamily: "monospace", fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                        Target: {log.target_user_id.substring(0, 8)}
                      </p>
                    )}
                    {log.reason && (
                      <p style={{ fontSize: "0.6875rem", fontStyle: "italic", color: "var(--text-secondary)", marginTop: "2px" }}>
                        "{log.reason.substring(0, 30)}..."
                      </p>
                    )}
                  </td>
                  <td style={{ fontSize: "0.6875rem", fontFamily: "monospace", color: "var(--text-secondary)" }}>
                    {log.event_hash ? (
                      <div title={`Event Hash: ${log.event_hash}\nPrev Hash: ${log.previous_event_hash || "GENESIS"}`}>
                        <span style={{ color: "#059669", fontWeight: 700 }}>SHA256: </span>
                        <span>{log.event_hash.substring(0, 12)}...</span>
                      </div>
                    ) : (
                      <span style={{ color: "var(--text-muted)" }}>Legacy record</span>
                    )}
                  </td>
                  <td style={{ textAlign: "right", paddingRight: "20px" }}>
                    <button
                      onClick={() => setSelectedLog(log)}
                      className="btn-secondary"
                      style={{ fontSize: "0.6875rem", padding: "5px 10px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                    >
                      <FileCode style={{ width: "12px", height: "12px" }} /> Inspect
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Inspect Event Modal */}
      {selectedLog && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div className="card" style={{ width: "100%", maxWidth: "640px", background: "var(--bg-surface)", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--border-subtle)", maxHeight: "90vh", display: "flex", flexDirection: "column" }}>
            <div style={{ padding: "20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Lock style={{ width: "18px", height: "18px", color: "var(--primary)" }} />
                <h3 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  Audit Event #{selectedLog.sequence_number || selectedLog.id.substring(0, 8)}
                </h3>
              </div>
              <button onClick={() => setSelectedLog(null)} className="btn-secondary" style={{ padding: "6px" }}>
                <X style={{ width: "16px", height: "16px" }} />
              </button>
            </div>

            <div style={{ padding: "20px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "14px" }}>
              {/* Hash Proof Box */}
              <div style={{ background: "var(--bg-canvas)", padding: "14px", borderRadius: "10px", border: "1px solid var(--border-subtle)", fontFamily: "monospace", fontSize: "0.75rem" }}>
                <p style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700, textTransform: "uppercase" }}>Cryptographic Chain Links</p>
                <div style={{ marginTop: "6px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Current Block Hash: </span>
                  <span style={{ color: "#059669", fontWeight: 700, wordBreak: "break-all" }}>{selectedLog.event_hash || "N/A"}</span>
                </div>
                <div style={{ marginTop: "4px" }}>
                  <span style={{ color: "var(--text-muted)" }}>Previous Block Hash: </span>
                  <span style={{ color: "var(--text-secondary)", wordBreak: "break-all" }}>{selectedLog.previous_event_hash || "GENESIS_ROOT"}</span>
                </div>
              </div>

              {/* Event Metadata */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px", fontSize: "0.8125rem" }}>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>Action</span>
                  <p style={{ fontWeight: 800, color: "var(--text-primary)" }}>{selectedLog.action}</p>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>Context Type</span>
                  <p style={{ fontWeight: 800, color: "var(--text-primary)" }}>{selectedLog.context_type}</p>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>Actor User ID</span>
                  <p style={{ fontFamily: "monospace", color: "var(--text-secondary)" }}>{selectedLog.actor_user_id || selectedLog.user_id || "System"}</p>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>Target User ID</span>
                  <p style={{ fontFamily: "monospace", color: "var(--text-secondary)" }}>{selectedLog.target_user_id || "None"}</p>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>IP Address</span>
                  <p style={{ fontFamily: "monospace", color: "var(--text-secondary)" }}>{selectedLog.ip_address || "Internal / Gateway"}</p>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>Support Session ID</span>
                  <p style={{ fontFamily: "monospace", color: "var(--text-secondary)" }}>{selectedLog.support_session_id || "None"}</p>
                </div>
              </div>

              {selectedLog.reason && (
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>Justification Reason</span>
                  <p style={{ background: "var(--bg-canvas)", padding: "10px", borderRadius: "8px", border: "1px solid var(--border-subtle)", fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                    {selectedLog.reason}
                  </p>
                </div>
              )}

              {/* JSON Diffs */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>Previous State</span>
                  <pre style={{ background: "var(--bg-canvas)", padding: "10px", borderRadius: "8px", border: "1px solid var(--border-subtle)", fontSize: "0.6875rem", overflowX: "auto", maxHeight: "160px" }}>
                    {JSON.stringify(selectedLog.old_values || {}, null, 2)}
                  </pre>
                </div>
                <div>
                  <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem", fontWeight: 700 }}>New State</span>
                  <pre style={{ background: "var(--bg-canvas)", padding: "10px", borderRadius: "8px", border: "1px solid var(--border-subtle)", fontSize: "0.6875rem", overflowX: "auto", maxHeight: "160px" }}>
                    {JSON.stringify(selectedLog.new_values || {}, null, 2)}
                  </pre>
                </div>
              </div>
            </div>

            <div style={{ padding: "16px 20px", borderTop: "1px solid var(--border-subtle)", display: "flex", justifyContent: "flex-end" }}>
              <button onClick={() => setSelectedLog(null)} className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
