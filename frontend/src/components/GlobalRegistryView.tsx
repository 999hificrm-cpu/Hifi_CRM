import React, { useState, useEffect } from "react";
import { api, GlobalCompany, GlobalCompanyCreatePayload } from "../services/api";
import { ImportModal } from "./ImportModal";
import { EditCompanyModal } from "./EditCompanyModal";
import { format10DigitPhone, getCallUrl, cleanPhoneInput } from "../utils/phoneHelper";
import {
  Globe2,
  Search,
  Download,
  Check,
  MapPin,
  UploadCloud,
  Plus,
  Building2,
  Phone,
  Mail,
  Globe,
  X,
  CheckCircle2,
  Users,
  ShieldCheck
} from "lucide-react";

interface GlobalRegistryViewProps {
  currentUser?: any;
}

export const GlobalRegistryView: React.FC<GlobalRegistryViewProps> = ({ currentUser: propUser }) => {
  const storedUser = localStorage.getItem("jarvis_user");
  const currentUser = propUser || (storedUser ? JSON.parse(storedUser) : null);
  const isSuperAdmin = currentUser?.is_super_admin ?? false;
  const canManage = isSuperAdmin || currentUser?.is_data_entry || currentUser?.platform_role === "DATA_ENTRY" || currentUser?.tenant_role === "DATA_ENTRY";
  const [companies, setCompanies] = useState<GlobalCompany[]>([]);
  const [searchTerm, setSearchTerm] = useState("");
  const [cityFilter, setCityFilter] = useState("");
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [pulling, setPulling] = useState(false);
  const [showImportModal, setShowImportModal] = useState(false);
  const [showAddModal, setShowAddModal] = useState(false);
  const [editingCompany, setEditingCompany] = useState<GlobalCompany | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // New Company Form State (UUID is kept internal, never exposed to user)
  const generateUUID = () => {
    return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, function (c) {
      const r = (Math.random() * 16) | 0;
      const v = c === "x" ? r : (r & 0x3) | 0x8;
      return v.toString(16);
    });
  };

  const initialForm: GlobalCompanyCreatePayload = {
    legal_name: "",
    id: generateUUID(),
    cin: "",
    registration_number: "",
    gst_number: "",
    address: "",
    city: "",
    postal_code: "",
    state: "",
    website: "",
    email: "",
    phone: "",
    industry: "",
    company_type: "Private Limited",
  };

  const [formData, setFormData] = useState<GlobalCompanyCreatePayload>(initialForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  useEffect(() => {
    loadGlobalCompanies();
  }, []);

  const loadGlobalCompanies = async () => {
    setLoading(true);
    try {
      const data = await api.getGlobalCompanies(searchTerm, cityFilter);
      setCompanies(data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAddModal = () => {
    setFormData({
      ...initialForm,
      id: generateUUID(),
    });
    setFormError(null);
    setShowAddModal(true);
  };

  const handleCreateCompany = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.legal_name.trim()) {
      setFormError("Company Name is required.");
      return;
    }

    setSaving(true);
    setFormError(null);
    try {
      await api.createGlobalCompany(formData);
      setShowAddModal(false);
      setSuccessMsg(`Company "${formData.legal_name}" created successfully!`);
      setTimeout(() => setSuccessMsg(null), 4000);
      loadGlobalCompanies();
    } catch (err: any) {
      setFormError(err.message || "Failed to create company.");
    } finally {
      setSaving(false);
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
    if (selectedIds.length === companies.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(companies.map((c) => c.id));
    }
  };

  const handlePullToCRM = async () => {
    if (selectedIds.length === 0) return;
    setPulling(true);
    try {
      const res = await api.pullGlobalCompanies(selectedIds);
      setSuccessMsg(
        `Successfully pulled ${res.pulled_companies} companies and created ${res.created_leads} active CRM leads! Remaining pull credits: ${res.remaining_quota}`
      );
      setSelectedIds([]);
      setTimeout(() => setSuccessMsg(null), 5000);
    } catch (err: any) {
      alert(err.message || "Failed to pull records");
    } finally {
      setPulling(false);
    }
  };

  // KPI Calculations
  const formatCurrency = (val: number) => {
    if (!val || val === 0) return "₹0";
    if (val >= 10000000) {
      return `₹${(val / 10000000).toFixed(2)} Cr`;
    }
    if (val >= 100000) {
      return `₹${(val / 100000).toFixed(2)} Lakh`;
    }
    return `₹${val.toLocaleString("en-IN")}`;
  };

  const totalCompanies = companies.length;
  const verifiedCompaniesCount = companies.filter(
    (c) =>
      Boolean(c.cin && c.cin.trim()) ||
      Boolean(c.gst_number && c.gst_number.trim()) ||
      Boolean(c.registration_number && c.registration_number.trim())
  ).length;

  const totalKeyPeople = companies.reduce((sum, c) => sum + (c.contacts_count || 0), 0);

  const totalRevenue = companies.reduce((sum, c) => {
    const isPublic = (c.company_type || "").toLowerCase().includes("public");
    const base = isPublic ? 50000000 : c.cin ? 12000000 : 7500000;
    const keyExecsBonus = (c.contacts_count || 0) * 2000000;
    return sum + base + keyExecsBonus;
  }, 0);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
        <div>
          <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
            <Globe2 style={{ width: "22px", height: "22px", color: "var(--cyan)" }} />
            Company Intelligence Registry
          </h2>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
            Verified enterprise business registry with CIN, GSTIN, registered address, and corporate contact profiles
          </p>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          <button
            onClick={handleOpenAddModal}
            className="btn-primary"
            style={{ fontSize: "0.8125rem" }}
            id="add-company-btn"
          >
            <Plus style={{ width: "16px", height: "16px" }} />
            + Add Company
          </button>

          <button
            onClick={() => setShowImportModal(true)}
            className="btn-secondary"
            style={{ fontSize: "0.8125rem" }}
            title="Import enterprise companies and contacts into Global Database"
          >
            <UploadCloud style={{ width: "16px", height: "16px", color: "var(--primary)" }} />
            Import to Global Database
          </button>

          {!canManage && selectedIds.length > 0 && (
            <button
              onClick={handlePullToCRM}
              disabled={pulling}
              className="btn-primary"
              style={{ background: "linear-gradient(135deg, #0891b2, #0e7490)", borderColor: "#155e75" }}
            >
              <Download style={{ width: "16px", height: "16px" }} />
              {pulling ? "Pulling Records..." : `Pull ${selectedIds.length} Selected to CRM`}
            </button>
          )}
        </div>
      </div>

      {/* KPI Summary Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
        {/* 1. Total Enterprises */}
        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Total Enterprises
            </span>
            <Building2 style={{ width: "16px", height: "16px", color: "var(--cyan)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--cyan-dark)" }}>
            {totalCompanies}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            Active businesses in global registry
          </span>
        </div>

        {/* 2. Direct Contact Reach */}
        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Direct Contact Reach
            </span>
            <ShieldCheck style={{ width: "16px", height: "16px", color: "var(--amber)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--amber-dark)" }}>
            {companies.filter((c) => Boolean(c.phone || c.email)).length}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            Direct corporate phone & email verified
          </span>
        </div>

        {/* 3. Verified Counts */}
        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Verified Counts
            </span>
            <CheckCircle2 style={{ width: "16px", height: "16px", color: "var(--emerald)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--emerald-dark)" }}>
            {verifiedCompaniesCount}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            CIN & GSTIN registered records
          </span>
        </div>

        {/* 4. Key Decision Makers / Executives */}
        <div className="card" style={{ padding: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase", letterSpacing: "0.03em" }}>
              Key Executives
            </span>
            <Users style={{ width: "16px", height: "16px", color: "var(--primary)" }} />
          </div>
          <div style={{ fontSize: "1.5rem", fontWeight: 800, color: "var(--primary-dark)" }}>
            {totalKeyPeople}
          </div>
          <span style={{ fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "4px", display: "block" }}>
            Verified directors & key personnel
          </span>
        </div>
      </div>

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
          <Check style={{ width: "16px", height: "16px" }} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* Search & Filter Bar */}
      <div className="card" style={{ padding: "16px", display: "flex", flexWrap: "wrap", alignItems: "center", gap: "12px" }}>
        <div style={{ position: "relative", flex: 1, minWidth: "260px" }}>
          <Search style={{ width: "16px", height: "16px", color: "var(--text-muted)", position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)" }} />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && loadGlobalCompanies()}
            placeholder="Search by company name, CIN, GST, or city..."
            className="input-text"
            style={{ paddingLeft: "36px" }}
          />
        </div>

        <input
          type="text"
          value={cityFilter}
          onChange={(e) => setCityFilter(e.target.value)}
          placeholder="Filter by city (e.g. Pune, Mumbai)"
          className="input-text"
          style={{ width: "200px" }}
        />

        <button onClick={loadGlobalCompanies} className="btn-secondary">
          Filter
        </button>
      </div>

      {/* Registry Table / List */}
      <div className="card" style={{ overflow: "hidden" }}>
        <div style={{
          padding: "12px 20px",
          borderBottom: "1px solid var(--border-subtle)",
          background: "var(--bg-surface-subtle)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          fontSize: "0.75rem",
          color: "var(--text-secondary)",
          fontWeight: 600
        }}>
          <label style={{ display: "flex", alignItems: "center", gap: "8px", cursor: "pointer" }}>
            <input
              type="checkbox"
              checked={companies.length > 0 && selectedIds.length === companies.length}
              onChange={handleSelectAll}
            />
            <span>Select All Visible ({companies.length})</span>
          </label>
          <span style={{ fontFamily: "monospace", fontWeight: 700 }}>{selectedIds.length} selected for import</span>
        </div>

        <div style={{ display: "flex", flexDirection: "column" }}>
          {loading ? (
            <p style={{ textAlign: "center", padding: "48px 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              Searching company intelligence registry...
            </p>
          ) : companies.length === 0 ? (
            <p style={{ textAlign: "center", padding: "48px 0", fontSize: "0.8125rem", color: "var(--text-muted)" }}>
              No matching enterprise companies found. Click "+ Add Company" to create one.
            </p>
          ) : (
            companies.map((comp) => {
              const isSelected = selectedIds.includes(comp.id);
              return (
                <div
                  key={comp.id}
                  onClick={() => handleSelectToggle(comp.id)}
                  style={{
                    padding: "16px 20px",
                    borderBottom: "1px solid var(--border-subtle)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    background: isSelected ? "var(--cyan-light)" : "var(--bg-surface)",
                    cursor: "pointer",
                    transition: "all 0.15s ease",
                    gap: "16px"
                  }}
                  onMouseOver={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "var(--bg-surface-hover)";
                  }}
                  onMouseOut={(e) => {
                    if (!isSelected) e.currentTarget.style.background = "var(--bg-surface)";
                  }}
                >
                  <div style={{ display: "flex", alignItems: "flex-start", gap: "12px", flex: 1 }}>
                    <input
                      type="checkbox"
                      checked={isSelected}
                      onChange={() => {}}
                      style={{ marginTop: "4px" }}
                    />
                    <div style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1 }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                        <h4 style={{ fontSize: "0.9375rem", fontWeight: 800, color: "var(--text-primary)" }}>
                          {comp.legal_name}
                        </h4>
                        <span className="badge badge-neutral" style={{ fontSize: "0.625rem" }}>
                          {comp.company_type || "Private Ltd"}
                        </span>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "12px", flexWrap: "wrap", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {comp.cin && (
                          <span style={{ fontFamily: "monospace" }}>
                            <strong>CIN:</strong> {comp.cin}
                          </span>
                        )}
                        {comp.registration_number && (
                          <span style={{ fontFamily: "monospace" }}>
                            <strong>Reg No:</strong> {comp.registration_number}
                          </span>
                        )}
                        {comp.gst_number && (
                          <span style={{ fontFamily: "monospace", color: "var(--primary-dark)" }}>
                            <strong>GST:</strong> {comp.gst_number}
                          </span>
                        )}
                        {comp.industry && <span>• {comp.industry}</span>}
                      </div>

                      {/* Contact & Location Details */}
                      <div style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap", fontSize: "0.6875rem", color: "var(--text-muted)", marginTop: "2px" }}>
                        {(comp.city || comp.state || comp.postal_code || comp.address) && (
                          <span style={{ display: "flex", alignItems: "center", gap: "4px", color: "var(--cyan-dark)", fontWeight: 600 }}>
                            <MapPin style={{ width: "12px", height: "12px" }} />
                            {[comp.address, comp.city, comp.state, comp.postal_code].filter(Boolean).join(", ")}
                          </span>
                        )}
                        {comp.phone && (
                          <a
                            href={getCallUrl(comp.phone)}
                            title={`Call (+91 ${format10DigitPhone(comp.phone)})`}
                            style={{ display: "flex", alignItems: "center", gap: "4px", color: "inherit", textDecoration: "none" }}
                          >
                            <Phone style={{ width: "11px", height: "11px", color: "var(--emerald)" }} />
                            <span>{format10DigitPhone(comp.phone)}</span>
                          </a>
                        )}
                        {comp.email && (
                          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                            <Mail style={{ width: "11px", height: "11px" }} />
                            {comp.email}
                          </span>
                        )}
                        {comp.website && (
                          <span style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                            <Globe style={{ width: "11px", height: "11px" }} />
                            <a href={comp.website.startsWith("http") ? comp.website : `https://${comp.website}`} target="_blank" rel="noreferrer" style={{ color: "var(--primary)" }} onClick={(e) => e.stopPropagation()}>
                              {comp.website}
                            </a>
                          </span>
                        )}
                        <span style={{ color: "var(--primary)", fontWeight: 600, marginLeft: "auto" }}>
                          {comp.contacts_count} Key People
                        </span>
                      </div>
                    </div>
                  </div>

                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "6px", flexShrink: 0 }}>
                    <span className="badge badge-open" style={{ fontSize: "0.6875rem" }}>
                      VERIFIED PROFILE
                    </span>
                    {canManage && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setEditingCompany(comp);
                        }}
                        className="btn btn-secondary"
                        style={{
                          padding: "4px 10px",
                          fontSize: "0.75rem",
                          display: "flex",
                          alignItems: "center",
                          gap: "4px",
                          borderRadius: "6px",
                          background: "var(--bg-surface)",
                          border: "1px solid var(--border-color)",
                        }}
                        title="Edit Enterprise Record"
                      >
                        ✏️ Edit
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Add Single Company Modal (UUID is assigned internally, never exposed to user) */}
      {showAddModal && (
        <div style={{
          position: "fixed",
          inset: 0,
          background: "rgba(15, 23, 42, 0.65)",
          backdropFilter: "blur(4px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 9999,
          padding: "16px"
        }}>
          <div className="card" style={{ width: "100%", maxWidth: "680px", maxHeight: "90vh", overflowY: "auto", padding: "24px" }}>
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", borderBottom: "1px solid var(--border-subtle)", paddingBottom: "12px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div style={{ width: "36px", height: "36px", borderRadius: "8px", background: "var(--cyan-light)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                  <Building2 style={{ width: "20px", height: "20px", color: "var(--cyan-dark)" }} />
                </div>
                <div>
                  <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>
                    Add Company to Intelligence Registry
                  </h3>
                  <p style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                    Provide company registry details, CIN, GST, address, and contact information
                  </p>
                </div>
              </div>
              <button onClick={() => setShowAddModal(false)} style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}>
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            {formError && (
              <div style={{ padding: "10px 14px", borderRadius: "8px", background: "var(--rose-light)", color: "var(--rose-dark)", fontSize: "0.75rem", fontWeight: 600, marginBottom: "14px" }}>
                {formError}
              </div>
            )}

            <form onSubmit={handleCreateCompany} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {/* Row 1: Company Name & Industry */}
              <div style={{ display: "grid", gridTemplateColumns: "1.2fr 0.8fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Company Name <span style={{ color: "var(--rose)" }}>*</span>
                  </label>
                  <input
                    type="text"
                    required
                    value={formData.legal_name}
                    onChange={(e) => setFormData({ ...formData, legal_name: e.target.value })}
                    placeholder="e.g. Acme Technologies Pvt Ltd"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-legal-name"
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Industry / Sector
                  </label>
                  <input
                    type="text"
                    value={formData.industry || ""}
                    onChange={(e) => setFormData({ ...formData, industry: e.target.value })}
                    placeholder="e.g. Information Technology, Aerospace"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-industry"
                  />
                </div>
              </div>

              {/* Row 2: CIN, Registration Number & GST */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    CIN (If available)
                  </label>
                  <input
                    type="text"
                    value={formData.cin || ""}
                    onChange={(e) => setFormData({ ...formData, cin: e.target.value.toUpperCase() })}
                    placeholder="e.g. U72200MH2020PTC123456"
                    className="input-text"
                    style={{ width: "100%", fontFamily: "monospace", fontSize: "0.75rem" }}
                    id="company-cin"
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Registration Number
                  </label>
                  <input
                    type="text"
                    value={formData.registration_number || ""}
                    onChange={(e) => setFormData({ ...formData, registration_number: e.target.value })}
                    placeholder="e.g. REG-987654"
                    className="input-text"
                    style={{ width: "100%", fontFamily: "monospace", fontSize: "0.75rem" }}
                    id="company-reg-number"
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    GST Number
                  </label>
                  <input
                    type="text"
                    value={formData.gst_number || ""}
                    onChange={(e) => setFormData({ ...formData, gst_number: e.target.value.toUpperCase() })}
                    placeholder="e.g. 27AAAAA0000A1Z5"
                    className="input-text"
                    style={{ width: "100%", fontFamily: "monospace", fontSize: "0.75rem" }}
                    id="company-gst-number"
                  />
                </div>
              </div>

              {/* Row 3: Address */}
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Address
                </label>
                <input
                  type="text"
                  value={formData.address || ""}
                  onChange={(e) => setFormData({ ...formData, address: e.target.value })}
                  placeholder="Street / Office Suite / Building Name"
                  className="input-text"
                  style={{ width: "100%" }}
                  id="company-address"
                />
              </div>

              {/* Row 4: City, Pincode, State */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    City
                  </label>
                  <input
                    type="text"
                    value={formData.city || ""}
                    onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                    placeholder="e.g. Mumbai, Pune"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-city"
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Pincode
                  </label>
                  <input
                    type="text"
                    value={formData.postal_code || ""}
                    onChange={(e) => setFormData({ ...formData, postal_code: e.target.value })}
                    placeholder="e.g. 411001"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-pincode"
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    State
                  </label>
                  <input
                    type="text"
                    value={formData.state || ""}
                    onChange={(e) => setFormData({ ...formData, state: e.target.value })}
                    placeholder="e.g. Maharashtra"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-state"
                  />
                </div>
              </div>

              {/* Row 5: Website, Email, Company Contact Number */}
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Website
                  </label>
                  <input
                    type="text"
                    value={formData.website || ""}
                    onChange={(e) => setFormData({ ...formData, website: e.target.value })}
                    placeholder="https://acme.com"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-website"
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Email
                  </label>
                  <input
                    type="email"
                    value={formData.email || ""}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    placeholder="contact@acme.com"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-email"
                  />
                </div>

                <div>
                  <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                    Company Contact Number
                  </label>
                  <input
                    type="tel"
                    maxLength={10}
                    value={formData.phone || ""}
                    onChange={(e) => setFormData({ ...formData, phone: cleanPhoneInput(e.target.value) })}
                    placeholder="e.g. 9876543210 (10 digits)"
                    className="input-text"
                    style={{ width: "100%" }}
                    id="company-contact-number"
                  />
                </div>
              </div>

              {/* Row 6: Company Type */}
              <div>
                <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", marginBottom: "4px" }}>
                  Company Type
                </label>
                <select
                  value={formData.company_type || "Private Limited"}
                  onChange={(e) => setFormData({ ...formData, company_type: e.target.value })}
                  className="input-text"
                  style={{ width: "100%" }}
                  id="company-type"
                >
                  <option value="Private Limited">Private Limited</option>
                  <option value="Public Limited">Public Limited</option>
                  <option value="LLP">Limited Liability Partnership (LLP)</option>
                  <option value="Sole Proprietorship">Sole Proprietorship</option>
                  <option value="Partnership">Partnership Firm</option>
                  <option value="Startup / Other">Startup / Other</option>
                </select>
              </div>

              {/* Actions */}
              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "12px", paddingTop: "12px", borderTop: "1px solid var(--border-subtle)" }}>
                <button
                  type="button"
                  onClick={() => setShowAddModal(false)}
                  className="btn-secondary"
                  disabled={saving}
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  className="btn-primary"
                  disabled={saving}
                  id="submit-company-btn"
                >
                  {saving ? "Saving Company..." : "Create Company"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {showImportModal && (
        <ImportModal
          jobType="GLOBAL_COMPANIES"
          onClose={() => setShowImportModal(false)}
          onSuccess={() => {
            loadGlobalCompanies();
            setSuccessMsg("Company database import completed successfully!");
            setTimeout(() => setSuccessMsg(null), 4000);
          }}
        />
      )}

      {editingCompany && (
        <EditCompanyModal
          company={editingCompany}
          isOpen={Boolean(editingCompany)}
          onClose={() => setEditingCompany(null)}
          onSaved={(updated) => {
            setCompanies((prev) => prev.map((c) => (c.id === updated.id ? updated : c)));
            setSuccessMsg(`Enterprise record "${updated.legal_name}" updated successfully!`);
            setTimeout(() => setSuccessMsg(null), 4000);
          }}
        />
      )}
    </div>
  );
};
