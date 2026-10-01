import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  ShieldCheck,
  KeyRound,
  Users,
  RefreshCw,
  Lock,
  CheckCircle2,
  AlertTriangle,
  X,
  Sliders,
  LogOut,
  Search,
} from "lucide-react";
import {
  api,
  PlatformRole,
  PlatformPermission,
} from "../../services/api";

interface PlatformSecurityViewProps {
  users: any[];
  onRefreshUsers: () => void;
}

export const PlatformSecurityView: React.FC<PlatformSecurityViewProps> = ({
  users,
  onRefreshUsers,
}) => {
  const [roles, setRoles] = useState<PlatformRole[]>([]);
  const [permissions, setPermissions] = useState<PlatformPermission[]>([]);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState<string | null>(null);

  // Modals
  const [selectedUserForRole, setSelectedUserForRole] = useState<any | null>(null);
  const [roleToAssign, setRoleToAssign] = useState<string>("PLATFORM_ADMIN");
  const [roleAssignReason, setRoleAssignReason] = useState<string>("");
  const [assigningRole, setAssigningRole] = useState(false);

  const [selectedUserForRevoke, setSelectedUserForRevoke] = useState<any | null>(null);
  const [revokeReason, setRevokeReason] = useState<string>("");
  const [revokingSessions, setRevokingSessions] = useState(false);

  const [selectedUserForOverride, setSelectedUserForOverride] = useState<any | null>(null);
  const [overridePermCode, setOverridePermCode] = useState<string>("");
  const [overrideGranted, setOverrideGranted] = useState(true);
  const [overrideReason, setOverrideReason] = useState<string>("");
  const [savingOverride, setSavingOverride] = useState(false);

  const [searchUser, setSearchUser] = useState("");

  useEffect(() => {
    loadSecurityData();
  }, []);

  const loadSecurityData = async () => {
    setLoading(true);
    try {
      const [rolesData, permsData] = await Promise.all([
        api.getPlatformRoles(),
        api.getPlatformPermissions(),
      ]);
      setRoles(rolesData);
      setPermissions(permsData);
    } catch (e) {
      console.error("Failed loading platform RBAC metadata:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleAssignRole = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserForRole) return;
    setAssigningRole(true);
    try {
      await api.assignPlatformRole(
        selectedUserForRole.id,
        roleToAssign,
        roleAssignReason || "Administrative role update"
      );
      setMsg(`Assigned role ${roleToAssign} to ${selectedUserForRole.full_name}.`);
      setSelectedUserForRole(null);
      setRoleAssignReason("");
      onRefreshUsers();
    } catch (err: any) {
      alert(err.message || "Failed to assign role.");
    } finally {
      setAssigningRole(false);
    }
  };

  const handleRevokeSessions = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserForRevoke) return;
    setRevokingSessions(true);
    try {
      await api.revokeUserSessions(
        selectedUserForRevoke.id,
        revokeReason || "Security revocation from admin console"
      );
      setMsg(`Successfully revoked all active tokens for ${selectedUserForRevoke.full_name}. Token version incremented.`);
      setSelectedUserForRevoke(null);
      setRevokeReason("");
      onRefreshUsers();
    } catch (err: any) {
      alert(err.message || "Failed to revoke sessions.");
    } finally {
      setRevokingSessions(false);
    }
  };

  const handleSaveOverride = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedUserForOverride || !overridePermCode) return;
    setSavingOverride(true);
    try {
      await api.setPermissionOverride(
        selectedUserForOverride.id,
        overridePermCode,
        overrideGranted,
        overrideReason || "Individual capability override"
      );
      setMsg(`Permission override saved for ${selectedUserForOverride.full_name}.`);
      setSelectedUserForOverride(null);
      setOverrideReason("");
      onRefreshUsers();
    } catch (err: any) {
      alert(err.message || "Failed to set override.");
    } finally {
      setSavingOverride(false);
    }
  };

  const filteredUsers = users.filter((u) => {
    if (!searchUser) return true;
    const q = searchUser.toLowerCase();
    return (
      u.full_name?.toLowerCase().includes(q) ||
      u.email?.toLowerCase().includes(q) ||
      (u.platform_role && u.platform_role.toLowerCase().includes(q))
    );
  });

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
            <ShieldAlert style={{ width: "22px", height: "22px", color: "var(--primary)" }} />
            Platform Security, RBAC & Session Revocation
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Enforce granular Platform RBAC, monitor token versioning, and execute immediate session invalidation
          </p>
        </div>

        <button onClick={() => { loadSecurityData(); onRefreshUsers(); }} className="btn-secondary" style={{ fontSize: "0.8125rem" }}>
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

      {/* Role Hierarchy Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: "16px" }}>
        {roles.map((r) => {
          const isSuper = r.code === "SUPER_ADMIN";
          return (
            <div
              key={r.id}
              className="card"
              style={{
                padding: "16px",
                border: isSuper ? "1px solid var(--primary)" : "1px solid var(--border-subtle)",
                background: isSuper ? "rgba(99, 102, 241, 0.04)" : "var(--bg-surface)",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
                <span style={{ fontSize: "0.875rem", fontWeight: 800, color: isSuper ? "var(--primary)" : "var(--text-primary)" }}>
                  {r.name}
                </span>
                <span
                  style={{
                    fontSize: "0.6875rem",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "4px",
                    background: "var(--bg-canvas)",
                    border: "1px solid var(--border-subtle)",
                    color: "var(--text-secondary)",
                  }}
                >
                  Level {r.hierarchy_level}
                </span>
              </div>
              <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginBottom: "12px", minHeight: "36px" }}>
                {r.description || "Platform access role with calibrated authority boundaries."}
              </p>
              <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: "10px" }}>
                <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-muted)", textTransform: "uppercase" }}>
                  Permissions ({r.permissions?.length || 0})
                </span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "4px", marginTop: "6px" }}>
                  {r.permissions?.slice(0, 4).map((p) => (
                    <span
                      key={p.id}
                      style={{
                        fontSize: "0.625rem",
                        fontWeight: 600,
                        padding: "2px 6px",
                        borderRadius: "4px",
                        background: p.risk_level === "CRITICAL" ? "#fee2e2" : "var(--bg-canvas)",
                        color: p.risk_level === "CRITICAL" ? "#991b1b" : "var(--text-secondary)",
                        border: "1px solid var(--border-subtle)",
                      }}
                      title={p.description || p.name}
                    >
                      {p.code}
                    </span>
                  ))}
                  {(r.permissions?.length || 0) > 4 && (
                    <span style={{ fontSize: "0.625rem", color: "var(--text-muted)", alignSelf: "center" }}>
                      +{(r.permissions?.length || 0) - 4} more
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Users & Session Control Table */}
      <div className="table-container">
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
          <div>
            <h3 style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>
              Platform Operators & Session Security Registry ({filteredUsers.length})
            </h3>
            <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
              Token version tracking, platform role elevation, and instant JWT revocation
            </span>
          </div>

          <div style={{ position: "relative", width: "280px" }}>
            <Search style={{ width: "15px", height: "15px", color: "var(--text-muted)", position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
            <input
              type="text"
              value={searchUser}
              onChange={(e) => setSearchUser(e.target.value)}
              placeholder="Search operator by name, email, or role..."
              className="input-text"
              style={{ paddingLeft: "32px", fontSize: "0.75rem" }}
            />
          </div>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th style={{ paddingLeft: "20px" }}>User</th>
              <th>Platform Role</th>
              <th>Tenant Role</th>
              <th>Token Version</th>
              <th>Status</th>
              <th style={{ textAlign: "right", paddingRight: "20px" }}>Security Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredUsers.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ textAlign: "center", padding: "36px 0", color: "var(--text-muted)" }}>
                  No users found.
                </td>
              </tr>
            ) : (
              filteredUsers.map((u) => (
                <tr key={u.id}>
                  <td style={{ paddingLeft: "20px" }}>
                    <p style={{ fontWeight: 700, color: "var(--text-primary)" }}>{u.full_name}</p>
                    <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>{u.email}</p>
                  </td>
                  <td>
                    {u.platform_role ? (
                      <span className="badge" style={{ background: "rgba(99, 102, 241, 0.1)", color: "#4f46e5", border: "1px solid rgba(99, 102, 241, 0.3)", fontWeight: 700 }}>
                        {u.platform_role}
                      </span>
                    ) : (
                      <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>None (Tenant Scoped)</span>
                    )}
                  </td>
                  <td>
                    <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                      {u.tenant_role || "NONE"}
                    </span>
                  </td>
                  <td>
                    <span style={{ fontFamily: "monospace", fontSize: "0.8125rem", fontWeight: 700, padding: "3px 8px", borderRadius: "4px", background: "var(--bg-canvas)", border: "1px solid var(--border-subtle)" }}>
                      v{u.token_version || 1}
                    </span>
                  </td>
                  <td>
                    <span className={`badge ${u.status === "ACTIVE" ? "badge-open" : "badge-lost"}`}>
                      {u.status}
                    </span>
                  </td>
                  <td style={{ textAlign: "right", paddingRight: "20px" }}>
                    <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "6px" }}>
                      <button
                        onClick={() => {
                          setSelectedUserForRole(u);
                          setRoleToAssign(u.platform_role || "PLATFORM_ADMIN");
                        }}
                        className="btn-secondary"
                        style={{ fontSize: "0.6875rem", padding: "5px 10px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                        title="Assign or change Platform Role"
                      >
                        <ShieldCheck style={{ width: "12px", height: "12px" }} /> Role
                      </button>

                      <button
                        onClick={() => {
                          setSelectedUserForOverride(u);
                          setOverridePermCode(permissions[0]?.code || "");
                        }}
                        className="btn-secondary"
                        style={{ fontSize: "0.6875rem", padding: "5px 10px", display: "inline-flex", alignItems: "center", gap: "4px" }}
                        title="Override specific permissions"
                      >
                        <Sliders style={{ width: "12px", height: "12px" }} /> Override
                      </button>

                      <button
                        onClick={() => setSelectedUserForRevoke(u)}
                        className="btn-secondary"
                        style={{
                          fontSize: "0.6875rem",
                          padding: "5px 10px",
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          color: "#dc2626",
                          borderColor: "#fca5a5",
                        }}
                        title="Revoke all active tokens immediately"
                      >
                        <LogOut style={{ width: "12px", height: "12px" }} /> Revoke
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* MODAL 1: Assign Platform Role */}
      {selectedUserForRole && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div className="card" style={{ width: "100%", maxWidth: "460px", background: "var(--bg-surface)", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
            <div style={{ padding: "20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)" }}>
                Assign Platform Role
              </h3>
              <button onClick={() => setSelectedUserForRole(null)} className="btn-secondary" style={{ padding: "6px" }}>
                <X style={{ width: "16px", height: "16px" }} />
              </button>
            </div>
            <form onSubmit={handleAssignRole} style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Target User</span>
                <p style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "0.9375rem" }}>{selectedUserForRole.full_name} ({selectedUserForRole.email})</p>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Platform Role</label>
                <select value={roleToAssign} onChange={(e) => setRoleToAssign(e.target.value)} className="select-dropdown" style={{ width: "100%" }}>
                  {roles.map((r) => (
                    <option key={r.id} value={r.code}>{r.name} ({r.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Audit Justification Reason</label>
                <textarea
                  value={roleAssignReason}
                  onChange={(e) => setRoleAssignReason(e.target.value)}
                  placeholder="Reason for role assignment..."
                  className="input-text"
                  rows={2}
                  style={{ width: "100%", fontSize: "0.75rem" }}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button type="button" onClick={() => setSelectedUserForRole(null)} className="btn-secondary" style={{ fontSize: "0.75rem" }}>Cancel</button>
                <button type="submit" disabled={assigningRole} className="btn-primary" style={{ fontSize: "0.75rem" }}>
                  {assigningRole ? "Saving..." : "Save Role Assignment"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: Revoke User Sessions */}
      {selectedUserForRevoke && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div className="card" style={{ width: "100%", maxWidth: "460px", background: "var(--bg-surface)", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
            <div style={{ padding: "20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", background: "rgba(239, 68, 68, 0.05)" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#dc2626" }}>
                <LogOut style={{ width: "18px", height: "18px" }} />
                <h3 style={{ fontSize: "1rem", fontWeight: 800 }}>Revoke All User Sessions</h3>
              </div>
              <button onClick={() => setSelectedUserForRevoke(null)} className="btn-secondary" style={{ padding: "6px" }}>
                <X style={{ width: "16px", height: "16px" }} />
              </button>
            </div>
            <form onSubmit={handleRevokeSessions} style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div style={{ padding: "10px 14px", borderRadius: "8px", background: "#fee2e2", color: "#991b1b", fontSize: "0.75rem" }}>
                This will increment <strong>{selectedUserForRevoke.full_name}</strong>'s token version from v{selectedUserForRevoke.token_version || 1} to v{(selectedUserForRevoke.token_version || 1) + 1}, instantly terminating all active desktop, mobile, and API sessions.
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Revocation Reason</label>
                <textarea
                  value={revokeReason}
                  onChange={(e) => setRevokeReason(e.target.value)}
                  placeholder="e.g. Lost device, suspicious IP detected, security offboarding..."
                  className="input-text"
                  rows={2}
                  style={{ width: "100%", fontSize: "0.75rem" }}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button type="button" onClick={() => setSelectedUserForRevoke(null)} className="btn-secondary" style={{ fontSize: "0.75rem" }}>Cancel</button>
                <button type="submit" disabled={revokingSessions} className="btn-primary" style={{ fontSize: "0.75rem", background: "#dc2626", border: "none" }}>
                  {revokingSessions ? "Revoking..." : "Revoke All Sessions Now"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 3: Permission Override */}
      {selectedUserForOverride && (
        <div style={{ position: "fixed", inset: 0, backgroundColor: "rgba(15, 23, 42, 0.75)", backdropFilter: "blur(4px)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 1000, padding: "20px" }}>
          <div className="card" style={{ width: "100%", maxWidth: "460px", background: "var(--bg-surface)", borderRadius: "16px", overflow: "hidden", border: "1px solid var(--border-subtle)" }}>
            <div style={{ padding: "20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)" }}>
                User Capability Override
              </h3>
              <button onClick={() => setSelectedUserForOverride(null)} className="btn-secondary" style={{ padding: "6px" }}>
                <X style={{ width: "16px", height: "16px" }} />
              </button>
            </div>
            <form onSubmit={handleSaveOverride} style={{ padding: "20px", display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Target User</span>
                <p style={{ fontWeight: 800, color: "var(--text-primary)", fontSize: "0.9375rem" }}>{selectedUserForOverride.full_name}</p>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Permission Code</label>
                <select value={overridePermCode} onChange={(e) => setOverridePermCode(e.target.value)} className="select-dropdown" style={{ width: "100%" }}>
                  {permissions.map((p) => (
                    <option key={p.id} value={p.code}>{p.name} ({p.code})</option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Status</label>
                <select value={overrideGranted ? "true" : "false"} onChange={(e) => setOverrideGranted(e.target.value === "true")} className="select-dropdown" style={{ width: "100%" }}>
                  <option value="true">Grant Permission Explicitly</option>
                  <option value="false">Deny / Revoke Permission Explicitly</option>
                </select>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Override Reason</label>
                <textarea
                  value={overrideReason}
                  onChange={(e) => setOverrideReason(e.target.value)}
                  placeholder="Reason for special grant..."
                  className="input-text"
                  rows={2}
                  style={{ width: "100%", fontSize: "0.75rem" }}
                  required
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "8px" }}>
                <button type="button" onClick={() => setSelectedUserForOverride(null)} className="btn-secondary" style={{ fontSize: "0.75rem" }}>Cancel</button>
                <button type="submit" disabled={savingOverride} className="btn-primary" style={{ fontSize: "0.75rem" }}>
                  {savingOverride ? "Saving..." : "Apply Override"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
