import React, { useState, useEffect } from "react";
import { Lead, PipelineStage, TelecallerUser, api } from "../services/api";
import { openGmail } from "../utils/mailHelper";
// import { EmailComposeModal } from "./EmailComposeModal";
import { format10DigitPhone, getCallUrl } from "../utils/phoneHelper";
import {
  Search,
  Phone,
  Mail,
  Flame,
  ExternalLink,
  Plus,
  UserCheck,
  CheckCircle2,
  X,
  Users,
  Building2,
  Briefcase,
  Target
} from "lucide-react";

interface LeadsTableProps {
  leads: Lead[];
  stages: PipelineStage[];
  onSelectLead: (lead: Lead) => void;
  onMoveStage: (leadId: string, stageId: string) => void;
  onNewLeadClick?: () => void;
  onRefresh?: () => void;
}

export const LeadsTable: React.FC<LeadsTableProps> = ({
  leads,
  stages,
  onSelectLead,
  onMoveStage,
  onNewLeadClick,
  onRefresh,
}) => {
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedStage, setSelectedStage] = useState<string>("ALL");
  const [selectedStatus, setSelectedStatus] = useState<string>("ALL");

  // Telecaller & Batch Assignment State
  const [selectedLeadIds, setSelectedLeadIds] = useState<Set<string>>(new Set());
  const [telecallers, setTelecallers] = useState<TelecallerUser[]>([]);
  const [targetTelecallerId, setTargetTelecallerId] = useState<string>("");
  const [assigning, setAssigning] = useState(false);
  const [assignMessage, setAssignMessage] = useState<string | null>(null);
  const [copiedEmailId, setCopiedEmailId] = useState<string | null>(null);

  const handleCopyEmail = (email: string, id: string) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmailId(id);
    setTimeout(() => setCopiedEmailId(null), 2000);
  };
  useEffect(() => {
    loadTelecallers();
  }, []);

  const loadTelecallers = async () => {
    try {
      const list = await api.getTelecallers();
      setTelecallers(list);
      if (list.length > 0) {
        setTargetTelecallerId(list[0].id);
      }
    } catch (err) {
      console.error("Failed to load telecallers for batch assignment:", err);
    }
  };

  const filteredLeads = leads.filter((l) => {
    const matchesSearch =
      !searchTerm ||
      l.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (l.company_name && l.company_name.toLowerCase().includes(searchTerm.toLowerCase())) ||
      (l.contact_name && l.contact_name.toLowerCase().includes(searchTerm.toLowerCase()));

    const matchesStage = selectedStage === "ALL" || l.pipeline_stage_id === selectedStage;
    const matchesStatus = selectedStatus === "ALL" || l.status === selectedStatus;

    return matchesSearch && matchesStage && matchesStatus;
  });

  const allFilteredSelected =
    filteredLeads.length > 0 &&
    filteredLeads.every((l) => selectedLeadIds.has(l.id));

  const handleToggleSelectAll = () => {
    if (allFilteredSelected) {
      setSelectedLeadIds(new Set());
    } else {
      const next = new Set<string>();
      filteredLeads.forEach((l) => next.add(l.id));
      setSelectedLeadIds(next);
    }
  };

  const handleToggleLead = (e: React.MouseEvent | React.ChangeEvent, leadId: string) => {
    e.stopPropagation();
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

  const handleBatchAssign = async () => {
    if (!targetTelecallerId || selectedLeadIds.size === 0) return;
    setAssigning(true);
    try {
      const leadIdList = Array.from(selectedLeadIds);
      const res = await api.batchAssignLeads(leadIdList, targetTelecallerId);

      setAssignMessage(res.message || `Successfully assigned ${leadIdList.length} leads!`);
      setTimeout(() => setAssignMessage(null), 4500);

      setSelectedLeadIds(new Set());
      if (onRefresh) {
        onRefresh();
      }
      loadTelecallers();
    } catch (err: any) {
      alert(err.message || "Failed to batch assign leads");
    } finally {
      setAssigning(false);
    }
  };

  const totalLeads = leads.length;
  const totalCompanies = new Set(leads.map(l => l.company_name).filter(Boolean)).size;
  const totalPipelineValue = leads.reduce((sum, lead) => sum + (Number(lead.value) || 0), 0);
  const activeLeads = leads.filter(l => l.status === "OPEN" || (!l.status.includes("WON") && !l.status.includes("LOST"))).length;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px", position: "relative" }}>
      {/* Page Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
            <Users style={{ width: "22px", height: "22px", color: "var(--primary)" }} />
            Leads & Contacts Directory
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Pipeline progression, contact records, and telecaller assignment
          </p>
        </div>

        {onNewLeadClick && (
          <button
            onClick={onNewLeadClick}
            className="btn-primary"
            style={{
              padding: "8px 18px",
              fontSize: "0.8125rem",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              boxShadow: "0 2px 8px rgba(79, 70, 229, 0.25)"
            }}
          >
            <Plus style={{ width: "15px", height: "15px" }} />
            Add New Lead
          </button>
        )}
      </div>

      {/* Metrics Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        <div className="card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "12px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "var(--primary-light)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Users style={{ width: "20px", height: "20px" }} />
          </div>
          <div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Total Leads</p>
            <h3 style={{ fontSize: "1.25rem", color: "var(--text-primary)", margin: "2px 0 0 0" }}>{totalLeads}</h3>
          </div>
        </div>

        <div className="card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "12px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(16, 185, 129, 0.1)", color: "var(--emerald)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Building2 style={{ width: "20px", height: "20px" }} />
          </div>
          <div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Total Companies</p>
            <h3 style={{ fontSize: "1.25rem", color: "var(--text-primary)", margin: "2px 0 0 0" }}>{totalCompanies}</h3>
          </div>
        </div>

        <div className="card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "12px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(245, 158, 11, 0.1)", color: "#f59e0b", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Briefcase style={{ width: "20px", height: "20px" }} />
          </div>
          <div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Total Deal Value</p>
            <h3 style={{ fontSize: "1.25rem", color: "var(--text-primary)", margin: "2px 0 0 0" }}>₹{totalPipelineValue.toLocaleString("en-IN")}</h3>
          </div>
        </div>

        <div className="card" style={{ padding: "16px", display: "flex", alignItems: "center", gap: "12px", background: "var(--bg-surface)", border: "1px solid var(--border-subtle)" }}>
          <div style={{ width: "40px", height: "40px", borderRadius: "10px", background: "rgba(99, 102, 241, 0.1)", color: "var(--primary)", display: "flex", alignItems: "center", justifyContent: "center" }}>
            <Target style={{ width: "20px", height: "20px" }} />
          </div>
          <div>
            <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Active Leads</p>
            <h3 style={{ fontSize: "1.25rem", color: "var(--text-primary)", margin: "2px 0 0 0" }}>{activeLeads}</h3>
          </div>
        </div>
      </div>

      {/* Toast Notification Banner */}
      {assignMessage && (
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
          <span>{assignMessage}</span>
        </div>
      )}

      {/* Search & Filters */}
      <div className="card" style={{ padding: "16px", display: "flex", flexWrap: "wrap", alignItems: "center", justifyContent: "space-between", gap: "12px" }}>
        <div style={{ position: "relative", flex: 1, minWidth: "240px" }}>
          <Search style={{ width: "16px", height: "16px", color: "var(--text-muted)", position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search leads by title, company, contact person..."
            className="input-text"
            style={{ paddingLeft: "36px", fontSize: "0.8125rem" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Stage Filter */}
          <select
            value={selectedStage}
            onChange={(e) => setSelectedStage(e.target.value)}
            className="select-dropdown"
            style={{ width: "auto", fontSize: "0.8125rem" }}
          >
            <option value="ALL">All Pipeline Stages</option>
            {stages.map((s) => (
              <option key={s.id} value={s.id}>
                {s.name}
              </option>
            ))}
          </select>

          {/* Status Filter */}
          <select
            value={selectedStatus}
            onChange={(e) => setSelectedStatus(e.target.value)}
            className="select-dropdown"
            style={{ width: "auto", fontSize: "0.8125rem" }}
          >
            <option value="ALL">All Statuses</option>
            <option value="OPEN">Open</option>
            <option value="WON">Won</option>
            <option value="LOST">Lost</option>
          </select>

          {onNewLeadClick && (
            <button
              onClick={onNewLeadClick}
              className="btn-primary"
              style={{ fontSize: "0.8125rem", whiteSpace: "nowrap" }}
            >
              <Plus style={{ width: "15px", height: "15px" }} />
              Add Lead
            </button>
          )}
        </div>
      </div>

      {/* Floating Sticky Batch Action Bar (When Leads are Selected) */}
      {selectedLeadIds.size > 0 && (
        <div
          style={{
            position: "sticky",
            top: "70px",
            zIndex: 40,
            background: "var(--bg-surface)",
            border: "2px solid var(--primary)",
            borderRadius: "12px",
            padding: "12px 20px",
            boxShadow: "var(--shadow-lg)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "12px",
            animation: "modal-appear 0.15s ease-out"
          }}
          id="batch-assignment-toolbar"
        >
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{
              fontSize: "0.75rem",
              fontWeight: 800,
              padding: "4px 10px",
              borderRadius: "999px",
              backgroundColor: "var(--primary-light)",
              color: "var(--primary)",
              fontFamily: "monospace"
            }}>
              {selectedLeadIds.size} Leads Selected
            </span>
            <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
              Assign to telecaller queue:
            </span>
          </div>

          <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
            {telecallers.length > 0 ? (
              <select
                value={targetTelecallerId}
                onChange={(e) => setTargetTelecallerId(e.target.value)}
                className="select-dropdown"
                style={{ fontSize: "0.8125rem", width: "auto", minWidth: "200px" }}
                id="select-batch-telecaller"
              >
                {telecallers.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.full_name} ({t.assigned_leads_count} currently)
                  </option>
                ))}
              </select>
            ) : (
              <span style={{ fontSize: "0.75rem", color: "var(--rose-dark)", fontWeight: 600 }}>
                No telecallers created yet. Go to Team tab.
              </span>
            )}

            <button
              type="button"
              onClick={handleBatchAssign}
              disabled={assigning || !targetTelecallerId || telecallers.length === 0}
              className="btn-primary"
              style={{ fontSize: "0.8125rem", padding: "7px 16px" }}
              id="btn-confirm-batch-assign"
            >
              <UserCheck style={{ width: "14px", height: "14px" }} />
              {assigning ? "Assigning..." : `Assign to Telecaller`}
            </button>

            <button
              type="button"
              onClick={() => setSelectedLeadIds(new Set())}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "7px 12px" }}
            >
              <X style={{ width: "14px", height: "14px" }} />
              Deselect
            </button>
          </div>
        </div>
      )}

      {/* Table Container with Mobile Touch Scrolling */}
      <div className="table-responsive card" style={{ padding: "0", overflow: "hidden" }}>
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: "40px", paddingLeft: "16px", paddingRight: "8px" }}>
                <input
                  type="checkbox"
                  checked={allFilteredSelected}
                  onChange={handleToggleSelectAll}
                  title="Select / Deselect all matching leads"
                  style={{ cursor: "pointer", accentColor: "var(--primary)", width: "16px", height: "16px" }}
                />
              </th>
              <th>Lead & Opportunity</th>
              <th>Contact Details</th>
              <th>Pipeline Stage</th>
              <th>Assigned Telecaller</th>
              <th>Radar Score</th>
              <th>Estimated Value</th>
              <th style={{ textAlign: "right", paddingRight: "20px" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filteredLeads.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ textAlign: "center", padding: "48px 0", color: "var(--text-muted)", fontStyle: "italic" }}>
                  No matching leads found
                </td>
              </tr>
            ) : (
              filteredLeads.map((lead) => {
                const isSelected = selectedLeadIds.has(lead.id);
                return (
                  <tr
                    key={lead.id}
                    onClick={() => onSelectLead(lead)}
                    style={{
                      cursor: "pointer",
                      backgroundColor: isSelected ? "var(--primary-light)" : undefined,
                    }}
                  >
                    <td style={{ width: "40px", paddingLeft: "16px", paddingRight: "8px" }} onClick={(e) => e.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={isSelected}
                        onChange={(e) => handleToggleLead(e, lead.id)}
                        style={{ cursor: "pointer", accentColor: "var(--primary)", width: "16px", height: "16px" }}
                      />
                    </td>

                    <td>
                      <p style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.8125rem" }}>
                        {lead.title}
                      </p>
                      <p style={{ color: "var(--text-secondary)", fontSize: "0.75rem", marginTop: "2px" }}>
                        {lead.company_name || "Independent Account"}
                      </p>
                    </td>

                    <td>
                      <p style={{ fontWeight: 600, color: "var(--text-primary)", fontSize: "0.75rem" }}>
                        {lead.contact_name || "Unassigned"}
                      </p>
                      <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "3px", fontSize: "0.6875rem", color: "var(--text-secondary)", flexWrap: "wrap" }}>
                        {lead.contact_phone && (
                          <a
                            href={lead.is_phone_masked ? undefined : getCallUrl(lead.contact_phone)}
                            onClick={(e) => {
                              if (lead.is_phone_masked) e.preventDefault();
                              else e.stopPropagation();
                            }}
                            title={lead.is_phone_masked ? "Masked Phone" : `Click to call (+91 ${format10DigitPhone(lead.contact_phone)})`}
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              color: "inherit",
                              textDecoration: "none"
                            }}
                          >
                            <Phone style={{ width: "12px", height: "12px", color: "var(--emerald)" }} />
                            <span>{format10DigitPhone(lead.contact_phone)}</span>
                            {lead.is_phone_masked && (
                              <span className="badge badge-masked" style={{ fontSize: "0.5625rem", padding: "1px 4px" }}>
                                Masked
                              </span>
                            )}
                          </a>
                        )}
                        {lead.contact_email && (
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleCopyEmail(lead.contact_email!, lead.id);
                            }}
                            title="Copy email to clipboard"
                            style={{
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              background: "var(--bg-surface-subtle)",
                              border: "1px solid var(--border-subtle)",
                              borderRadius: "4px",
                              padding: "2px 6px",
                              fontSize: "0.6875rem",
                              color: "#dc2626",
                              cursor: "pointer",
                              transition: "all 0.15s ease",
                              textAlign: "left"
                            }}
                          >
                            <Mail style={{ width: "11px", height: "11px", color: "#dc2626" }} />
                            <span style={{ textDecoration: "underline", textDecorationStyle: "dotted" }}>
                              {copiedEmailId === lead.id ? "Copied!" : lead.contact_email}
                            </span>
                          </button>
                        )}
                      </div>
                    </td>

                    <td>
                      <span
                        className="badge"
                        style={{
                          backgroundColor: `${lead.stage?.color || "#4f46e5"}15`,
                          color: lead.stage?.color || "var(--primary)",
                          border: `1px solid ${lead.stage?.color || "#4f46e5"}35`,
                        }}
                      >
                        {lead.stage?.name || "Stage"}
                      </span>
                    </td>

                    <td>
                      {lead.owner_name ? (
                        <span style={{
                          display: "inline-flex",
                          alignItems: "center",
                          gap: "4px",
                          fontSize: "0.6875rem",
                          fontWeight: 700,
                          padding: "2px 8px",
                          borderRadius: "999px",
                          background: "var(--primary-light)",
                          color: "var(--primary)",
                          border: "1px solid var(--primary-border)"
                        }}>
                          <Users style={{ width: "11px", height: "11px" }} />
                          {lead.owner_name}
                        </span>
                      ) : (
                        <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", fontStyle: "italic" }}>
                          Unassigned
                        </span>
                      )}
                    </td>

                    <td>
                      <div style={{ display: "flex", alignItems: "center", gap: "6px", fontFamily: "monospace", fontWeight: 700, color: "var(--amber-dark)" }}>
                        <Flame style={{ width: "14px", height: "14px", color: "var(--amber)" }} />
                        <span>{lead.score}</span>
                        <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>/ 100</span>
                      </div>
                    </td>

                    <td style={{ fontFamily: "monospace", fontWeight: 600, color: "var(--text-primary)" }}>
                      ₹{Number(lead.value || 0).toLocaleString("en-IN")}
                    </td>

                    <td style={{ textAlign: "right", paddingRight: "20px" }}>
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectLead(lead);
                        }}
                        className="btn-secondary"
                        style={{ fontSize: "0.75rem", padding: "4px 10px" }}
                      >
                        <ExternalLink style={{ width: "13px", height: "13px" }} />
                        View 360°
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>


    </div>
  );
};
