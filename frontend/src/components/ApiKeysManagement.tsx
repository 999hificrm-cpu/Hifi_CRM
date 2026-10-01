import React, { useState, useEffect } from "react";
import { api, ApiKey } from "../services/api";
import { Key, Plus, Trash2, Copy, AlertTriangle, EyeOff, ShieldCheck } from "lucide-react";

export const ApiKeysManagement: React.FC = () => {
  const [keys, setKeys] = useState<ApiKey[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyData, setNewKeyData] = useState<{ name: string; scopes: string; expires_in_days: number }>({
    name: "",
    scopes: "read",
    expires_in_days: 365,
  });
  const [createdRawKey, setCreatedRawKey] = useState<string | null>(null);

  useEffect(() => {
    fetchKeys();
  }, []);

  const fetchKeys = async () => {
    setLoading(true);
    try {
      const res = await api.getApiKeys();
      setKeys(res || []);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreate = async () => {
    try {
      const scopesArr = newKeyData.scopes.split(",").map((s) => s.trim()).filter(Boolean);
      const res = await api.createApiKey({
        name: newKeyData.name,
        scopes: scopesArr,
        expires_in_days: newKeyData.expires_in_days,
      });
      setCreatedRawKey(res.raw_key);
      fetchKeys();
    } catch (e: any) {
      alert(e.message || "Failed to create API key");
    }
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm("Are you sure you want to revoke this API key? This action cannot be undone.")) return;
    try {
      await api.revokeApiKey(id);
      fetchKeys();
    } catch (e: any) {
      alert(e.message || "Failed to revoke API key");
    }
  };

  const handleCopy = () => {
    if (createdRawKey) {
      navigator.clipboard.writeText(createdRawKey);
      alert("API Key copied to clipboard.");
    }
  };

  const closeModalAndClearKey = () => {
    setCreatedRawKey(null);
    setShowCreateModal(false);
    setNewKeyData({ name: "", scopes: "read", expires_in_days: 365 });
  };

  return (
    <div style={{ maxWidth: "1000px", margin: "0 auto", padding: "24px 0" }}>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
            <Key style={{ width: "24px", height: "24px", color: "var(--primary)" }} />
            API Keys (Developer Settings)
          </h2>
          <p style={{ color: "var(--text-secondary)", fontSize: "0.875rem", marginTop: "4px" }}>
            Manage programmatic access to JARVIS CRM.
          </p>
        </div>
        <button className="btn-primary" onClick={() => setShowCreateModal(true)}>
          <Plus style={{ width: "16px", height: "16px" }} />
          Generate New Key
        </button>
      </div>

      <div className="card table-container">
        {loading ? (
          <div style={{ padding: "40px", textAlign: "center", color: "var(--text-secondary)" }}>Loading API keys...</div>
        ) : keys.length === 0 ? (
          <div style={{ textAlign: "center", padding: "40px", color: "var(--text-tertiary)" }}>
            <ShieldCheck style={{ width: "32px", height: "32px", margin: "0 auto 12px auto", color: "var(--primary)" }} />
            No active API keys found.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Prefix / Hash</th>
                <th>Scopes</th>
                <th>Status</th>
                <th style={{ textAlign: "right" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {keys.map((k) => (
                <tr key={k.id}>
                  <td style={{ fontWeight: 600 }}>{k.name}</td>
                  <td>
                    <code style={{ fontSize: "0.75rem", color: "var(--text-secondary)", background: "var(--bg-canvas)", padding: "4px 8px", borderRadius: "4px" }}>
                      {k.key_prefix}••••••••
                    </code>
                  </td>
                  <td>
                    <div style={{ display: "flex", gap: "4px", flexWrap: "wrap" }}>
                      {k.scopes.map((s, idx) => (
                        <span key={idx} style={{ fontSize: "0.7rem", padding: "2px 6px", background: "var(--primary-light)", color: "var(--primary)", borderRadius: "4px" }}>{s}</span>
                      ))}
                    </div>
                  </td>
                  <td>
                    <span style={{
                      fontSize: "0.75rem", fontWeight: 700, padding: "4px 8px", borderRadius: "12px",
                      background: k.status === "ACTIVE" ? "rgba(34,197,94,0.1)" : "rgba(239,68,68,0.1)",
                      color: k.status === "ACTIVE" ? "var(--success)" : "var(--danger)"
                    }}>
                      {k.status}
                    </span>
                  </td>
                  <td style={{ textAlign: "right" }}>
                    {k.status === "ACTIVE" && (
                      <button onClick={() => handleRevoke(k.id)} className="btn-secondary" style={{ padding: "6px 12px", fontSize: "0.75rem", color: "var(--danger)" }}>
                        <Trash2 style={{ width: "12px", height: "12px" }} /> Revoke
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreateModal && (
        <div className="modal-overlay">
          <div className="modal-content" style={{ maxWidth: "500px" }}>
            <div className="modal-header">
              <h2>{createdRawKey ? "Save Your API Key" : "Generate API Key"}</h2>
              <button className="btn-secondary" style={{ padding: "4px" }} onClick={closeModalAndClearKey}>
                <Trash2 style={{ width: "16px", height: "16px" }} />
              </button>
            </div>
            <div className="modal-body">
              {createdRawKey ? (
                <div>
                  <div style={{ padding: "16px", background: "rgba(245,158,11,0.1)", border: "1px solid rgba(245,158,11,0.3)", borderRadius: "8px", marginBottom: "16px", display: "flex", gap: "12px" }}>
                    <AlertTriangle style={{ width: "24px", height: "24px", color: "var(--warning)", flexShrink: 0 }} />
                    <div style={{ fontSize: "0.875rem", color: "var(--warning-dark, #b45309)", fontWeight: 600 }}>
                      This is the ONLY time you will see this API key. Copy it now and store it securely. We do not store the raw key.
                    </div>
                  </div>
                  <div style={{ display: "flex", gap: "8px", marginBottom: "24px" }}>
                    <input type="text" value={createdRawKey} readOnly className="form-input" style={{ flex: 1, fontFamily: "monospace", color: "var(--primary)" }} />
                    <button className="btn-primary" onClick={handleCopy}>
                      <Copy style={{ width: "16px", height: "16px" }} /> Copy
                    </button>
                  </div>
                  <button className="btn-secondary" style={{ width: "100%", justifyContent: "center" }} onClick={closeModalAndClearKey}>
                    I have saved the key securely
                  </button>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <label className="form-label">Key Name (e.g. Zapier Integration)</label>
                    <input type="text" className="form-input" value={newKeyData.name} onChange={(e) => setNewKeyData({ ...newKeyData, name: e.target.value })} />
                  </div>
                  <div>
                    <label className="form-label">Scopes (comma separated)</label>
                    <input type="text" className="form-input" value={newKeyData.scopes} onChange={(e) => setNewKeyData({ ...newKeyData, scopes: e.target.value })} placeholder="read, write" />
                  </div>
                  <div>
                    <label className="form-label">Expires In (Days)</label>
                    <input type="number" className="form-input" value={newKeyData.expires_in_days} onChange={(e) => setNewKeyData({ ...newKeyData, expires_in_days: parseInt(e.target.value) || 365 })} />
                  </div>
                </div>
              )}
            </div>
            {!createdRawKey && (
              <div className="modal-footer">
                <button className="btn-secondary" onClick={() => setShowCreateModal(false)}>Cancel</button>
                <button className="btn-primary" onClick={handleCreate} disabled={!newKeyData.name}>Generate</button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
