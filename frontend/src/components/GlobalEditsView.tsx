import React, { useState, useEffect } from "react";
import { api } from "../services/api";
import { ActivitySquare, Check, X, Building2, UserCheck, Search, Filter } from "lucide-react";

export const GlobalEditsView: React.FC = () => {
  const [edits, setEdits] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterType, setFilterType] = useState<"ALL" | "COMPANY" | "PERSON">("ALL");

  useEffect(() => {
    loadEdits();
  }, []);

  const loadEdits = async () => {
    setLoading(true);
    try {
      const data = await api.getPendingGlobalEdits();
      setEdits(data || []);
    } catch (err) {
      console.error("Failed to load global edits:", err);
    } finally {
      setLoading(false);
    }
  };

  const handleResolve = async (id: string, action: "APPROVE" | "REJECT") => {
    try {
      await api.resolveGlobalEdit(id, action);
      loadEdits();
    } catch (err: any) {
      alert(err.message || "Failed to resolve edit request");
    }
  };

  const filteredEdits = edits.filter(e => {
    if (filterType !== "ALL" && e.entity_type !== filterType) return false;
    return true;
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px", padding: "24px", maxWidth: "1200px", margin: "0 auto", width: "100%" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <div
            style={{
              width: "48px",
              height: "48px",
              borderRadius: "12px",
              background: "linear-gradient(135deg, rgba(245, 158, 11, 0.2), rgba(217, 119, 6, 0.1))",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "var(--amber)",
              flexShrink: 0,
            }}
          >
            <ActivitySquare style={{ width: "24px", height: "24px" }} />
          </div>
          <div>
            <h2 style={{ margin: 0, fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
              Global Data Edits
              <span className="badge badge-hot" style={{ fontSize: "0.6875rem" }}>
                {edits.length} PENDING
              </span>
            </h2>
            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px", marginBottom: 0 }}>
              Review and approve data modifications submitted by Data Entry operators.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value as any)}
            className="input-text"
            style={{ width: "160px" }}
          >
            <option value="ALL">All Entities</option>
            <option value="COMPANY">Companies</option>
            <option value="PERSON">People</option>
          </select>
        </div>
      </div>

      {/* List */}
      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            Loading pending requests...
          </div>
        ) : filteredEdits.length === 0 ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
            No pending edit requests found.
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column" }}>
            {filteredEdits.map((edit) => (
              <div
                key={edit.id}
                style={{
                  padding: "16px 20px",
                  borderBottom: "1px solid var(--border-subtle)",
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    {edit.entity_type === "COMPANY" ? (
                      <Building2 style={{ width: "16px", height: "16px", color: "var(--primary)" }} />
                    ) : (
                      <UserCheck style={{ width: "16px", height: "16px", color: "var(--emerald)" }} />
                    )}
                    <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      {edit.entity_type === "COMPANY" ? "Company Edit" : "Person Edit"} - {edit.entity_id}
                    </span>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                      Submitted by: {edit.submitted_by_name} ({new Date(edit.created_at).toLocaleString()})
                    </span>
                  </div>
                  <div style={{ display: "flex", gap: "8px" }}>
                    <button
                      onClick={() => handleResolve(edit.id, "REJECT")}
                      className="btn-secondary"
                      style={{ padding: "4px 10px", fontSize: "0.75rem", color: "var(--rose-dark)" }}
                    >
                      <X style={{ width: "14px", height: "14px" }} /> Reject
                    </button>
                    <button
                      onClick={() => handleResolve(edit.id, "APPROVE")}
                      className="btn-primary"
                      style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                    >
                      <Check style={{ width: "14px", height: "14px" }} /> Approve
                    </button>
                  </div>
                </div>

                <div
                  style={{
                    background: "var(--bg-surface-subtle)",
                    padding: "12px",
                    borderRadius: "8px",
                    fontSize: "0.75rem",
                    fontFamily: "monospace",
                    whiteSpace: "pre-wrap",
                    color: "var(--text-secondary)",
                    border: "1px solid var(--border-color)",
                  }}
                >
                  {JSON.stringify(edit.changes_json, null, 2)}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
