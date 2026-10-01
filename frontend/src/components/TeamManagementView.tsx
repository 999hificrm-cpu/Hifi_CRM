import React, { useState, useEffect } from "react";
import { api, TelecallerUser, Lead } from "../services/api";
import {
  Users,
  UserPlus,
  PhoneCall,
  CheckCircle2,
  AlertCircle,
  Search,
  X,
  Plus,
  CheckSquare,
  Square,
  Sparkles,
  ArrowRight,
  Shield,
  Phone,
  Mail,
  Edit2,
  FileText,
  Save
} from "lucide-react";
import { format10DigitPhone, cleanPhoneInput } from "../utils/phoneHelper";
import jsPDF from "jspdf";
import autoTable from "jspdf-autotable";

interface TeamManagementViewProps {
  onNavigateToLeads?: () => void;
}

export const TeamManagementView: React.FC<TeamManagementViewProps> = ({ onNavigateToLeads }) => {
  const [telecallers, setTelecallers] = useState<TelecallerUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [successBanner, setSuccessBanner] = useState<string | null>(null);

  // Add Telecaller Modal State
  const [showAddModal, setShowAddModal] = useState(false);
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [savingPassword, setSavingPassword] = useState(false);
  const [copiedEmailId, setCopiedEmailId] = useState<string | null>(null);

  const handleCopyEmail = (email: string, id: string) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmailId(id);
    setTimeout(() => setCopiedEmailId(null), 2000);
  };
  const [phone, setPhone] = useState("");
  const [creating, setCreating] = useState(false);
  const [addError, setAddError] = useState<string | null>(null);

  // Assign Leads Modal State
  const [selectedTelecaller, setSelectedTelecaller] = useState<TelecallerUser | null>(null);
  const [availableLeads, setAvailableLeads] = useState<Lead[]>([]);
  const [loadingLeads, setLoadingLeads] = useState(false);
  const [selectedLeadIds, setSelectedLeadIds] = useState<Set<string>>(new Set());
  const [leadsSearch, setLeadsSearch] = useState("");
  const [assigning, setAssigning] = useState(false);

  // Targets Editing State
  const [editingTargetId, setEditingTargetId] = useState<string | null>(null);
  const [tempTargets, setTempTargets] = useState<{ calls: number; connects: number; conversions: number }>({ calls: 0, connects: 0, conversions: 0 });

  const handleEditTargets = (tc: TelecallerUser) => {
    setEditingTargetId(tc.id);
    const tg = tc.telecaller_targets || { calls: 0, connects: 0, conversions: 0 };
    setTempTargets({ calls: tg.calls || 0, connects: tg.connects || 0, conversions: tg.conversions || 0 });
  };

  const handleSaveTargets = async (tc: TelecallerUser) => {
    try {
      await api.updateUser(tc.id, { telecaller_targets: tempTargets });
      setSuccessBanner(`Updated targets for ${tc.full_name}`);
      setTimeout(() => setSuccessBanner(null), 3000);
      setEditingTargetId(null);
      loadTelecallers();
    } catch (err: any) {
      alert(err.message || "Failed to update targets.");
    }
  };

  const generatePDFReport = () => {
    const doc = new jsPDF();
    doc.setFontSize(18);
    doc.text("Telecaller Performance Report", 14, 22);
    doc.setFontSize(11);
    doc.text(`Generated on: ${new Date().toLocaleDateString()}`, 14, 30);

    const tableData = telecallers.map(tc => {
      const tg = tc.telecaller_targets || { calls: 0, connects: 0, conversions: 0 };
      return [
        tc.full_name,
        tc.email,
        tc.assigned_leads_count,
        tg.calls,
        tg.connects,
        tg.conversions,
        tc.status
      ];
    });

    autoTable(doc, {
      startY: 35,
      head: [["Telecaller", "Email", "Assigned Leads", "Target Calls", "Target Connects", "Target Conversions", "Status"]],
      body: tableData,
      theme: "grid",
      headStyles: { fillColor: [79, 70, 229] }
    });

    doc.save(`telecaller-report-${new Date().toISOString().split('T')[0]}.pdf`);
  };

  useEffect(() => {
    loadTelecallers();
  }, []);

  const loadTelecallers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getTelecallers();
      setTelecallers(data);
    } catch (err: any) {
      setError(err.message || "Failed to load telecallers");
    } finally {
      setLoading(false);
    }
  };

  const handleCreateTelecaller = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!fullName.trim() || !email.trim() || !password.trim()) {
      setAddError("Please fill out full name, email, and password.");
      return;
    }
    setCreating(true);
    setAddError(null);
    try {
      await api.createUser({
        full_name: fullName.trim(),
        email: email.trim().toLowerCase(),
        password: password.trim(),
        phone: phone ? phone.replace(/\D/g, "") : undefined,
        tenant_role: "TELECALLER",
      });

      setSuccessBanner(`Successfully added telecaller ${fullName.trim()}`);
      setTimeout(() => setSuccessBanner(null), 4500);

      // Reset form and reload
      setFullName("");
      setEmail("");
      setPassword("");
      setPhone("");
      setShowAddModal(false);
      loadTelecallers();
    } catch (err: any) {
      setAddError(err.message || "Failed to create telecaller");
    } finally {
      setCreating(false);
    }
  };

  const handleOpenAssignModal = async (tc: TelecallerUser) => {
    setSelectedTelecaller(tc);
    setSelectedLeadIds(new Set());
    setLeadsSearch("");
    setLoadingLeads(true);
    try {
      const allLeads = await api.getAssignableLeads(tc.id);
      setAvailableLeads(allLeads);
    } catch (err) {
      console.error(err);
    } finally {
      setLoadingLeads(false);
    }
  };

  const handleToggleLead = (leadId: string) => {
    setSelectedLeadIds((prev) => {
      const next = new Set(prev);
      if (next.has(leadId)) {
        next.delete(leadId);
      } else {
        next.add(leadId);
      }
      return next;
    });
  };

  const handleSelectBatch = (count: number) => {
    const unassignedOrFiltered = availableLeads
      .filter((l) => {
        if (!leadsSearch) return true;
        const q = leadsSearch.toLowerCase();
        return (
          l.title.toLowerCase().includes(q) ||
          (l.company_name && l.company_name.toLowerCase().includes(q))
        );
      })
      .slice(0, count);

    setSelectedLeadIds(new Set(unassignedOrFiltered.map((l) => l.id)));
  };

  const handleExecuteBatchAssign = async () => {
    if (!selectedTelecaller || selectedLeadIds.size === 0) return;
    setAssigning(true);
    try {
      const leadIdList = Array.from(selectedLeadIds);
      const res = await api.batchAssignLeads(leadIdList, selectedTelecaller.id);

      setSuccessBanner(res.message || `Successfully assigned ${leadIdList.length} leads to ${selectedTelecaller.full_name}`);
      setTimeout(() => setSuccessBanner(null), 5000);

      setSelectedTelecaller(null);
      setSelectedLeadIds(new Set());
      loadTelecallers();
    } catch (err: any) {
      alert(err.message || "Failed to assign leads");
    } finally {
      setAssigning(false);
    }
  };

  const totalAssignedLeads = telecallers.reduce((acc, curr) => acc + (curr.assigned_leads_count || 0), 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Top Banner & Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
              Team & Telecallers
            </h2>
            <span style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "999px",
              backgroundColor: "var(--primary-light)",
              color: "var(--primary)",
              border: "1px solid var(--primary-border)"
            }}>
              Org Admin Authority
            </span>
          </div>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Assign telecallers to specific leads. Telecallers only see leads explicitly assigned by you.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          {onNavigateToLeads && (
            <button
              onClick={onNavigateToLeads}
              className="btn-secondary"
              style={{ fontSize: "0.8125rem" }}
            >
              Go to Leads Table
              <ArrowRight style={{ width: "14px", height: "14px" }} />
            </button>
          )}

          <button
            onClick={generatePDFReport}
            className="btn-secondary"
            style={{ fontSize: "0.8125rem", color: "var(--indigo)" }}
            title="Download PDF Report"
          >
            <FileText style={{ width: "15px", height: "15px" }} />
            Download Report
          </button>

          <button
            onClick={() => setShowAddModal(true)}
            className="btn-primary"
            style={{ fontSize: "0.8125rem" }}
            id="btn-add-telecaller"
          >
            <UserPlus style={{ width: "15px", height: "15px" }} />
            Add Telecaller
          </button>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successBanner && (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "10px 16px",
            borderRadius: "8px",
            background: "var(--emerald-light)",
            border: "1px solid var(--emerald-border)",
            color: "var(--emerald-dark)",
            fontSize: "0.8125rem",
            fontWeight: 600,
          }}
        >
          <CheckCircle2 style={{ width: "16px", height: "16px", color: "var(--emerald)" }} />
          <span>{successBanner}</span>
        </div>
      )}

      {/* KPI Cards */}
      <div className="grid-cols-kpi">
        <div className="stat-card stat-card-accent-indigo">
          <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
            Total Telecallers
          </p>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "4px" }}>
            {telecallers.length}
          </h3>
          <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Scoped users on Calling Desk
          </p>
        </div>

        <div className="stat-card stat-card-accent-emerald">
          <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
            Assigned Leads
          </p>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--emerald-dark)", marginTop: "4px" }}>
            {totalAssignedLeads}
          </h3>
          <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Active leads in telecaller queues
          </p>
        </div>

        <div className="stat-card stat-card-accent-amber">
          <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
            Data Protection
          </p>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--amber-dark)", marginTop: "4px" }}>
            100%
          </h3>
          <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Strict lead scoping & phone masking active
          </p>
        </div>

        <div className="stat-card stat-card-accent-rose">
          <p style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
            Avg Queue Size
          </p>
          <h3 style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--rose-dark)", marginTop: "4px" }}>
            {telecallers.length > 0 ? (totalAssignedLeads / telecallers.length).toFixed(0) : 0}
          </h3>
          <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px" }}>
            Leads per telecaller desk
          </p>
        </div>
      </div>

      {/* Telecallers Table */}
      <div className="card" style={{ padding: "0", overflow: "hidden" }}>
        <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <div>
            <h3 style={{ fontSize: "0.9375rem", fontWeight: 700, color: "var(--text-primary)" }}>
              Organization Telecallers
            </h3>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
              Each telecaller's dashboard displays ONLY the leads explicitly assigned by you.
            </p>
          </div>
          <button onClick={loadTelecallers} className="btn-secondary" style={{ fontSize: "0.75rem", padding: "4px 10px" }}>
            Refresh
          </button>
        </div>

        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ paddingLeft: "20px" }}>Telecaller Member</th>
                <th>Contact Details</th>
                <th>Role & Scope</th>
                <th>Daily Targets</th>
                <th>Assigned Leads Count</th>
                <th>Status</th>
                <th style={{ textAlign: "right", paddingRight: "20px" }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "40px", color: "var(--text-muted)" }}>
                    Loading telecallers...
                  </td>
                </tr>
              ) : telecallers.length === 0 ? (
                <tr>
                  <td colSpan={6} style={{ textAlign: "center", padding: "48px 20px" }}>
                    <Users style={{ width: "36px", height: "36px", color: "var(--text-muted)", margin: "0 auto 12px auto" }} />
                    <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                      No telecallers added yet
                    </p>
                    <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px", maxWidth: "420px", marginInline: "auto" }}>
                      Create a telecaller user so they can log into the Calling Desk and work on the leads you select for them.
                    </p>
                    <button
                      onClick={() => setShowAddModal(true)}
                      className="btn-primary"
                      style={{ marginTop: "16px", fontSize: "0.8125rem" }}
                    >
                      <UserPlus style={{ width: "14px", height: "14px" }} />
                      Add Your First Telecaller
                    </button>
                  </td>
                </tr>
              ) : (
                telecallers.map((tc) => (
                  <tr key={tc.id}>
                    <td style={{ paddingLeft: "20px" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                        <div style={{
                          width: "32px",
                          height: "32px",
                          borderRadius: "50%",
                          background: "var(--primary-light)",
                          color: "var(--primary)",
                          fontWeight: 700,
                          fontSize: "0.8125rem",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          border: "1px solid var(--primary-border)"
                        }}>
                          {tc.full_name ? tc.full_name.charAt(0).toUpperCase() : "T"}
                        </div>
                        <div>
                          <p style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.8125rem" }}>
                            {tc.full_name}
                          </p>
                          <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                            ID: {tc.id.substring(0, 8)}...
                          </p>
                        </div>
                      </div>
                    </td>

                    <td>
                      <div style={{ fontSize: "0.75rem", display: "flex", flexDirection: "column", gap: "2px" }}>
                        <span 
                          onClick={() => handleCopyEmail(tc.email, tc.id)}
                          style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--text-secondary)", cursor: "pointer" }}
                          title="Copy email to clipboard"
                        >
                          <Mail style={{ width: "12px", height: "12px", color: "var(--text-muted)" }} />
                          <span style={{ textDecoration: "underline", textDecorationStyle: "dotted" }}>
                            {copiedEmailId === tc.id ? "Copied!" : tc.email}
                          </span>
                        </span>
                        {tc.phone && (
                          <span style={{ display: "flex", alignItems: "center", gap: "5px", color: "var(--text-secondary)" }}>
                            <Phone style={{ width: "12px", height: "12px", color: "var(--text-muted)" }} />
                            {format10DigitPhone(tc.phone)}
                          </span>
                        )}
                      </div>
                    </td>

                    <td>
                      <span className="badge badge-masked" style={{ fontSize: "0.6875rem", fontWeight: 700 }}>
                        <Shield style={{ width: "11px", height: "11px" }} />
                        TELECALLER (SCOPED)
                      </span>
                    </td>

                    <td>
                      {editingTargetId === tc.id ? (
                        <div style={{ display: "flex", flexDirection: "column", gap: "6px", fontSize: "0.75rem" }}>
                          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                            <span>Calls:</span>
                            <input 
                              type="number" 
                              value={tempTargets.calls} 
                              onChange={(e) => setTempTargets({...tempTargets, calls: parseInt(e.target.value) || 0})}
                              style={{ width: "40px", padding: "2px" }}
                            />
                          </div>
                          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                            <span>Conn:</span>
                            <input 
                              type="number" 
                              value={tempTargets.connects} 
                              onChange={(e) => setTempTargets({...tempTargets, connects: parseInt(e.target.value) || 0})}
                              style={{ width: "40px", padding: "2px" }}
                            />
                          </div>
                          <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                            <span>Conv:</span>
                            <input 
                              type="number" 
                              value={tempTargets.conversions} 
                              onChange={(e) => setTempTargets({...tempTargets, conversions: parseInt(e.target.value) || 0})}
                              style={{ width: "40px", padding: "2px" }}
                            />
                          </div>
                          <div style={{ display: "flex", gap: "4px" }}>
                            <button onClick={() => handleSaveTargets(tc)} style={{ color: "var(--emerald)", cursor: "pointer", background: "none", border: "none" }} title="Save Targets">
                              <Save style={{ width: "14px", height: "14px" }} />
                            </button>
                            <button onClick={() => setEditingTargetId(null)} style={{ color: "var(--text-muted)", cursor: "pointer", background: "none", border: "none" }} title="Cancel">
                              <X style={{ width: "14px", height: "14px" }} />
                            </button>
                          </div>
                        </div>
                      ) : (
                        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                          <div style={{ display: "flex", flexDirection: "column" }}>
                            <span>📞 Calls: <strong>{tc.telecaller_targets?.calls || 0}</strong></span>
                            <span>✅ Conn: <strong>{tc.telecaller_targets?.connects || 0}</strong></span>
                            <span>🎯 Conv: <strong>{tc.telecaller_targets?.conversions || 0}</strong></span>
                            {/* Missing target reminder if they haven't made calls today */}
                            {(!tc.telecaller_targets?.calls || tc.telecaller_targets?.calls === 0) && (
                              <span style={{ color: "var(--amber-dark)", fontSize: "0.6875rem", display: "flex", alignItems: "center", gap: "2px", marginTop: "2px" }}>
                                <AlertCircle style={{ width: "10px", height: "10px" }} /> No Target
                              </span>
                            )}
                          </div>
                          <button onClick={() => handleEditTargets(tc)} style={{ color: "var(--indigo)", cursor: "pointer", background: "none", border: "none", padding: "4px" }} title="Edit Targets">
                            <Edit2 style={{ width: "14px", height: "14px" }} />
                          </button>
                        </div>
                      )}
                    </td>

                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                        <span style={{
                          display: "inline-block",
                          padding: "3px 10px",
                          borderRadius: "999px",
                          fontSize: "0.75rem",
                          fontWeight: 800,
                          fontFamily: "monospace",
                          background: tc.assigned_leads_count > 0 ? "var(--emerald-light)" : "var(--bg-surface-subtle)",
                          color: tc.assigned_leads_count > 0 ? "var(--emerald-dark)" : "var(--text-muted)",
                          border: `1px solid ${tc.assigned_leads_count > 0 ? "var(--emerald-border)" : "var(--border-subtle)"}`
                        }}>
                          {tc.assigned_leads_count} Leads
                        </span>
                        {tc.assigned_leads_count === 0 && (
                          <span style={{ fontSize: "0.6875rem", color: "var(--amber-dark)", fontWeight: 600 }}>
                            Empty Queue
                          </span>
                        )}
                      </div>
                    </td>

                    <td>
                      <span className="badge badge-success" style={{ fontSize: "0.6875rem" }}>
                        {tc.status || "ACTIVE"}
                      </span>
                    </td>

                    <td style={{ textAlign: "right", paddingRight: "20px" }}>
                      <button
                        onClick={() => handleOpenAssignModal(tc)}
                        className="btn-primary"
                        style={{ fontSize: "0.75rem", padding: "5px 12px" }}
                      >
                        <PhoneCall style={{ width: "12px", height: "12px" }} />
                        Assign Leads
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* MODAL 1: ADD NEW TELECALLER */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "480px" }}>
            <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <UserPlus style={{ width: "18px", height: "18px", color: "var(--primary)" }} />
                <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  Add New Telecaller
                </h3>
              </div>
              <button
                onClick={() => setShowAddModal(false)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X style={{ width: "18px", height: "18px" }} />
              </button>
            </div>

            <form onSubmit={handleCreateTelecaller} style={{ padding: "20px 24px", display: "flex", flexDirection: "column", gap: "16px" }}>
              {addError && (
                <div style={{ padding: "10px", borderRadius: "6px", background: "var(--rose-light)", color: "var(--rose-dark)", border: "1px solid var(--rose-border)", fontSize: "0.75rem", display: "flex", alignItems: "center", gap: "6px" }}>
                  <AlertCircle style={{ width: "14px", height: "14px", flexShrink: 0 }} />
                  <span>{addError}</span>
                </div>
              )}

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Full Name *
                </label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Rahul Sharma"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  className="input-text"
                  id="input-telecaller-name"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Email Address *
                </label>
                <input
                  type="email"
                  required
                  placeholder="rahul@organization.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="input-text"
                  id="input-telecaller-email"
                />
                <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "3px" }}>
                  Used to login to the Calling Desk.
                </p>
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Login Password *
                </label>
                <input
                  type="password"
                  required
                  placeholder="Minimum 8 characters"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-text"
                  id="input-telecaller-password"
                />
              </div>

              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Phone Number (Optional - 10 Digits)
                </label>
                <input
                  type="text"
                  placeholder="9876543210"
                  maxLength={10}
                  value={phone}
                  onChange={(e) => setPhone(cleanPhoneInput(e.target.value))}
                  className="input-text"
                  id="input-telecaller-phone"
                />
              </div>

              <div style={{
                padding: "12px",
                borderRadius: "8px",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                fontSize: "0.75rem",
                color: "var(--text-secondary)"
              }}>
                <strong>Security Guard:</strong> Telecallers receive masked phone numbers & emails, and can only view leads you assign to them.
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary"
                  disabled={creating}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={creating}
                  id="btn-submit-telecaller"
                >
                  {creating ? "Creating..." : "Create Telecaller"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL 2: ASSIGN LEADS TO TELECALLER */}
      {selectedTelecaller && (
        <div className="modal-overlay" onClick={() => setSelectedTelecaller(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ maxWidth: "680px", maxHeight: "88vh" }}>
            <div style={{ padding: "18px 24px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div>
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <PhoneCall style={{ width: "18px", height: "18px", color: "var(--primary)" }} />
                  <h3 style={{ fontSize: "1.05rem", fontWeight: 800, color: "var(--text-primary)" }}>
                    Assign Leads to {selectedTelecaller.full_name}
                  </h3>
                </div>
                <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                  Currently has <strong>{selectedTelecaller.assigned_leads_count}</strong> leads assigned. Select leads below to dispatch to their queue.
                </p>
              </div>
              <button
                onClick={() => setSelectedTelecaller(null)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X style={{ width: "18px", height: "18px" }} />
              </button>
            </div>

            {/* Quick Batch Select Buttons */}
            <div style={{ padding: "12px 24px", background: "var(--bg-surface-subtle)", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "10px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)" }}>Quick Select:</span>
                <button
                  type="button"
                  onClick={() => handleSelectBatch(10)}
                  className="btn-secondary"
                  style={{ fontSize: "0.6875rem", padding: "3px 8px" }}
                >
                  First 10
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectBatch(20)}
                  className="btn-secondary"
                  style={{ fontSize: "0.6875rem", padding: "3px 8px" }}
                >
                  First 20
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectBatch(50)}
                  className="btn-secondary"
                  style={{ fontSize: "0.6875rem", padding: "3px 8px" }}
                >
                  First 50
                </button>
                <button
                  type="button"
                  onClick={() => handleSelectBatch(availableLeads.length)}
                  className="btn-secondary"
                  style={{ fontSize: "0.6875rem", padding: "3px 8px" }}
                >
                  All ({availableLeads.length})
                </button>
              </div>

              <div style={{ position: "relative", minWidth: "180px" }}>
                <Search style={{ width: "13px", height: "13px", color: "var(--text-muted)", position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
                <input
                  type="text"
                  placeholder="Filter leads..."
                  value={leadsSearch}
                  onChange={(e) => setLeadsSearch(e.target.value)}
                  className="input-text"
                  style={{ paddingLeft: "30px", fontSize: "0.75rem", paddingBlock: "4px" }}
                />
              </div>
            </div>

            {/* Leads Selectable List */}
            <div style={{ overflowY: "auto", flex: 1, padding: "12px 24px", display: "flex", flexDirection: "column", gap: "8px" }}>
              {loadingLeads ? (
                <div style={{ textAlign: "center", padding: "36px", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                  Loading leads...
                </div>
              ) : availableLeads.length === 0 ? (
                <div style={{ textAlign: "center", padding: "36px", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                  No leads available in this organization. Create or import leads first.
                </div>
              ) : (
                availableLeads
                  .filter((l) => {
                    if (!leadsSearch) return true;
                    const q = leadsSearch.toLowerCase();
                    return (
                      l.title.toLowerCase().includes(q) ||
                      (l.company_name && l.company_name.toLowerCase().includes(q)) ||
                      (l.contact_name && l.contact_name.toLowerCase().includes(q))
                    );
                  })
                  .map((lead) => {
                    const isSelected = selectedLeadIds.has(lead.id);
                    const isAlreadyOwner = lead.owner_id === selectedTelecaller.id;
                    return (
                      <div
                        key={lead.id}
                        onClick={() => handleToggleLead(lead.id)}
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          padding: "10px 14px",
                          borderRadius: "8px",
                          border: `1px solid ${isSelected ? "var(--primary-border)" : "var(--border-subtle)"}`,
                          background: isSelected ? "var(--primary-light)" : "var(--bg-surface)",
                          cursor: "pointer",
                          transition: "all 0.15s ease",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleToggleLead(lead.id)}
                            onClick={(e) => e.stopPropagation()}
                            style={{ accentColor: "var(--primary)", width: "16px", height: "16px", cursor: "pointer" }}
                          />
                          <div>
                            <p style={{ fontWeight: 700, fontSize: "0.8125rem", color: "var(--text-primary)" }}>
                              {lead.title}
                            </p>
                            <p style={{ fontSize: "0.6875rem", color: "var(--text-secondary)" }}>
                              {lead.company_name || "Independent"} &bull; {lead.contact_name || "No contact"}
                            </p>
                          </div>
                        </div>

                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          {isAlreadyOwner && (
                            <span className="badge badge-success" style={{ fontSize: "0.625rem" }}>
                              Already Assigned
                            </span>
                          )}
                          <span className="badge" style={{ fontSize: "0.625rem", background: `${lead.stage?.color || "#4f46e5"}15`, color: lead.stage?.color || "var(--primary)" }}>
                            {lead.stage?.name || "Stage"}
                          </span>
                        </div>
                      </div>
                    );
                  })
              )}
            </div>

            {/* Modal Footer */}
            <div style={{ padding: "16px 24px", borderTop: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", background: "var(--bg-surface-subtle)" }}>
              <span style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {selectedLeadIds.size} leads selected
              </span>

              <div style={{ display: "flex", gap: "10px" }}>
                <button
                  type="button"
                  onClick={() => setSelectedTelecaller(null)}
                  className="btn-secondary"
                  disabled={assigning}
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={handleExecuteBatchAssign}
                  className="btn-primary"
                  disabled={assigning || selectedLeadIds.size === 0}
                  id="btn-confirm-assign-leads"
                >
                  {assigning ? "Assigning..." : `Assign ${selectedLeadIds.size} Leads`}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
