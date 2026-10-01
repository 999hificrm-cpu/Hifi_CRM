import React, { useState, useEffect } from "react";
import { api, GlobalPerson } from "../services/api";
import { ImportModal } from "./ImportModal";
import { EditPersonModal } from "./EditPersonModal";
import { openGmail } from "../utils/mailHelper";
import { format10DigitPhone, getCallUrl, cleanPhoneInput } from "../utils/phoneHelper";
import {
  UserCheck,
  Search,
  Download,
  Check,
  UploadCloud,
  Plus,
  Phone,
  Mail,
  ExternalLink,
  MapPin,
  Building2,
  Briefcase,
  X,
  Sparkles,
  Users,
  BadgePercent,
  CheckCircle2,
  Filter,
  Trash2
} from "lucide-react";

interface PeopleIntelligenceViewProps {
  currentUser?: any;
}

export const PeopleIntelligenceView: React.FC<PeopleIntelligenceViewProps> = ({ currentUser: propUser }) => {
  const storedUser = localStorage.getItem("jarvis_user");
  const currentUser = propUser || (storedUser ? JSON.parse(storedUser) : null);
  const isSuperAdmin = currentUser?.is_super_admin ?? false;
  const canManage = isSuperAdmin || currentUser?.is_data_entry || currentUser?.platform_role === "DATA_ENTRY" || currentUser?.tenant_role === "DATA_ENTRY";
  const [people, setPeople] = useState<GlobalPerson[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [departmentFilter, setDepartmentFilter] = useState("ALL");
  const [seniorityFilter, setSeniorityFilter] = useState("ALL");
  const [cityFilter, setCityFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [copiedEmailId, setCopiedEmailId] = useState<string | null>(null);

  const handleCopyEmail = (email: string, id: string) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmailId(id);
    setTimeout(() => setCopiedEmailId(null), 2000);
  };

  // Modals state
  const [showImportModal, setShowImportModal] = useState(false);
  const [showAddLeadModal, setShowAddLeadModal] = useState(false);
  const [showPullModal, setShowPullModal] = useState(false);
  const [editingPerson, setEditingPerson] = useState<GlobalPerson | null>(null);
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [targetOrgId, setTargetOrgId] = useState("");
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Detailed Single Add Lead Form State
  const [formName, setFormName] = useState("");
  const [formEmail, setFormEmail] = useState("");
  const [formPhone, setFormPhone] = useState("");
  const [formDesignation, setFormDesignation] = useState("");
  const [formCompany, setFormCompany] = useState("");
  const [associatedCompanies, setAssociatedCompanies] = useState<Array<{ company_name: string; designation: string }>>([
    { company_name: "", designation: "" }
  ]);
  const [formIndustry, setFormIndustry] = useState("");
  const [formSeniority, setFormSeniority] = useState("Director");
  const [formDepartment, setFormDepartment] = useState("Engineering");
  const [formLinkedin, setFormLinkedin] = useState("");
  const [formCity, setFormCity] = useState("");
  const [formState, setFormState] = useState("");
  const [formCountry, setFormCountry] = useState("India");
  const [formValue, setFormValue] = useState("");
  const [formNotes, setFormNotes] = useState("");
  const [submittingLead, setSubmittingLead] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  const handleAddCompanyRow = () => {
    setAssociatedCompanies([...associatedCompanies, { company_name: "", designation: "" }]);
  };

  const handleRemoveCompanyRow = (index: number) => {
    if (associatedCompanies.length > 1) {
      setAssociatedCompanies(associatedCompanies.filter((_, i) => i !== index));
    } else {
      setAssociatedCompanies([{ company_name: "", designation: "" }]);
    }
  };

  const handleCompanyRowChange = (index: number, field: "company_name" | "designation", value: string) => {
    const updated = [...associatedCompanies];
    updated[index][field] = value;
    setAssociatedCompanies(updated);
  };

  useEffect(() => {
    loadGlobalPeople();
    loadOrganizations();
  }, []);

  const loadGlobalPeople = async () => {
    setLoading(true);
    try {
      const data = await api.getGlobalPeople({
        search: searchTerm,
        department: departmentFilter,
        seniority: seniorityFilter,
        city: cityFilter,
      });
      setPeople(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const loadOrganizations = async () => {
    try {
      const orgs = await api.getOrganizations();
      setOrganizations(orgs);
      if (orgs.length > 0) {
        setTargetOrgId(orgs[0].id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSelectToggle = (id: string) => {
    if (selectedIds.includes(id)) {
      setSelectedIds(selectedIds.filter((item) => item !== id));
    } else {
      setSelectedIds([...selectedIds, id]);
    }
  };

  const handleSelectAll = () => {
    if (selectedIds.length === people.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(people.map((p) => p.id));
    }
  };

  // Single Add Lead Handler
  const handleCreatePersonLead = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formName.trim()) {
      setFormError("Full Name is required");
      return;
    }

    setSubmittingLead(true);
    setFormError(null);

    const validAssoc = associatedCompanies
      .map((ac) => ({ company_name: ac.company_name.trim(), designation: ac.designation.trim() }))
      .filter((ac) => ac.company_name.length > 0);

    const primaryCompany = validAssoc[0]?.company_name || formCompany.trim() || undefined;
    const primaryDesignation = validAssoc[0]?.designation || formDesignation.trim() || undefined;

    try {
      const created = await api.createGlobalPerson({
        full_name: formName.trim(),
        email: formEmail.trim() || undefined,
        phone: formPhone.trim() || undefined,
        designation: primaryDesignation,
        company_name: primaryCompany,
        associated_companies: validAssoc,
        industry: formIndustry.trim() || undefined,
        seniority: formSeniority,
        department: formDepartment,
        linkedin_url: formLinkedin.trim() || undefined,
        city: formCity.trim() || undefined,
        state: formState.trim() || undefined,
        country: formCountry.trim() || "India",
        estimated_value: Number(formValue) || 0.0,
        notes: formNotes.trim() || undefined,
        source: "MANUAL",
        status: "ACTIVE",
      });

      setSuccessMsg(`Successfully added "${created.full_name}" to People Intelligence directory!`);
      setShowAddLeadModal(false);
      resetAddLeadForm();
      loadGlobalPeople();
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err: any) {
      setFormError(err.message || "Failed to create person lead");
    } finally {
      setSubmittingLead(false);
    }
  };

  const resetAddLeadForm = () => {
    setFormName("");
    setFormEmail("");
    setFormPhone("");
    setFormDesignation("");
    setFormCompany("");
    setAssociatedCompanies([{ company_name: "", designation: "" }]);
    setFormIndustry("");
    setFormSeniority("Director");
    setFormDepartment("Engineering");
    setFormLinkedin("");
    setFormCity("");
    setFormState("");
    setFormCountry("India");
    setFormValue("");
    setFormNotes("");
    setFormError(null);
  };

  // Pull to CRM Handler
  const handleExecutePull = async () => {
    if (selectedIds.length === 0) return;
    setPulling(true);
    try {
      const res = await api.pullGlobalPeople({
        global_people_ids: selectedIds,
        target_organization_id: targetOrgId || undefined,
      });

      setSuccessMsg(
        `Successfully pulled ${res.pulled_people} executives into CRM! Created ${res.created_leads} active leads, ${res.created_contacts} contacts, and ${res.created_companies} accounts.`
      );
      setSelectedIds([]);
      setShowPullModal(false);
      setTimeout(() => setSuccessMsg(null), 6000);
    } catch (err: any) {
      alert(err.message || "Failed to pull records to CRM");
    } finally {
      setPulling(false);
    }
  };

  // Metrics Calculations
  const totalExecutives = people.length;
  const decisionMakers = people.filter((p) =>
    ["C-Level", "VP", "Director"].includes(p.seniority || "")
  ).length;
  const verifiedContacts = people.filter((p) => Boolean(p.email && p.phone)).length;
  const totalPotentialValue = people.reduce(
    (acc, curr) => acc + Number(curr.estimated_value || 0),
    0
  );

  const formatCurrency = (val: number) => {
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(1)} L`;
    if (val >= 1000) return `₹${(val / 1000).toFixed(0)}k`;
    return `₹${val.toLocaleString("en-IN")}`;
  };

  const getSeniorityBadge = (seniority?: string | null) => {
    switch (seniority) {
      case "C-Level":
        return { bg: "#fdf2f8", color: "#9d174d", border: "#fbcfe8" };
      case "VP":
        return { bg: "#eff6ff", color: "#1e40af", border: "#bfdbfe" };
      case "Director":
        return { bg: "#ecfdf5", color: "#065f46", border: "#a7f3d0" };
      case "Manager":
        return { bg: "#fffbeb", color: "#92400e", border: "#fde68a" };
      default:
        return { bg: "var(--bg-surface-subtle)", color: "var(--text-secondary)", border: "var(--border-subtle)" };
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
              <UserCheck style={{ width: "22px", height: "22px", color: "var(--emerald)" }} />
              People Intelligence
            </h2>
            <span style={{
              fontSize: "0.6875rem",
              fontWeight: 700,
              padding: "2px 8px",
              borderRadius: "999px",
              backgroundColor: "var(--emerald-light)",
              color: "var(--emerald-dark)",
              border: "1px solid var(--emerald-border)"
            }}>
              global_people
            </span>
          </div>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "3px" }}>
            Global executive & decision-maker directory. Bulk upload or add detailed single leads to build your sales pipeline.
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {/* Bulk Ingestion Wizard Button */}
          <button
            onClick={() => setShowImportModal(true)}
            className="btn-secondary"
            style={{ fontSize: "0.8125rem" }}
            title="Upload CSV / Excel to bulk import decision-makers into global_people"
          >
            <UploadCloud style={{ width: "16px", height: "16px", color: "var(--primary)" }} />
            Import Global Database
          </button>

          {/* Single Add Lead Button */}
          <button
            onClick={() => setShowAddLeadModal(true)}
            className="btn-primary"
            style={{ fontSize: "0.8125rem" }}
          >
            <Plus style={{ width: "16px", height: "16px" }} />
            + Add Lead
          </button>

          {/* Pull Selected to CRM (Hidden for Super Admin & Data Entry) */}
          {!canManage && selectedIds.length > 0 && (
            <button
              onClick={() => setShowPullModal(true)}
              className="btn-primary"
              style={{ background: "linear-gradient(135deg, #059669, #047857)", borderColor: "#065f46" }}
            >
              <Download style={{ width: "16px", height: "16px" }} />
              Pull {selectedIds.length} Selected to CRM
            </button>
          )}
        </div>
      </div>

      {/* Success Notification Banner */}
      {successMsg && (
        <div style={{
          padding: "12px 16px",
          borderRadius: "10px",
          background: "var(--emerald-light)",
          border: "1px solid var(--emerald-border)",
          color: "var(--emerald-dark)",
          fontSize: "0.8125rem",
          fontWeight: 600,
          display: "flex",
          alignItems: "center",
          gap: "8px"
        }}>
          <CheckCircle2 style={{ width: "16px", height: "16px", flexShrink: 0 }} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Executive Metric Stat Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "14px" }}>
        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Total People Leads
            </span>
            <Users style={{ width: "16px", height: "16px", color: "var(--primary)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--text-primary)" }}>
            {totalExecutives}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            Profiles in `global_people` table
          </span>
        </div>

        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Decision-Makers
            </span>
            <Briefcase style={{ width: "16px", height: "16px", color: "var(--indigo)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--indigo-dark)" }}>
            {decisionMakers}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            C-Level, VP & Director tiers
          </span>
        </div>

        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Verified Contacts
            </span>
            <CheckCircle2 style={{ width: "16px", height: "16px", color: "var(--emerald)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--emerald-dark)" }}>
            {verifiedContacts}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            Direct mobile & email verified
          </span>
        </div>

        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Enterprise Accounts
            </span>
            <Building2 style={{ width: "16px", height: "16px", color: "var(--amber)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--amber-dark)" }}>
            {new Set(people.map((p) => p.company_name).filter(Boolean)).size}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            Corporate networks represented
          </span>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="card" style={{ padding: "16px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "12px" }}>
        {/* Main Search Input */}
        <div style={{ position: "relative", flex: 1, minWidth: "240px" }}>
          <Search style={{ width: "15px", height: "15px", color: "var(--text-muted)", position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadGlobalPeople()}
            placeholder="Search by name, role, company, email, phone..."
            className="input-text"
            style={{ paddingLeft: "36px" }}
          />
        </div>

        {/* Department Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Dept:</span>
          <select
            value={departmentFilter}
            onChange={(e) => setDepartmentFilter(e.target.value)}
            className="input-text"
            style={{ width: "150px", padding: "8px 10px" }}
          >
            <option value="ALL">All Departments</option>
            <option value="Engineering">Engineering</option>
            <option value="Sales">Sales</option>
            <option value="Marketing">Marketing</option>
            <option value="Operations">Operations</option>
            <option value="Finance">Finance</option>
            <option value="HR">Human Resources</option>
            <option value="Executive">Executive</option>
          </select>
        </div>

        {/* Seniority Filter */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <span style={{ fontSize: "0.75rem", color: "var(--text-muted)", fontWeight: 600 }}>Level:</span>
          <select
            value={seniorityFilter}
            onChange={(e) => setSeniorityFilter(e.target.value)}
            className="input-text"
            style={{ width: "150px", padding: "8px 10px" }}
          >
            <option value="ALL">All Seniority</option>
            <option value="C-Level">C-Level</option>
            <option value="VP">VP</option>
            <option value="Director">Director</option>
            <option value="Manager">Manager</option>
            <option value="Lead">Lead</option>
            <option value="Individual Contributor">Individual Contributor</option>
          </select>
        </div>

        {/* City Filter */}
        <input
          type="text"
          value={cityFilter}
          onChange={(e) => setCityFilter(e.target.value)}
          placeholder="City (e.g. Mumbai, Bengaluru)"
          className="input-text"
          style={{ width: "170px" }}
        />

        <button onClick={loadGlobalPeople} className="btn-secondary" style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
          <Filter style={{ width: "14px", height: "14px" }} />
          Filter
        </button>
      </div>

      {/* People Leads Directory Table */}
      <div className="card" style={{ overflow: "hidden" }}>
        {/* Table Header Bar */}
        <div style={{
          padding: "12px 20px",
          borderBottom: "1px solid var(--border-subtle)",
          background: "var(--bg-surface-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: "0.75rem"
        }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <input
              type="checkbox"
              checked={people.length > 0 && selectedIds.length === people.length}
              onChange={handleSelectAll}
              style={{ cursor: "pointer", accentColor: "var(--primary)" }}
            />
            <span style={{ fontWeight: 700, color: "var(--text-secondary)" }}>
              {selectedIds.length} of {people.length} selected
            </span>
          </div>
          <span style={{ color: "var(--text-muted)", fontSize: "0.6875rem" }}>
            Stored in table: <code style={{ color: "var(--emerald)", fontWeight: 700 }}>global_people</code>
          </span>
        </div>

        {loading ? (
          <div style={{ padding: "48px 0", textAlign: "center", color: "var(--text-muted)" }}>
            Loading executive profiles...
          </div>
        ) : people.length === 0 ? (
          <div style={{ padding: "48px 0", textAlign: "center", color: "var(--text-muted)" }}>
            No people records found matching your filters. Click <strong>+ Add Lead</strong> or <strong>Import Global Database</strong> to ingest records.
          </div>
        ) : (
          <div style={{ overflowX: "auto" }}>
            <table className="leads-table" style={{ width: "100%", borderCollapse: "collapse" }}>
              <thead>
                <tr style={{ background: "var(--bg-surface-subtle)", borderBottom: "1px solid var(--border-subtle)" }}>
                  <th style={{ width: "40px", padding: "12px 16px" }}></th>
                  <th style={{ textAlign: "left", padding: "12px 16px", fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Executive Profile</th>
                  <th style={{ textAlign: "left", padding: "12px 16px", fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Company & Industry</th>
                  <th style={{ textAlign: "left", padding: "12px 16px", fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Contact Details</th>
                  <th style={{ textAlign: "left", padding: "12px 16px", fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Department & Location</th>
                  <th style={{ textAlign: "center", padding: "12px 16px", fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Direct Channels</th>
                  <th style={{ textAlign: "center", padding: "12px 16px", fontSize: "0.6875rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>Status</th>
                </tr>
              </thead>
              <tbody>
                {people.map((person) => {
                  const isSelected = selectedIds.includes(person.id);
                  const senBadge = getSeniorityBadge(person.seniority);
                  const initial = person.full_name ? person.full_name.charAt(0).toUpperCase() : "P";

                  return (
                    <tr
                      key={person.id}
                      style={{
                        borderBottom: "1px solid var(--border-subtle)",
                        background: isSelected ? "var(--bg-surface-subtle)" : "transparent",
                        transition: "background 0.15s ease"
                      }}
                    >
                      {/* Checkbox */}
                      <td style={{ padding: "12px 16px" }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleSelectToggle(person.id)}
                          style={{ cursor: "pointer", accentColor: "var(--primary)" }}
                        />
                      </td>

                      {/* Executive Profile */}
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <div style={{
                            width: "34px",
                            height: "34px",
                            borderRadius: "50%",
                            background: "linear-gradient(135deg, var(--primary), var(--indigo-dark))",
                            color: "#fff",
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontWeight: 700,
                            fontSize: "0.8125rem",
                            flexShrink: 0
                          }}>
                            {initial}
                          </div>
                          <div>
                            <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                              <span style={{ fontWeight: 700, color: "var(--text-primary)", fontSize: "0.875rem" }}>
                                {person.full_name}
                              </span>
                              {person.seniority && (
                                <span style={{
                                  fontSize: "0.625rem",
                                  fontWeight: 700,
                                  padding: "2px 6px",
                                  borderRadius: "4px",
                                  background: senBadge.bg,
                                  color: senBadge.color,
                                  border: `1px solid ${senBadge.border}`
                                }}>
                                  {person.seniority}
                                </span>
                              )}
                            </div>
                            <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                              {person.designation || "Executive"}
                            </div>
                          </div>
                        </div>
                      </td>

                      {/* Company & Industry / Associated Companies */}
                      <td style={{ padding: "12px 16px" }}>
                        {person.associated_companies && person.associated_companies.length > 0 ? (
                          <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
                            {person.associated_companies.map((ac, acIdx) => (
                              <div key={acIdx} style={{ display: "flex", alignItems: "center", gap: "5px", fontSize: "0.75rem" }}>
                                <Building2 style={{ width: "12px", height: "12px", color: acIdx === 0 ? "var(--cyan-dark)" : "var(--text-muted)", flexShrink: 0 }} />
                                <span style={{ fontWeight: acIdx === 0 ? 700 : 500, color: "var(--text-primary)" }}>{ac.company_name}</span>
                                {ac.designation && (
                                  <span style={{ fontSize: "0.6875rem", color: "var(--text-secondary)", background: "var(--bg-surface-subtle)", padding: "1px 5px", borderRadius: "4px" }}>
                                    {ac.designation}
                                  </span>
                                )}
                              </div>
                            ))}
                          </div>
                        ) : (
                          <div style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "5px" }}>
                            <Building2 style={{ width: "13px", height: "13px", color: "var(--text-muted)" }} />
                            {person.company_name || "Independent"}
                          </div>
                        )}
                        {person.industry && (
                          <div style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>
                            {person.industry}
                          </div>
                        )}
                      </td>

                      {/* Contact Details */}
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", flexDirection: "column", gap: "4px", fontSize: "0.75rem" }}>
                          {person.phone && (
                            <a
                              href={getCallUrl(person.phone)}
                              style={{ display: "inline-flex", alignItems: "center", gap: "5px", color: "var(--emerald)", textDecoration: "none", fontWeight: 600 }}
                            >
                              <Phone style={{ width: "12px", height: "12px" }} />
                              {format10DigitPhone(person.phone)}
                            </a>
                          )}
                          {person.email && (
                            <div style={{ display: "flex", alignItems: "center", gap: "5px" }}>
                              <button
                                type="button"
                                onClick={() => handleCopyEmail(person.email!, person.id)}
                                style={{
                                  background: "none",
                                  border: "none",
                                  padding: 0,
                                  cursor: "pointer",
                                  color: "var(--text-secondary)",
                                  fontSize: "0.6875rem",
                                  display: "flex",
                                  alignItems: "center",
                                  gap: "3px",
                                  textDecoration: "underline"
                                }}
                                title="Copy email to clipboard"
                              >
                                <Mail style={{ width: "12px", height: "12px" }} />
                                {copiedEmailId === person.id ? "Copied!" : person.email}
                              </button>
                            </div>
                          )}
                          {person.linkedin_url && (
                            <a
                              href={person.linkedin_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              style={{ display: "inline-flex", alignItems: "center", gap: "4px", fontSize: "0.6875rem", color: "#0077b5", textDecoration: "none" }}
                            >
                              <ExternalLink style={{ width: "11px", height: "11px" }} />
                              LinkedIn Profile
                            </a>
                          )}
                        </div>
                      </td>

                      {/* Department & Location */}
                      <td style={{ padding: "12px 16px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>
                          {person.department || "General"}
                        </div>
                        <div style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>
                          <MapPin style={{ width: "11px", height: "11px" }} />
                          {[person.city, person.state, person.country].filter(Boolean).join(", ")}
                        </div>
                      </td>

                      {/* Direct Outreach Channels */}
                      <td style={{ padding: "12px 16px", textAlign: "center" }}>
                        <div style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                          {person.phone && (
                            <span
                              style={{
                                fontSize: "0.6875rem",
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: "4px",
                                background: "rgba(16, 185, 129, 0.1)",
                                color: "var(--emerald)",
                                border: "1px solid rgba(16, 185, 129, 0.25)",
                              }}
                              title={`Direct Phone: ${format10DigitPhone(person.phone)}`}
                            >
                              Phone
                            </span>
                          )}
                          {person.email && (
                            <span
                              style={{
                                fontSize: "0.6875rem",
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: "4px",
                                background: "rgba(99, 102, 241, 0.1)",
                                color: "var(--primary)",
                                border: "1px solid rgba(99, 102, 241, 0.25)",
                              }}
                              title={`Corporate Email: ${person.email}`}
                            >
                              Email
                            </span>
                          )}
                          {person.linkedin_url && (
                            <span
                              style={{
                                fontSize: "0.6875rem",
                                fontWeight: 700,
                                padding: "2px 6px",
                                borderRadius: "4px",
                                background: "rgba(6, 182, 212, 0.1)",
                                color: "var(--cyan)",
                                border: "1px solid rgba(6, 182, 212, 0.25)",
                              }}
                              title="LinkedIn Verified"
                            >
                              LinkedIn
                            </span>
                          )}
                        </div>
                      </td>

                      {/* Status & Actions */}
                      <td style={{ padding: "12px 16px", textAlign: "center" }}>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: "6px" }}>
                          <span style={{
                            fontSize: "0.625rem",
                            fontWeight: 700,
                            padding: "2px 8px",
                            borderRadius: "999px",
                            background: "var(--emerald-light)",
                            color: "var(--emerald-dark)",
                            border: "1px solid var(--emerald-border)",
                            textTransform: "uppercase"
                          }}>
                            VERIFIED PROFILE
                          </span>
                          {canManage && (
                            <button
                              onClick={() => setEditingPerson(person)}
                              className="btn btn-secondary"
                              style={{
                                padding: "3px 8px",
                                fontSize: "0.72rem",
                                borderRadius: "6px",
                                border: "1px solid var(--border-color)",
                                background: "var(--bg-surface)",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                              }}
                              title="Edit Executive Profile"
                            >
                              ✏️ Edit
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* =========================================================================
          MODAL 1: SINGLE ADD LEAD MODAL (Detailed Input Fields)
         ========================================================================= */}
      {showAddLeadModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.45)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px",
          }}
        >
          <div
            style={{
              background: "var(--bg-surface)",
              borderRadius: "14px",
              border: "1px solid var(--border-subtle)",
              boxShadow: "var(--shadow-xl)",
              width: "100%",
              maxWidth: "680px",
              maxHeight: "90vh",
              overflowY: "auto",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            {/* Modal Header */}
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "8px",
                  backgroundColor: "var(--emerald-light)",
                  color: "var(--emerald-dark)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}>
                  <UserCheck style={{ width: "18px", height: "18px" }} />
                </div>
                <div>
                  <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                    Add Lead to People Intelligence
                  </h3>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                    Directly persist person lead with detailed executive attributes into `global_people`.
                  </p>
                </div>
              </div>
              <button
                onClick={() => setShowAddLeadModal(false)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            {formError && (
              <div style={{
                padding: "10px 14px",
                borderRadius: "8px",
                backgroundColor: "var(--rose-light)",
                border: "1px solid var(--rose-border)",
                color: "var(--rose-dark)",
                fontSize: "0.75rem",
                fontWeight: 600,
              }}>
                {formError}
              </div>
            )}

            {/* Detailed Input Form */}
            <form onSubmit={handleCreatePersonLead} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {/* Primary Required Inputs: Name, Mobile, Email */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Full Name <span style={{ color: "var(--rose)" }}>*</span>
                  </label>
                  <input
                    type="text"
                    required
                    placeholder="e.g. Rajesh Sharma"
                    value={formName}
                    onChange={(e) => setFormName(e.target.value)}
                    className="input-text"
                    id="person-lead-name"
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Mobile Number (10 Digits)
                  </label>
                  <input
                    type="text"
                    placeholder="9876543210"
                    maxLength={10}
                    value={formPhone}
                    onChange={(e) => setFormPhone(cleanPhoneInput(e.target.value))}
                    className="input-text"
                    id="person-lead-mobile"
                  />
                </div>
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Email ID
                  </label>
                  <input
                    type="email"
                    placeholder="rajesh.sharma@company.com"
                    value={formEmail}
                    onChange={(e) => setFormEmail(e.target.value)}
                    className="input-text"
                    id="person-lead-email"
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Industry / Domain
                  </label>
                  <input
                    type="text"
                    placeholder="e.g. Aerospace, IT, BFSI"
                    value={formIndustry}
                    onChange={(e) => setFormIndustry(e.target.value)}
                    className="input-text"
                    id="person-lead-industry"
                  />
                </div>
              </div>

              {/* Dynamic Associated Companies & Designations Section */}
              <div style={{
                padding: "12px 14px",
                borderRadius: "10px",
                background: "var(--bg-surface-subtle)",
                border: "1px solid var(--border-subtle)",
                display: "flex",
                flexDirection: "column",
                gap: "10px"
              }}>
                <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
                  <div>
                    <h4 style={{ fontSize: "0.8125rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "6px" }}>
                      <Building2 style={{ width: "15px", height: "15px", color: "var(--cyan-dark)" }} />
                      Associated Companies & Designations
                    </h4>
                    <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>
                      Add one or multiple companies with specific designation/role for each
                    </p>
                  </div>
                  <button
                    type="button"
                    onClick={handleAddCompanyRow}
                    className="btn-secondary"
                    style={{ fontSize: "0.6875rem", padding: "4px 8px" }}
                    id="add-associated-company-btn"
                  >
                    <Plus style={{ width: "12px", height: "12px" }} />
                    + Add Another Company
                  </button>
                </div>

                <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
                  {associatedCompanies.map((item, idx) => (
                    <div key={idx} style={{ display: "grid", gridTemplateColumns: "1fr 1fr auto", gap: "8px", alignItems: "center" }}>
                      <div>
                        <input
                          type="text"
                          placeholder={`Company ${idx + 1} Name (e.g. Tata Advanced Systems)`}
                          value={item.company_name}
                          onChange={(e) => handleCompanyRowChange(idx, "company_name", e.target.value)}
                          className="input-text"
                          style={{ width: "100%", fontSize: "0.75rem" }}
                          id={`person-company-name-${idx}`}
                        />
                      </div>
                      <div>
                        <input
                          type="text"
                          placeholder={`Designation (e.g. Director / Advisor)`}
                          value={item.designation}
                          onChange={(e) => handleCompanyRowChange(idx, "designation", e.target.value)}
                          className="input-text"
                          style={{ width: "100%", fontSize: "0.75rem" }}
                          id={`person-designation-${idx}`}
                        />
                      </div>
                      <button
                        type="button"
                        onClick={() => handleRemoveCompanyRow(idx)}
                        disabled={associatedCompanies.length === 1 && idx === 0 && !item.company_name}
                        style={{
                          background: "none",
                          border: "none",
                          cursor: "pointer",
                          color: "var(--rose)",
                          padding: "6px",
                          borderRadius: "4px",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center"
                        }}
                        title="Remove Company"
                      >
                        <Trash2 style={{ width: "15px", height: "15px" }} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>

              {/* Row 4: Seniority & Department */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Seniority Level
                  </label>
                  <select
                    value={formSeniority}
                    onChange={(e) => setFormSeniority(e.target.value)}
                    className="input-text"
                  >
                    <option value="C-Level">C-Level (CEO, CTO, COO, CFO)</option>
                    <option value="VP">VP (Vice President)</option>
                    <option value="Director">Director</option>
                    <option value="Manager">Manager</option>
                    <option value="Lead">Lead / Head</option>
                    <option value="Individual Contributor">Individual Contributor</option>
                  </select>
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Department
                  </label>
                  <select
                    value={formDepartment}
                    onChange={(e) => setFormDepartment(e.target.value)}
                    className="input-text"
                  >
                    <option value="Engineering">Engineering & Technology</option>
                    <option value="Sales">Sales & Business Development</option>
                    <option value="Marketing">Marketing & Growth</option>
                    <option value="Operations">Operations & Supply Chain</option>
                    <option value="Finance">Finance & Accounts</option>
                    <option value="HR">Human Resources</option>
                    <option value="Executive">Executive Leadership</option>
                  </select>
                </div>
              </div>

              {/* Row 5: LinkedIn URL & Estimated Value */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    LinkedIn Profile URL
                  </label>
                  <input
                    type="url"
                    placeholder="https://linkedin.com/in/username"
                    value={formLinkedin}
                    onChange={(e) => setFormLinkedin(e.target.value)}
                    className="input-text"
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Estimated Opportunity Value (₹)
                  </label>
                  <input
                    type="number"
                    placeholder="e.g. 1500000"
                    value={formValue}
                    onChange={(e) => setFormValue(e.target.value)}
                    className="input-text"
                  />
                </div>
              </div>

              {/* Row 6: City, State, Country */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    City
                  </label>
                  <input
                    type="text"
                    placeholder="Bengaluru"
                    value={formCity}
                    onChange={(e) => setFormCity(e.target.value)}
                    className="input-text"
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    State
                  </label>
                  <input
                    type="text"
                    placeholder="Karnataka"
                    value={formState}
                    onChange={(e) => setFormState(e.target.value)}
                    className="input-text"
                  />
                </div>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                    Country
                  </label>
                  <input
                    type="text"
                    value={formCountry}
                    onChange={(e) => setFormCountry(e.target.value)}
                    className="input-text"
                  />
                </div>
              </div>

              {/* Row 7: Notes & Persona Summary */}
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>
                  Notes & Persona Bio
                </label>
                <textarea
                  rows={3}
                  placeholder="Key priorities, pain points, budget authority, communication preferences..."
                  value={formNotes}
                  onChange={(e) => setFormNotes(e.target.value)}
                  className="input-text"
                  style={{ resize: "vertical" }}
                />
              </div>

              {/* Modal Actions */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "10px", marginTop: "8px", borderTop: "1px solid var(--border-subtle)", paddingTop: "14px" }}>
                <button
                  type="button"
                  onClick={() => setShowAddLeadModal(false)}
                  className="btn-secondary"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submittingLead}
                  className="btn-primary"
                  style={{ minWidth: "130px" }}
                >
                  {submittingLead ? "Saving..." : "Save Person Lead"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 2: PULL SELECTED TO CRM MODAL
         ========================================================================= */}
      {showPullModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            backgroundColor: "rgba(15, 23, 42, 0.45)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "16px",
          }}
        >
          <div
            style={{
              background: "var(--bg-surface)",
              borderRadius: "14px",
              border: "1px solid var(--border-subtle)",
              boxShadow: "var(--shadow-xl)",
              width: "100%",
              maxWidth: "460px",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "16px",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <div style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "8px",
                  backgroundColor: "var(--emerald-light)",
                  color: "var(--emerald-dark)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center"
                }}>
                  <Download style={{ width: "18px", height: "18px" }} />
                </div>
                <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  Pull {selectedIds.length} People to CRM
                </h3>
              </div>
              <button
                onClick={() => setShowPullModal(false)}
                style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer" }}
              >
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)" }}>
              The selected executives will be automatically mapped to <strong>Contacts</strong>, <strong>Companies</strong>, and active sales <strong>Leads</strong> inside the target organization.
            </p>

            <div>
              <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "6px" }}>
                Target Organization *
              </label>
              <select
                value={targetOrgId}
                onChange={(e) => setTargetOrgId(e.target.value)}
                className="input-text"
              >
                {organizations.map((org) => (
                  <option key={org.id} value={org.id}>
                    {org.name} ({org.domain || "Internal Tenant"})
                  </option>
                ))}
              </select>
            </div>

            <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
              <button
                type="button"
                onClick={() => setShowPullModal(false)}
                className="btn-secondary"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={pulling}
                onClick={handleExecutePull}
                className="btn-primary"
                style={{ background: "linear-gradient(135deg, #059669, #047857)", borderColor: "#065f46" }}
              >
                {pulling ? "Pulling Records..." : "Confirm & Pull to CRM"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* =========================================================================
          MODAL 3: BULK INGESTION WIZARD (jobType="GLOBAL_PEOPLE")
         ========================================================================= */}
      {showImportModal && (
        <ImportModal
          jobType="GLOBAL_PEOPLE"
          onClose={() => setShowImportModal(false)}
          onSuccess={() => {
            loadGlobalPeople();
            setShowImportModal(false);
          }}
        />
      )}

      {editingPerson && (
        <EditPersonModal
          person={editingPerson}
          isOpen={Boolean(editingPerson)}
          onClose={() => setEditingPerson(null)}
          onSaved={(updated) => {
            setPeople((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
            setSuccessMsg(`Decision maker profile for "${updated.full_name}" updated!`);
            setTimeout(() => setSuccessMsg(null), 4000);
          }}
        />
      )}
    </div>
  );
};
