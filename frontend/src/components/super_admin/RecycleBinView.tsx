import React, { useState, useEffect } from "react";
import {
  Trash2,
  RotateCcw,
  RefreshCw,
  Search,
  AlertTriangle,
  CheckCircle2,
  Building2,
  Users,
  Contact2,
  Layers,
  Briefcase,
  X,
} from "lucide-react";
import { api, RecycleBinItem } from "../../services/api";

export const RecycleBinView: React.FC = () => {
  const [activeEntity, setActiveEntity] = useState<string>("leads");
  const [items, setItems] = useState<RecycleBinItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [msg, setMsg] = useState<string | null>(null);

  // Restore state
  const [restoringId, setRestoringId] = useState<string | null>(null);

  // Purge state
  const [itemToPurge, setItemToPurge] = useState<RecycleBinItem | null>(null);
  const [purgeReason, setPurgeReason] = useState("");
  const [purging, setPurging] = useState(false);

  useEffect(() => {
    loadRecycleItems();
  }, [activeEntity]);

  const loadRecycleItems = async () => {
    setLoading(true);
    try {
      const data = await api.getRecycleBinItems(activeEntity);
      setItems(data);
    } catch (e) {
      console.error("Failed loading recycle bin items:", e);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  const handleRestore = async (item: RecycleBinItem) => {
    setRestoringId(item.id);
    try {
      await api.restoreRecycleBinItem(
        activeEntity,
        item.id,
        "Restored by Super Admin from Recycle Bin"
      );
      setMsg(`Successfully restored ${item.title || item.name || item.full_name || item.id}.`);
      setItems((prev) => prev.filter((i) => i.id !== item.id));
    } catch (err: any) {
      alert(err.message || "Failed to restore item.");
    } finally {
      setRestoringId(null);
    }
  };

  const handlePurge = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!itemToPurge) return;
    setPurging(true);
    try {
      await api.purgeRecycleBinItem(
        activeEntity,
        itemToPurge.id,
        purgeReason || "Permanent deletion requested by Super Admin"
      );
      setMsg(`Permanently purged record.`);
      setItems((prev) => prev.filter((i) => i.id !== itemToPurge.id));
      setItemToPurge(null);
      setPurgeReason("");
    } catch (err: any) {
      alert(err.message || "Failed to permanently purge item.");
    } finally {
      setPurging(false);
    }
  };

  const filteredItems = items.filter((item) => {
    if (!search) return true;
    const q = search.toLowerCase();
    const name = (item.title || item.name || item.full_name || item.email || "").toLowerCase();
    const reason = (item.deletion_reason || "").toLowerCase();
    const id = item.id.toLowerCase();
    return name.includes(q) || reason.includes(q) || id.includes(q);
  });

  const entityTabs = [
    { id: "leads", label: "Leads", icon: Layers },
    { id: "companies", label: "Companies", icon: Building2 },
    { id: "contacts", label: "Contacts", icon: Contact2 },
    { id: "users", label: "Users", icon: Users },
    { id: "organizations", label: "Organizations", icon: Briefcase },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
            <Trash2 style={{ width: "22px", height: "22px", color: "#ef4444" }} />
            Enterprise Recycle Bin & Disaster Recovery
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Audit-safe soft-deleted items across organizations with 1-click restoration or irreversible purge
          </p>
        </div>

        <button onClick={loadRecycleItems} className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
          <RefreshCw style={{ width: "14px", height: "14px" }} /> Refresh
        </button>
      </div>

      {msg && (
        <div style={{ padding: "12px 16px", borderRadius: "10px", background: "var(--emerald-light)", border: "1px solid var(--emerald-border)", color: "var(--emerald-dark)", fontSize: "0.8125rem", fontWeight: 600, display: "flex", alignItems: "center", gap: "8px" }}>
          <CheckCircle2 style={{ width: "16px", height: "16px" }} />
          <span>{msg}</span>
          <button onClick={() => setMsg(null)} style={{ marginLeft: "auto", background: "none", border: "none", cursor: "pointer", color: "var(--emerald-dark)" }}>
            <X style={{ width: "14px", height: "14px" }} />
          </button>
        </div>
      )}

      {/* Entity Selector Tabs */}
      <div style={{ display: "flex", gap: "8px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "8px", flexWrap: "wrap" }}>
        {entityTabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = activeEntity === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => setActiveEntity(tab.id)}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "8px 16px",
                borderRadius: "8px",
                background: isActive ? "rgba(99, 102, 241, 0.1)" : "transparent",
                color: isActive ? "var(--primary)" : "var(--text-secondary)",
                border: isActive ? "1px solid rgba(99, 102, 241, 0.3)" : "1px solid transparent",
                fontWeight: 700,
                fontSize: "0.8125rem",
                cursor: "pointer",
              }}
            >
              <Icon style={{ width: "16px", height: "16px" }} />
              {tab.label}
            </button>
          );
        })}
      </div>

      {/* Search Bar */}
      <div className="card" style={{ padding: "14px 18px", display: "flex", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
        <div style={{ position: "relative", flex: 1, maxWidth: "420px" }}>
          <Search style={{ width: "15px", height: "15px", color: "var(--text-muted)", position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder={`Search deleted ${activeEntity} by name, reason, or ID...`}
            className="input-text"
            style={{ paddingLeft: "32px", fontSize: "0.8125rem", width: "100%" }}
          />
        </div>
        <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>
          {filteredItems.length} soft-deleted items found
        </span>
      </div>

      {/* Table */}
      <div className="table-container">
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ paddingLeft: "20px" }}>Deleted Record</th>
              <th>Deleted Timestamp</th>
              <th>Deleted By</th>
              <th>Deletion Reason</th>
              <th style={{ textAlign: "right", paddingRight: "20px" }}>Recovery Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", padding: "36px 0", color: "var(--text-muted)" }}>
                  Scanning recycle bin partition...
                </td>
              </tr>
            ) : filteredItems.length === 0 ? (
              <tr>
                <td colSpan={5} style={{ textAlign: "center", padding: "36px 0", color: "var(--text-muted)" }}>
                  Recycle bin is clean. No deleted {activeEntity} found.
                </td>
              </tr>
            ) : (
              filteredItems.map((item) => {
                const displayName = item.title || item.name || item.full_name || item.email || "Unnamed Entity";
                return (
                  <tr key={item.id}>
                    <td style={{ paddingLeft: "20px" }}>
                      <p style={{ fontWeight: 700, color: "var(--text-primary)" }}>{displayName}</p>
                      <p style={{ fontFamily: "monospace", fontSize: "0.6875rem", color: "var(--text-muted)" }}>{item.id}</p>
                    </td>
                    <td style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      {item.deleted_at ? (
                        <>
                          <p style={{ fontWeight: 600 }}>{new Date(item.deleted_at).toLocaleDateString()}</p>
                          <p style={{ fontFamily: "monospace", fontSize: "0.6875rem", color: "var(--text-muted)" }}>{new Date(item.deleted_at).toLocaleTimeString()}</p>
                        </>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      {item.deleted_by ? `${item.deleted_by.substring(0, 8)}...` : "System / Admin"}
                    </td>
                    <td style={{ fontSize: "0.75rem", color: "var(--text-secondary)", maxWidth: "240px" }}>
                      <span style={{ fontStyle: item.deletion_reason ? "normal" : "italic", color: item.deletion_reason ? "var(--text-primary)" : "var(--text-muted)" }}>
                        {item.deletion_reason || "No explicit reason specified"}
                      </span>
                    </td>
                    <td style={{ textAlign: "right", paddingRight: "20px" }}>
                      <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "8px" }}>
                        <button
                          onClick={() => handleRestore(item)}
                          disabled={restoringId === item.id}
                          className="btn-secondary"
                          style={{
                            fontSize: "0.75rem",
                            padding: "6px 12px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            color: "var(--emerald-dark)",
                            borderColor: "var(--emerald-border)",
                            background: "var(--emerald-light)",
                            fontWeight: 700,
                          }}
                        >
                          <RotateCcw style={{ width: "13px", height: "13px" }} />
                          {restoringId === item.id ? "Restoring..." : "Restore"}
                        </button>

                        <button
                          onClick={() => setItemToPurge(item)}
                          className="btn-secondary"
                          style={{
                            fontSize: "0.75rem",
                            padding: "6px 12px",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "6px",
                            color: "#dc2626",
                            borderColor: "#fecaca",
                            background: "#fee2e2",
                            fontWeight: 700,
                          }}
                        >
                          <Trash2 style={{ width: "13px", height: "13px" }} />
                          Purge
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Permanent Purge Confirmation Modal */}
      {itemToPurge && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div className="card" style={{ width: "100%", maxWidth: "460px", background: "var(--bg-surface)", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
            <div style={{ padding: "20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(239, 68, 68, 0.06)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#dc2626" }}>
                <AlertTriangle style={{ width: "18px", height: "18px" }} />
                <h3 style={{ fontSize: "1rem", fontWeight: 800 }}>Permanent Purge Confirmation</h3>
              </div>
              <button onClick={() => setItemToPurge(null)} className="btn-secondary" style={{ padding: "6px" }}>
                <X style={{ width: "16px", height: "16px" }} />
              </button>
            </div>

            <form onSubmit={handlePurge} style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ padding: "10px 14px", borderRadius: "8px", background: "#fee2e2", color: "#991b1b", fontSize: "0.75rem" }}>
                <strong>Warning:</strong> This action is completely irreversible. <strong>{itemToPurge.title || itemToPurge.name || itemToPurge.full_name || itemToPurge.id}</strong> will be permanently deleted from the database.
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Compliance & Purge Justification Reason <span style={{ color: "#ef4444" }}>*</span>
                </label>
                <textarea
                  value={purgeReason}
                  onChange={(e) => setPurgeReason(e.target.value)}
                  placeholder="e.g. GDPR right to be forgotten / verified obsolete test fixture..."
                  className="input-text"
                  rows={2}
                  style={{ width: "100%", fontSize: "0.75rem" }}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button type="button" onClick={() => setItemToPurge(null)} className="btn-secondary" style={{ fontSize: "0.75rem" }}>Cancel</button>
                <button type="submit" disabled={purging || !purgeReason.trim()} className="btn-primary" style={{ fontSize: "0.75rem", background: "#dc2626", border: "none" }}>
                  {purging ? "Purging..." : "Permanently Purge Record"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
