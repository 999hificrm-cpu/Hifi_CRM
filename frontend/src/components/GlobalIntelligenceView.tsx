import React, { useState, useEffect } from "react";
import {
  api,
  CompanyWithPeople,
  LinkedPerson,
  GlobalIntelligenceResponse,
} from "../services/api";
import { openGmail } from "../utils/mailHelper";
import { format10DigitPhone, getCallUrl } from "../utils/phoneHelper";
import { EditCompanyModal } from "./EditCompanyModal";
import { EditPersonModal } from "./EditPersonModal";
import {
  BrainCircuit,
  Building2,
  Users,
  Search,
  Download,
  Check,
  CheckCircle2,
  MapPin,
  Phone,
  Mail,
  Globe,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  ShieldCheck,
  Briefcase,
  X,
  Layers,
  Sparkles,
  LayoutGrid,
  Columns3,
  UserCheck
} from "lucide-react";

interface GlobalIntelligenceViewProps {
  isOrgAdmin?: boolean;
  currentUser?: any;
}

export const GlobalIntelligenceView: React.FC<GlobalIntelligenceViewProps> = ({ isOrgAdmin, currentUser: propUser }) => {
  const storedUser = localStorage.getItem("jarvis_user");
  const currentUser = propUser || (storedUser ? JSON.parse(storedUser) : null);
  const isSuperAdmin = currentUser?.is_super_admin ?? !isOrgAdmin;
  const canManage = isSuperAdmin || currentUser?.is_data_entry || currentUser?.platform_role === "DATA_ENTRY" || currentUser?.tenant_role === "DATA_ENTRY";
  const orgName = currentUser?.organization?.name || "Your Organization";
  const orgId = currentUser?.organization_id || currentUser?.organization?.id;

  const [intelligenceData, setIntelligenceData] = useState<GlobalIntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [editingCompany, setEditingCompany] = useState<any | null>(null);
  const [editingPerson, setEditingPerson] = useState<any | null>(null);
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<"ALL" | "WITH_PEOPLE" | "WITHOUT_PEOPLE">("ALL");
  const [cityFilter, setCityFilter] = useState("");
  const [industryFilter, setIndustryFilter] = useState("ALL");
  
  // View mode switcher: DUAL (side-by-side), COMPANIES (company column only), PEOPLE (people column only)
  const [activeColumnView, setActiveColumnView] = useState<"DUAL" | "COMPANIES" | "PEOPLE">("DUAL");
  
  const [copiedEmailId, setCopiedEmailId] = useState<string | null>(null);

  const handleCopyEmail = (email: string, id: string) => {
    if (!email) return;
    navigator.clipboard.writeText(email);
    setCopiedEmailId(id);
    setTimeout(() => setCopiedEmailId(null), 2000);
  };

  // Selection states
  const [selectedCompanyIds, setSelectedCompanyIds] = useState<string[]>([]);
  const [selectedPeopleIds, setSelectedPeopleIds] = useState<string[]>([]);
  
  // Expanded companies state (set of company IDs)
  const [expandedCompanies, setExpandedCompanies] = useState<Set<string>>(new Set());

  // Pull modal state
  const [showPullModal, setShowPullModal] = useState(false);
  const [pullTargetType, setPullTargetType] = useState<"COMPANIES" | "PEOPLE">("COMPANIES");
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [targetOrgId, setTargetOrgId] = useState("");
  const [pulling, setPulling] = useState(false);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  useEffect(() => {
    loadIntelligence();
    loadOrganizations();
  }, [filterType, industryFilter]);

  const loadIntelligence = async () => {
    setLoading(true);
    try {
      const data = await api.getGlobalIntelligence({
        search: searchTerm,
        filter_type: filterType,
        city: cityFilter,
        industry: industryFilter !== "ALL" ? industryFilter : undefined,
      });
      setIntelligenceData(data);

      // Auto-expand companies that have people for immediate visibility
      const autoExpanded = new Set<string>();
      data.companies.forEach((c) => {
        if (c.people_count > 0) {
          autoExpanded.add(c.id);
        }
      });
      setExpandedCompanies(autoExpanded);
    } catch (err) {
      console.error("Failed to load Global Intelligence data:", err);
    } finally {
      setLoading(false);
    }
  };

  const loadOrganizations = async () => {
    if (!isSuperAdmin) {
      if (orgId) setTargetOrgId(orgId);
      return;
    }
    try {
      const orgs = await api.getOrganizations();
      setOrganizations(orgs || []);
      if (orgs && orgs.length > 0) {
        setTargetOrgId(orgs[0].id);
      }
    } catch (err) {
      console.error("Failed to load organizations:", err);
    }
  };

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadIntelligence();
  };

  const handleClearFilters = () => {
    setSearchTerm("");
    setCityFilter("");
    setIndustryFilter("ALL");
    setFilterType("ALL");
    setTimeout(() => {
      api.getGlobalIntelligence({ filter_type: "ALL" }).then((data) => {
        setIntelligenceData(data);
        const autoExpanded = new Set<string>();
        data.companies.forEach((c) => {
          if (c.people_count > 0) autoExpanded.add(c.id);
        });
        setExpandedCompanies(autoExpanded);
      });
    }, 50);
  };

  const toggleExpandCompany = (id: string) => {
    setExpandedCompanies((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  };

  const handleExpandAll = () => {
    if (!intelligenceData) return;
    const allIds = new Set(intelligenceData.companies.map((c) => c.id));
    setExpandedCompanies(allIds);
  };

  const handleCollapseAll = () => {
    setExpandedCompanies(new Set());
  };

  const handleSelectCompany = (id: string) => {
    setSelectedCompanyIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAllCompanies = () => {
    if (!intelligenceData) return;
    if (selectedCompanyIds.length === intelligenceData.companies.length) {
      setSelectedCompanyIds([]);
    } else {
      setSelectedCompanyIds(intelligenceData.companies.map((c) => c.id));
    }
  };

  const handleSelectPerson = (id: string) => {
    setSelectedPeopleIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const handleSelectAllPeople = () => {
    if (!intelligenceData) return;
    if (selectedPeopleIds.length === intelligenceData.unlinked_people.length) {
      setSelectedPeopleIds([]);
    } else {
      setSelectedPeopleIds(intelligenceData.unlinked_people.map((p) => p.id));
    }
  };

  const handleOpenPullModal = (type: "COMPANIES" | "PEOPLE") => {
    setPullTargetType(type);
    setShowPullModal(true);
  };

  const handlePullConfirm = async () => {
    if (isSuperAdmin) return;
    setPulling(true);
    try {
      const targetId = orgId || targetOrgId;
      if (pullTargetType === "COMPANIES") {
        if (selectedCompanyIds.length === 0) return;
        const res = await api.pullGlobalCompanies(selectedCompanyIds, targetId || undefined);
        setSuccessMsg(
          `Successfully conserved ${res.pulled_companies} enterprise(s) and created ${res.created_leads} CRM opportunities in ${orgName}!`
        );
        setSelectedCompanyIds([]);
      } else {
        if (selectedPeopleIds.length === 0) return;
        const res = await api.pullGlobalPeople({
          global_people_ids: selectedPeopleIds,
          target_organization_id: targetId || undefined,
        });
        setSuccessMsg(
          `Successfully conserved ${res.pulled_people} independent lead(s) into ${orgName} CRM pipeline!`
        );
        setSelectedPeopleIds([]);
      }
      setShowPullModal(false);
      setTimeout(() => setSuccessMsg(null), 6000);
      loadIntelligence();
    } catch (err: any) {
      alert(err.message || "Failed to pull records to CRM.");
    } finally {
      setPulling(false);
    }
  };

  const companies = intelligenceData?.companies || [];
  const unlinkedPeople = intelligenceData?.unlinked_people || [];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
      {/* View Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <div
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "10px",
                background: "linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                color: "#ffffff",
                boxShadow: "0 4px 12px rgba(99, 102, 241, 0.25)",
              }}
            >
              <BrainCircuit style={{ width: "20px", height: "20px" }} />
            </div>
            <div>
              <h2
                style={{
                  fontSize: "1.375rem",
                  fontWeight: 800,
                  color: "var(--text-primary)",
                  letterSpacing: "-0.02em",
                  margin: 0,
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                {isSuperAdmin ? "Global Intelligence Graph" : "Global Registry & Lead Discovery"}
                <span
                  style={{
                    fontSize: "0.6875rem",
                    fontWeight: 700,
                    padding: "2px 8px",
                    borderRadius: "20px",
                    background: isSuperAdmin ? "rgba(99, 102, 241, 0.12)" : "rgba(6, 182, 212, 0.12)",
                    color: isSuperAdmin ? "var(--primary)" : "var(--cyan)",
                    border: isSuperAdmin ? "1px solid rgba(99, 102, 241, 0.25)" : "1px solid rgba(6, 182, 212, 0.25)",
                    letterSpacing: "0.02em",
                  }}
                >
                  {isSuperAdmin ? "Dual Columns: Enterprises + Independent Leads" : `Exclusive Lead Conservation Active • ${orgName}`}
                </span>
              </h2>
              <p
                style={{
                  fontSize: "0.8125rem",
                  color: "var(--text-secondary)",
                  marginTop: "2px",
                  marginBottom: 0,
                }}
              >
                {isSuperAdmin
                  ? "Unified intelligence correlating enterprise companies with verified key decision-makers & leadership teams across India"
                  : "Discover verified corporate accounts and decision makers. Pull and conserve opportunities directly into your CRM pipeline."}
              </p>
            </div>
          </div>
        </div>

        {/* Top Actions & Pull triggers (Only for ORG Admin) */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
          {!isSuperAdmin && selectedCompanyIds.length > 0 && (
            <button
              onClick={() => handleOpenPullModal("COMPANIES")}
              className="btn-primary"
              style={{
                background: "linear-gradient(135deg, #0891b2, #0e7490)",
                borderColor: "#155e75",
                fontSize: "0.8125rem",
              }}
              id="pull-companies-btn"
            >
              <Download style={{ width: "15px", height: "15px" }} />
              Conserve {selectedCompanyIds.length} Companies to My CRM
            </button>
          )}

          {!isSuperAdmin && selectedPeopleIds.length > 0 && (
            <button
              onClick={() => handleOpenPullModal("PEOPLE")}
              className="btn-primary"
              style={{
                background: "linear-gradient(135deg, #059669, #047857)",
                borderColor: "#065f46",
                fontSize: "0.8125rem",
              }}
              id="pull-people-btn"
            >
              <Download style={{ width: "15px", height: "15px" }} />
              Conserve {selectedPeopleIds.length} Leads to My CRM
            </button>
          )}

          <div style={{ display: "flex", gap: "6px" }}>
            <button
              onClick={handleExpandAll}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "6px 12px" }}
              title="Expand all company rosters"
            >
              Expand All
            </button>
            <button
              onClick={handleCollapseAll}
              className="btn-secondary"
              style={{ fontSize: "0.75rem", padding: "6px 12px" }}
              title="Collapse all company rosters"
            >
              Collapse All
            </button>
          </div>
        </div>
      </div>

      {/* Success Notification Banner */}
      {successMsg && (
        <div
          style={{
            padding: "12px 16px",
            borderRadius: "8px",
            background: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "var(--emerald)",
            fontSize: "0.8125rem",
            fontWeight: 600,
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <CheckCircle2 style={{ width: "18px", height: "18px", flexShrink: 0 }} />
          <span>{successMsg}</span>
        </div>
      )}

      {/* 4 High-Level Intelligence KPI Cards (Reasonable metrics, No Revenue) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))",
          gap: "14px",
        }}
      >
        {/* Total Enterprises */}
        <div className="card" style={{ padding: "16px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Total Enterprises
            </span>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(6, 182, 212, 0.1)",
                color: "var(--cyan)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Building2 style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "8px" }}>
            {intelligenceData?.total_companies ?? "..."}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px" }}>
            Active verified legal entities
          </div>
        </div>

        {/* Total People Leads */}
        <div className="card" style={{ padding: "16px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Total People Leads
            </span>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(99, 102, 241, 0.1)",
                color: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <Users style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)", marginTop: "8px" }}>
            {intelligenceData?.total_people ?? "..."}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px" }}>
            {intelligenceData?.linked_people_count ?? 0} mapped, {intelligenceData?.unlinked_people_count ?? 0} independent
          </div>
        </div>

        {/* Linked Decision-Makers */}
        <div className="card" style={{ padding: "16px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Linked Decision-Makers
            </span>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(16, 185, 129, 0.1)",
                color: "var(--emerald)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <CheckCircle2 style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--emerald)", marginTop: "8px" }}>
            {intelligenceData?.linked_people_count ?? "..."}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px" }}>
            Connected across {intelligenceData?.companies_with_people_count ?? 0} enterprises
          </div>
        </div>

        {/* Direct Outreach Reachability (Reasonable Contact Metric) */}
        <div className="card" style={{ padding: "16px 20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-secondary)", textTransform: "uppercase" }}>
              Direct Contact Coverage
            </span>
            <div
              style={{
                width: "32px",
                height: "32px",
                borderRadius: "8px",
                background: "rgba(245, 158, 11, 0.1)",
                color: "var(--amber)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
              }}
            >
              <ShieldCheck style={{ width: "16px", height: "16px" }} />
            </div>
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--amber)", marginTop: "8px" }}>
            {intelligenceData?.direct_reach_percentage ? `${intelligenceData.direct_reach_percentage}%` : "100%"}
          </div>
          <div style={{ fontSize: "0.75rem", color: "var(--text-secondary)", marginTop: "4px" }}>
            Verified direct phone & email reach
          </div>
        </div>
      </div>

      {/* Unified Search and Filter Toolbar */}
      <div
        className="card"
        style={{
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          gap: "14px",
        }}
      >
        <form
          onSubmit={handleSearchSubmit}
          style={{
            display: "flex",
            gap: "10px",
            flexWrap: "wrap",
          }}
        >
          <div style={{ position: "relative", flex: "1 1 320px" }}>
            <Search
              style={{
                position: "absolute",
                left: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                width: "16px",
                height: "16px",
                color: "var(--text-muted)",
              }}
            />
            <input
              type="text"
              placeholder="Search by company name, CIN, GST, person name, designation, email, phone..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="input-field"
              style={{ paddingLeft: "36px", width: "100%", fontSize: "0.8125rem" }}
              id="global-intel-search-input"
            />
          </div>

          <div style={{ position: "relative", width: "180px" }}>
            <MapPin
              style={{
                position: "absolute",
                left: "12px",
                top: "50%",
                transform: "translateY(-50%)",
                width: "14px",
                height: "14px",
                color: "var(--text-muted)",
              }}
            />
            <input
              type="text"
              placeholder="City (e.g. Mumbai)"
              value={cityFilter}
              onChange={(e) => setCityFilter(e.target.value)}
              className="input-field"
              style={{ paddingLeft: "34px", width: "100%", fontSize: "0.8125rem" }}
            />
          </div>

          <select
            value={industryFilter}
            onChange={(e) => setIndustryFilter(e.target.value)}
            className="input-field"
            style={{ width: "170px", fontSize: "0.8125rem" }}
          >
            <option value="ALL">All Industries</option>
            <option value="Information Technology">IT & Software</option>
            <option value="Engineering & Heavy Dynamics">Engineering</option>
            <option value="Financial Services">Financial Services</option>
            <option value="Healthcare & Life Sciences">Healthcare</option>
            <option value="Logistics & Supply Chain">Logistics</option>
            <option value="Manufacturing & Metals">Manufacturing</option>
            <option value="Consumer Goods & Retail">Retail & FMCG</option>
          </select>

          <button
            type="submit"
            className="btn-primary"
            style={{ fontSize: "0.8125rem", padding: "8px 16px" }}
            id="global-intel-search-btn"
          >
            <Search style={{ width: "15px", height: "15px" }} />
            Search
          </button>

          {(searchTerm || cityFilter || industryFilter !== "ALL" || filterType !== "ALL") && (
            <button
              type="button"
              onClick={handleClearFilters}
              className="btn-secondary"
              style={{ fontSize: "0.8125rem", padding: "8px 12px" }}
            >
              Clear
            </button>
          )}
        </form>

        {/* Filter Tabs & Column Layout Switcher */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: "10px",
            borderTop: "1px solid var(--border-color)",
            paddingTop: "12px",
          }}
        >
          {/* Filter Tabs for Companies */}
          <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
            <button
              onClick={() => setFilterType("ALL")}
              style={{
                padding: "5px 12px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                border: "1px solid",
                borderColor: filterType === "ALL" ? "var(--primary)" : "var(--border-color)",
                background: filterType === "ALL" ? "rgba(99, 102, 241, 0.1)" : "transparent",
                color: filterType === "ALL" ? "var(--primary)" : "var(--text-secondary)",
                cursor: "pointer",
              }}
              id="filter-tab-all"
            >
              All Enterprises ({intelligenceData?.total_companies ?? 0})
            </button>
            <button
              onClick={() => setFilterType("WITH_PEOPLE")}
              style={{
                padding: "5px 12px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                border: "1px solid",
                borderColor: filterType === "WITH_PEOPLE" ? "var(--emerald)" : "var(--border-color)",
                background: filterType === "WITH_PEOPLE" ? "rgba(16, 185, 129, 0.1)" : "transparent",
                color: filterType === "WITH_PEOPLE" ? "var(--emerald)" : "var(--text-secondary)",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                gap: "5px",
              }}
              id="filter-tab-with-people"
            >
              <Users style={{ width: "13px", height: "13px" }} />
              With Decision-Makers ({intelligenceData?.companies_with_people_count ?? 0})
            </button>
            <button
              onClick={() => setFilterType("WITHOUT_PEOPLE")}
              style={{
                padding: "5px 12px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                border: "1px solid",
                borderColor: filterType === "WITHOUT_PEOPLE" ? "var(--amber)" : "var(--border-color)",
                background: filterType === "WITHOUT_PEOPLE" ? "rgba(245, 158, 11, 0.1)" : "transparent",
                color: filterType === "WITHOUT_PEOPLE" ? "var(--amber)" : "var(--text-secondary)",
                cursor: "pointer",
              }}
              id="filter-tab-without-people"
            >
              Awaiting Leadership (
              {Math.max(
                0,
                (intelligenceData?.total_companies ?? 0) -
                  (intelligenceData?.companies_with_people_count ?? 0)
              )}
              )
            </button>
          </div>

          {/* View Mode Column Switcher */}
          <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
            <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-muted)" }}>
              View:
            </span>
            <button
              onClick={() => setActiveColumnView("DUAL")}
              style={{
                padding: "5px 10px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                border: "1px solid",
                borderColor: activeColumnView === "DUAL" ? "var(--primary)" : "var(--border-color)",
                background: activeColumnView === "DUAL" ? "rgba(99, 102, 241, 0.15)" : "transparent",
                color: activeColumnView === "DUAL" ? "var(--primary)" : "var(--text-secondary)",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
              }}
              id="view-toggle-dual"
            >
              <LayoutGrid style={{ width: "13px", height: "13px" }} />
              Dual Columns
            </button>

            <button
              onClick={() => setActiveColumnView("COMPANIES")}
              style={{
                padding: "5px 10px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                border: "1px solid",
                borderColor: activeColumnView === "COMPANIES" ? "var(--primary)" : "var(--border-color)",
                background: activeColumnView === "COMPANIES" ? "rgba(99, 102, 241, 0.15)" : "transparent",
                color: activeColumnView === "COMPANIES" ? "var(--primary)" : "var(--text-secondary)",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
              }}
              id="view-toggle-companies"
            >
              <Building2 style={{ width: "13px", height: "13px" }} />
              Companies ({companies.length})
            </button>

            <button
              onClick={() => setActiveColumnView("PEOPLE")}
              style={{
                padding: "5px 10px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                border: "1px solid",
                borderColor: activeColumnView === "PEOPLE" ? "var(--emerald)" : "var(--border-color)",
                background: activeColumnView === "PEOPLE" ? "rgba(16, 185, 129, 0.15)" : "transparent",
                color: activeColumnView === "PEOPLE" ? "var(--emerald)" : "var(--text-secondary)",
                cursor: "pointer",
                display: "inline-flex",
                alignItems: "center",
                gap: "5px",
              }}
              id="view-toggle-people"
            >
              <UserCheck style={{ width: "13px", height: "13px" }} />
              Independent Leads ({unlinkedPeople.length})
            </button>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div
          className="card"
          style={{
            padding: "40px",
            textAlign: "center",
            color: "var(--text-secondary)",
            fontSize: "0.875rem",
          }}
        >
          <div
            style={{
              display: "inline-block",
              width: "24px",
              height: "24px",
              border: "3px solid var(--border-color)",
              borderTopColor: "var(--primary)",
              borderRadius: "50%",
              animation: "spin 0.8s linear infinite",
              marginBottom: "12px",
            }}
          />
          <div>Synthesizing Enterprise + People Intelligence Graph...</div>
        </div>
      )}

      {/* Main Dual-Column / Partition Content Area */}
      {!loading && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns:
              activeColumnView === "DUAL"
                ? "minmax(0, 1.15fr) minmax(0, 0.85fr)"
                : "minmax(0, 1fr)",
            gap: "20px",
            alignItems: "start",
          }}
        >
          {/* ========================================================================= */}
          {/* COLUMN 1: ENTERPRISES & ASSOCIATED LEADERSHIP TEAMS                       */}
          {/* ========================================================================= */}
          {(activeColumnView === "DUAL" || activeColumnView === "COMPANIES") && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {/* Column Header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <Building2 style={{ width: "16px", height: "16px", color: "var(--cyan)" }} />
                  <span style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>
                    Registered Enterprises & Associated Teams
                  </span>
                  <span
                    style={{
                      fontSize: "0.6875rem",
                      fontWeight: 700,
                      padding: "1px 7px",
                      borderRadius: "10px",
                      background: "rgba(6, 182, 212, 0.1)",
                      color: "var(--cyan)",
                    }}
                  >
                    {companies.length}
                  </span>
                </div>

                <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                  <input
                    type="checkbox"
                    checked={companies.length > 0 && selectedCompanyIds.length === companies.length}
                    onChange={handleSelectAllCompanies}
                    style={{ cursor: "pointer" }}
                  />
                  <span>Select All</span>
                </label>
              </div>

              {/* Companies Empty State */}
              {companies.length === 0 && (
                <div className="card" style={{ padding: "32px 20px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                  No companies found matching current filters.
                </div>
              )}

              {/* Companies Cards */}
              {companies.map((company) => {
                const isExpanded = expandedCompanies.has(company.id);
                const isSelected = selectedCompanyIds.includes(company.id);
                const hasPeople = company.associated_people && company.associated_people.length > 0;

                return (
                  <div
                    key={company.id}
                    className="card"
                    style={{
                      padding: "0",
                      overflow: "hidden",
                      border: isSelected
                        ? "1.5px solid var(--primary)"
                        : "1px solid var(--border-color)",
                      boxShadow: isSelected
                        ? "0 4px 14px rgba(99, 102, 241, 0.12)"
                        : "none",
                      transition: "all 0.2s ease",
                    }}
                  >
                    {/* Company Header Row */}
                    <div
                      style={{
                        padding: "14px 18px",
                        background: isSelected
                          ? "rgba(99, 102, 241, 0.03)"
                          : "var(--bg-surface)",
                        display: "flex",
                        alignItems: "flex-start",
                        justifyContent: "space-between",
                        gap: "14px",
                        flexWrap: "wrap",
                      }}
                    >
                      {/* Left: Checkbox + Identity & Tags */}
                      <div style={{ display: "flex", alignItems: "flex-start", gap: "10px", flex: "1 1 320px" }}>
                        <input
                          type="checkbox"
                          checked={isSelected}
                          onChange={() => handleSelectCompany(company.id)}
                          style={{ marginTop: "4px", cursor: "pointer" }}
                        />

                        <div style={{ display: "flex", flexDirection: "column", gap: "4px", flex: 1 }}>
                          <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                            <span
                              style={{
                                fontSize: "0.9375rem",
                                fontWeight: 800,
                                color: "var(--text-primary)",
                                letterSpacing: "-0.01em",
                              }}
                            >
                              {company.legal_name}
                            </span>

                            {company.display_name && company.display_name !== company.legal_name && (
                              <span
                                style={{
                                  fontSize: "0.75rem",
                                  fontWeight: 600,
                                  color: "var(--text-muted)",
                                }}
                              >
                                ({company.display_name})
                              </span>
                            )}

                            {company.company_type && (
                              <span
                                style={{
                                  fontSize: "0.625rem",
                                  fontWeight: 600,
                                  padding: "2px 6px",
                                  borderRadius: "10px",
                                  background: "rgba(6, 182, 212, 0.1)",
                                  color: "var(--cyan)",
                                  border: "1px solid rgba(6, 182, 212, 0.2)",
                                }}
                              >
                                {company.company_type}
                              </span>
                            )}

                            {company.industry && (
                              <span
                                style={{
                                  fontSize: "0.625rem",
                                  fontWeight: 600,
                                  padding: "2px 6px",
                                  borderRadius: "10px",
                                  background: "rgba(148, 163, 184, 0.1)",
                                  color: "var(--text-secondary)",
                                  border: "1px solid var(--border-color)",
                                }}
                              >
                                {company.industry}
                              </span>
                            )}
                          </div>

                          {/* Location & Tax Identifiers (CIN, GST, Registration Number - NO UUID!) */}
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "12px",
                              flexWrap: "wrap",
                              fontSize: "0.6875rem",
                              color: "var(--text-secondary)",
                            }}
                          >
                            {(company.city || company.state) && (
                              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                <MapPin style={{ width: "12px", height: "12px", color: "var(--text-muted)" }} />
                                <span>
                                  {[company.city, company.state].filter(Boolean).join(", ")}
                                </span>
                              </div>
                            )}

                            {company.cin && (
                              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                <span style={{ fontWeight: 700, color: "var(--text-muted)" }}>CIN:</span>
                                <span style={{ fontFamily: "monospace", color: "var(--text-primary)" }}>
                                  {company.cin}
                                </span>
                              </div>
                            )}

                            {company.gst_number && (
                              <div style={{ display: "flex", alignItems: "center", gap: "4px" }}>
                                <span style={{ fontWeight: 700, color: "var(--text-muted)" }}>GST:</span>
                                <span style={{ fontFamily: "monospace", color: "var(--text-primary)" }}>
                                  {company.gst_number}
                                </span>
                              </div>
                            )}
                          </div>

                          {/* Corporate Contact Channels */}
                          <div
                            style={{
                              display: "flex",
                              alignItems: "center",
                              gap: "14px",
                              flexWrap: "wrap",
                              fontSize: "0.6875rem",
                              marginTop: "2px",
                            }}
                          >
                            {company.phone && (
                              <a
                                href={getCallUrl(company.phone)}
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "3px",
                                  color: "var(--primary)",
                                  textDecoration: "none",
                                  fontWeight: 600,
                                }}
                                title={`Call enterprise (+91 ${format10DigitPhone(company.phone)})`}
                              >
                                <Phone style={{ width: "11px", height: "11px" }} />
                                <span>{format10DigitPhone(company.phone)}</span>
                              </a>
                            )}

                            {company.email && (
                              <button
                                onClick={() => handleCopyEmail(company.email!, company.id)}
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "3px",
                                  color: "var(--primary)",
                                  background: "none",
                                  border: "none",
                                  padding: 0,
                                  cursor: "pointer",
                                  fontSize: "0.6875rem",
                                  fontWeight: 600,
                                }}
                                title="Copy email to clipboard"
                              >
                                <Mail style={{ width: "11px", height: "11px" }} />
                                <span>{copiedEmailId === company.id ? "Copied!" : company.email}</span>
                              </button>
                            )}

                            {company.website && (
                              <a
                                href={company.website.startsWith("http") ? company.website : `https://${company.website}`}
                                target="_blank"
                                rel="noopener noreferrer"
                                style={{
                                  display: "inline-flex",
                                  alignItems: "center",
                                  gap: "3px",
                                  color: "var(--text-secondary)",
                                  textDecoration: "none",
                                  fontWeight: 500,
                                }}
                              >
                                <Globe style={{ width: "11px", height: "11px" }} />
                                <span>Website</span>
                                <ExternalLink style={{ width: "9px", height: "9px" }} />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Right: People Badge & Expand Toggle */}
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexShrink: 0 }}>
                        {/* Pull Action for ORG Admin OR Status Tag & Edit Button for Super Admin/Data Entry */}
                        {!canManage ? (
                          <button
                            type="button"
                            onClick={() => {
                              setSelectedCompanyIds([company.id]);
                              handleOpenPullModal("COMPANIES");
                            }}
                            className="btn-primary"
                            style={{
                              padding: "4px 10px",
                              fontSize: "0.6875rem",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              background: "linear-gradient(135deg, #0891b2, #0e7490)",
                              borderColor: "#155e75",
                            }}
                            title="Conserve enterprise into your CRM pipeline"
                          >
                            <Download style={{ width: "11px", height: "11px" }} />
                            <span>Conserve to CRM</span>
                          </button>
                        ) : (
                          <div style={{ display: "inline-flex", alignItems: "center", gap: "6px" }}>
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                padding: "3px 8px",
                                borderRadius: "999px",
                                fontSize: "0.6875rem",
                                fontWeight: 700,
                                background: "rgba(16, 185, 129, 0.12)",
                                color: "var(--emerald)",
                                border: "1px solid rgba(16, 185, 129, 0.3)",
                              }}
                            >
                              <span>AVAILABLE</span>
                            </span>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingCompany(company);
                              }}
                              className="btn btn-secondary"
                              style={{
                                padding: "3px 8px",
                                fontSize: "0.7rem",
                                borderRadius: "6px",
                                border: "1px solid var(--border-color)",
                                background: "var(--bg-surface)",
                                cursor: "pointer",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "3px",
                              }}
                              title="Edit Enterprise Record"
                            >
                              ✏️ Edit
                            </button>
                          </div>
                        )}
                        <div
                          style={{
                            padding: "4px 8px",
                            borderRadius: "16px",
                            fontSize: "0.6875rem",
                            fontWeight: 700,
                            display: "flex",
                            alignItems: "center",
                            gap: "5px",
                            background: hasPeople
                              ? "rgba(16, 185, 129, 0.12)"
                              : "rgba(148, 163, 184, 0.1)",
                            color: hasPeople ? "var(--emerald)" : "var(--text-muted)",
                            border: hasPeople
                              ? "1px solid rgba(16, 185, 129, 0.3)"
                              : "1px solid var(--border-color)",
                          }}
                        >
                          <Users style={{ width: "12px", height: "12px" }} />
                          <span>
                            {company.people_count > 0
                              ? `${company.people_count} Decision-Maker${company.people_count > 1 ? "s" : ""}`
                              : "No Personnel Mapped"}
                          </span>
                        </div>

                        <button
                          onClick={() => toggleExpandCompany(company.id)}
                          className="btn-secondary"
                          style={{
                            fontSize: "0.6875rem",
                            padding: "4px 8px",
                            display: "flex",
                            alignItems: "center",
                            gap: "3px",
                          }}
                          title={isExpanded ? "Collapse executive roster" : "Expand executive roster"}
                        >
                          <span>{isExpanded ? "Hide" : "Roster"}</span>
                          {isExpanded ? (
                            <ChevronUp style={{ width: "12px", height: "12px" }} />
                          ) : (
                            <ChevronDown style={{ width: "12px", height: "12px" }} />
                          )}
                        </button>
                      </div>
                    </div>

                    {/* Expandable People Section Directly Under Company */}
                    {isExpanded && (
                      <div
                        style={{
                          background: "rgba(0, 0, 0, 0.02)",
                          borderTop: "1px solid var(--border-color)",
                          padding: "14px 18px",
                        }}
                      >
                        <div
                          style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "space-between",
                            marginBottom: "10px",
                          }}
                        >
                          <div
                            style={{
                              fontSize: "0.75rem",
                              fontWeight: 700,
                              color: "var(--text-primary)",
                              display: "flex",
                              alignItems: "center",
                              gap: "5px",
                            }}
                          >
                            <ShieldCheck style={{ width: "14px", height: "14px", color: "var(--primary)" }} />
                            Associated Leadership & Key Executives ({company.associated_people?.length || 0})
                          </div>
                          <span style={{ fontSize: "0.625rem", color: "var(--text-muted)" }}>
                            Direct outreach channels enabled
                          </span>
                        </div>

                        {/* If company has associated people */}
                        {hasPeople ? (
                          <div
                            style={{
                              display: "grid",
                              gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))",
                              gap: "10px",
                            }}
                          >
                            {company.associated_people.map((person) => {
                              const initials = person.full_name
                                .split(" ")
                                .filter(Boolean)
                                .map((p) => p[0])
                                .slice(0, 2)
                                .join("")
                                .toUpperCase();

                              return (
                                <div
                                  key={person.id}
                                  style={{
                                    background: "var(--bg-surface)",
                                    border: "1px solid var(--border-color)",
                                    borderRadius: "8px",
                                    padding: "10px 12px",
                                    display: "flex",
                                    flexDirection: "column",
                                    gap: "6px",
                                    boxShadow: "0 1px 3px rgba(0, 0, 0, 0.04)",
                                  }}
                                >
                                  {/* Top Row: Avatar + Name + Seniority Badge */}
                                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: "6px" }}>
                                    <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                                      <div
                                        style={{
                                          width: "28px",
                                          height: "28px",
                                          borderRadius: "50%",
                                          background: "linear-gradient(135deg, #4f46e5 0%, #06b6d4 100%)",
                                          color: "#ffffff",
                                          fontWeight: 700,
                                          fontSize: "0.6875rem",
                                          display: "flex",
                                          alignItems: "center",
                                          justifyContent: "center",
                                          flexShrink: 0,
                                        }}
                                      >
                                        {initials || "U"}
                                      </div>
                                      <div>
                                        <div style={{ fontSize: "0.8125rem", fontWeight: 700, color: "var(--text-primary)" }}>
                                          {person.full_name}
                                        </div>
                                        <div style={{ fontSize: "0.6875rem", fontWeight: 600, color: "var(--primary)" }}>
                                          {person.designation || "Executive"}
                                        </div>
                                      </div>
                                    </div>

                                    {person.seniority && (
                                      <span
                                        style={{
                                          fontSize: "0.5625rem",
                                          fontWeight: 700,
                                          padding: "2px 5px",
                                          borderRadius: "4px",
                                          background: "rgba(99, 102, 241, 0.1)",
                                          color: "var(--primary)",
                                          border: "1px solid rgba(99, 102, 241, 0.2)",
                                        }}
                                      >
                                        {person.seniority}
                                      </span>
                                    )}
                                  </div>

                                  {/* Department and Location */}
                                  <div
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      gap: "8px",
                                      fontSize: "0.625rem",
                                      color: "var(--text-secondary)",
                                    }}
                                  >
                                    {person.department && (
                                      <span style={{ display: "flex", alignItems: "center", gap: "2px" }}>
                                        <Briefcase style={{ width: "10px", height: "10px", color: "var(--text-muted)" }} />
                                        {person.department}
                                      </span>
                                    )}
                                    {(person.city || person.state) && (
                                      <span style={{ display: "flex", alignItems: "center", gap: "2px" }}>
                                        <MapPin style={{ width: "10px", height: "10px", color: "var(--text-muted)" }} />
                                        {[person.city, person.state].filter(Boolean).join(", ")}
                                      </span>
                                    )}
                                  </div>

                                  {/* Direct Contact Actions (Reasonable format, No Revenue) */}
                                  <div
                                    style={{
                                      display: "flex",
                                      alignItems: "center",
                                      justifyContent: "space-between",
                                      borderTop: "1px solid var(--border-color)",
                                      paddingTop: "6px",
                                      marginTop: "2px",
                                    }}
                                  >
                                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                      {person.phone && (
                                        <a
                                          href={getCallUrl(person.phone)}
                                          className="btn-secondary"
                                          style={{
                                            padding: "3px 6px",
                                            fontSize: "0.625rem",
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: "3px",
                                            color: "var(--emerald)",
                                            borderColor: "rgba(16, 185, 129, 0.3)",
                                            textDecoration: "none",
                                          }}
                                          title={`Call ${person.full_name} (+91 ${format10DigitPhone(person.phone)})`}
                                        >
                                          <Phone style={{ width: "10px", height: "10px" }} />
                                          {format10DigitPhone(person.phone)}
                                        </a>
                                      )}

                                      {person.email && (
                                        <button
                                          onClick={() => handleCopyEmail(person.email!, person.id)}
                                          className="btn-secondary"
                                          style={{
                                            padding: "3px 6px",
                                            fontSize: "0.625rem",
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: "3px",
                                            color: "var(--primary)",
                                            borderColor: "rgba(99, 102, 241, 0.3)",
                                          }}
                                          title={`Copy Email ${person.email} to clipboard`}
                                        >
                                          <Mail style={{ width: "10px", height: "10px" }} />
                                          {copiedEmailId === person.id ? "Copied!" : "Email"}
                                        </button>
                                      )}

                                      {person.linkedin_url && (
                                        <a
                                          href={
                                            person.linkedin_url.startsWith("http")
                                              ? person.linkedin_url
                                              : `https://${person.linkedin_url}`
                                          }
                                          target="_blank"
                                          rel="noopener noreferrer"
                                          className="btn-secondary"
                                          style={{
                                            padding: "3px 6px",
                                            fontSize: "0.625rem",
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: "3px",
                                            color: "var(--cyan)",
                                            borderColor: "rgba(6, 182, 212, 0.3)",
                                            textDecoration: "none",
                                          }}
                                          title="Open LinkedIn Profile"
                                        >
                                          LinkedIn
                                          <ExternalLink style={{ width: "9px", height: "9px" }} />
                                        </a>
                                      )}
                                    </div>

                                      <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                                        <span
                                          style={{
                                            fontSize: "0.5625rem",
                                            fontWeight: 700,
                                            padding: "1px 5px",
                                            borderRadius: "4px",
                                            background: "rgba(16, 185, 129, 0.1)",
                                            color: "var(--emerald)",
                                          }}
                                        >
                                          Verified
                                        </span>
                                      {canManage && (
                                        <button
                                          type="button"
                                          onClick={(e) => {
                                            e.stopPropagation();
                                            setEditingPerson(person);
                                          }}
                                          className="btn-secondary"
                                          style={{
                                            padding: "2px 6px",
                                            fontSize: "0.625rem",
                                            display: "inline-flex",
                                            alignItems: "center",
                                            gap: "2px",
                                            borderRadius: "4px",
                                            cursor: "pointer",
                                          }}
                                          title="Edit Decision-Maker"
                                        >
                                          ✏️ Edit
                                        </button>
                                      )}
                                    </div>
                                  </div>
                                </div>
                              );
                            })}
                          </div>
                        ) : (
                          /* No people linked to this company */
                          <div
                            style={{
                              padding: "12px",
                              borderRadius: "6px",
                              background: "var(--bg-surface)",
                              border: "1px dashed var(--border-color)",
                              textAlign: "center",
                              fontSize: "0.6875rem",
                              color: "var(--text-muted)",
                            }}
                          >
                            No executive personnel currently mapped to <strong>{company.legal_name}</strong>.
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* ========================================================================= */}
          {/* COLUMN 2: INDEPENDENT PEOPLE LEADS (NOT ASSOCIATED WITH REGISTERED ENTITY) */}
          {/* ========================================================================= */}
          {(activeColumnView === "DUAL" || activeColumnView === "PEOPLE") && (
            <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              {/* Column Header */}
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "10px 14px",
                  borderRadius: "8px",
                  background: "var(--bg-surface)",
                  border: "1px solid var(--border-color)",
                }}
              >
                <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                  <UserCheck style={{ width: "16px", height: "16px", color: "var(--emerald)" }} />
                  <div>
                    <span style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>
                      Independent People Leads
                    </span>
                    <span
                      style={{
                        fontSize: "0.6875rem",
                        fontWeight: 700,
                        padding: "1px 7px",
                        borderRadius: "10px",
                        background: "rgba(16, 185, 129, 0.1)",
                        color: "var(--emerald)",
                        marginLeft: "8px",
                      }}
                    >
                      {unlinkedPeople.length}
                    </span>
                  </div>
                </div>

                <label style={{ display: "flex", alignItems: "center", gap: "6px", cursor: "pointer", fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>
                  <input
                    type="checkbox"
                    checked={unlinkedPeople.length > 0 && selectedPeopleIds.length === unlinkedPeople.length}
                    onChange={handleSelectAllPeople}
                    style={{ cursor: "pointer" }}
                  />
                  <span>Select All</span>
                </label>
              </div>

              {/* People Empty State */}
              {unlinkedPeople.length === 0 && (
                <div className="card" style={{ padding: "32px 20px", textAlign: "center", color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                  All people leads are currently mapped to registered enterprises.
                </div>
              )}

              {/* Independent People Cards */}
              <div
                style={{
                  display: "grid",
                  gridTemplateColumns: activeColumnView === "PEOPLE" ? "repeat(auto-fill, minmax(320px, 1fr))" : "1fr",
                  gap: "12px",
                }}
              >
                {unlinkedPeople.map((person) => {
                  const isSelected = selectedPeopleIds.includes(person.id);
                  const initials = person.full_name
                    .split(" ")
                    .filter(Boolean)
                    .map((p) => p[0])
                    .slice(0, 2)
                    .join("")
                    .toUpperCase();

                  return (
                    <div
                      key={person.id}
                      className="card"
                      style={{
                        padding: "14px 16px",
                        border: isSelected ? "1.5px solid var(--emerald)" : "1px solid var(--border-color)",
                        boxShadow: isSelected ? "0 4px 12px rgba(16, 185, 129, 0.1)" : "none",
                        display: "flex",
                        flexDirection: "column",
                        gap: "8px",
                        transition: "all 0.2s ease",
                      }}
                    >
                      {/* Top Header: Checkbox, Avatar, Name, Seniority */}
                      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: "8px" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                          <input
                            type="checkbox"
                            checked={isSelected}
                            onChange={() => handleSelectPerson(person.id)}
                            style={{ cursor: "pointer" }}
                          />

                          <div
                            style={{
                              width: "32px",
                              height: "32px",
                              borderRadius: "50%",
                              background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                              color: "#ffffff",
                              fontWeight: 700,
                              fontSize: "0.75rem",
                              display: "flex",
                              alignItems: "center",
                              justifyContent: "center",
                              flexShrink: 0,
                            }}
                          >
                            {initials || "P"}
                          </div>

                          <div>
                            <div style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                              {person.full_name}
                            </div>
                            <div style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--emerald)" }}>
                              {person.designation || "Executive"}
                            </div>
                          </div>
                        </div>

                        {person.seniority && (
                          <span
                            style={{
                              fontSize: "0.625rem",
                              fontWeight: 700,
                              padding: "2px 6px",
                              borderRadius: "4px",
                              background: "rgba(16, 185, 129, 0.1)",
                              color: "var(--emerald)",
                              border: "1px solid rgba(16, 185, 129, 0.25)",
                            }}
                          >
                            {person.seniority}
                          </span>
                        )}
                      </div>

                      {/* Stated Unregistered Company Tag */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "6px",
                          fontSize: "0.75rem",
                          background: "var(--bg-canvas)",
                          padding: "6px 10px",
                          borderRadius: "6px",
                          border: "1px solid var(--border-color)",
                        }}
                      >
                        <Building2 style={{ width: "13px", height: "13px", color: "var(--text-muted)" }} />
                        <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>
                          {person.company_name || "Unspecified Enterprise"}
                        </span>
                        <span
                          style={{
                            fontSize: "0.5625rem",
                            fontWeight: 700,
                            padding: "1px 5px",
                            borderRadius: "4px",
                            background: "rgba(245, 158, 11, 0.1)",
                            color: "var(--amber)",
                            marginLeft: "auto",
                          }}
                        >
                          Unregistered Account
                        </span>
                      </div>

                      {/* Department and Location */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          gap: "12px",
                          fontSize: "0.6875rem",
                          color: "var(--text-secondary)",
                        }}
                      >
                        {person.department && (
                          <span style={{ display: "flex", alignItems: "center", gap: "3px" }}>
                            <Briefcase style={{ width: "11px", height: "11px", color: "var(--text-muted)" }} />
                            {person.department}
                          </span>
                        )}
                        {(person.city || person.state) && (
                          <span style={{ display: "flex", alignItems: "center", gap: "3px" }}>
                            <MapPin style={{ width: "11px", height: "11px", color: "var(--text-muted)" }} />
                            {[person.city, person.state].filter(Boolean).join(", ")}
                          </span>
                        )}
                      </div>

                      {/* Outreach Channels & Pull Trigger */}
                      <div
                        style={{
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "space-between",
                          borderTop: "1px solid var(--border-color)",
                          paddingTop: "8px",
                          marginTop: "2px",
                        }}
                      >
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          {person.phone && (
                            <a
                              href={getCallUrl(person.phone)}
                              className="btn-secondary"
                              style={{
                                padding: "3px 8px",
                                fontSize: "0.6875rem",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "3px",
                                color: "var(--emerald)",
                                borderColor: "rgba(16, 185, 129, 0.3)",
                                textDecoration: "none",
                              }}
                              title={`Call ${person.full_name} (+91 ${format10DigitPhone(person.phone)})`}
                            >
                              <Phone style={{ width: "10px", height: "10px" }} />
                              {format10DigitPhone(person.phone)}
                            </a>
                          )}

                          {person.email && (
                            <button
                              onClick={() => handleCopyEmail(person.email!, person.id)}
                              className="btn-secondary"
                              style={{
                                padding: "3px 8px",
                                fontSize: "0.6875rem",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "3px",
                                color: "var(--primary)",
                                borderColor: "rgba(99, 102, 241, 0.3)",
                              }}
                              title={`Copy Email ${person.email} to clipboard`}
                            >
                              <Mail style={{ width: "10px", height: "10px" }} />
                              {copiedEmailId === person.id ? "Copied!" : "Email"}
                            </button>
                          )}

                          {person.linkedin_url && (
                            <a
                              href={
                                person.linkedin_url.startsWith("http")
                                  ? person.linkedin_url
                                  : `https://${person.linkedin_url}`
                              }
                              target="_blank"
                              rel="noopener noreferrer"
                              className="btn-secondary"
                              style={{
                                padding: "3px 8px",
                                fontSize: "0.6875rem",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "3px",
                                color: "var(--cyan)",
                                borderColor: "rgba(6, 182, 212, 0.3)",
                                textDecoration: "none",
                              }}
                              title="LinkedIn Profile"
                            >
                              LinkedIn
                              <ExternalLink style={{ width: "9px", height: "9px" }} />
                            </a>
                          )}
                        </div>

                        {!canManage ? (
                          <button
                            onClick={() => {
                              setSelectedPeopleIds([person.id]);
                              handleOpenPullModal("PEOPLE");
                            }}
                            className="btn-primary"
                            style={{
                              padding: "3px 9px",
                              fontSize: "0.6875rem",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "3px",
                              background: "linear-gradient(135deg, #059669, #047857)",
                              borderColor: "#065f46",
                            }}
                            title="Conserve individual lead into your CRM"
                          >
                            <Download style={{ width: "10px", height: "10px" }} />
                            Conserve
                          </button>
                        ) : (
                          <div style={{ display: "inline-flex", alignItems: "center", gap: "5px" }}>
                            <span
                              style={{
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "4px",
                                padding: "2px 6px",
                                borderRadius: "999px",
                                fontSize: "0.625rem",
                                fontWeight: 700,
                                background: "rgba(16, 185, 129, 0.12)",
                                color: "var(--emerald)",
                                border: "1px solid rgba(16, 185, 129, 0.3)",
                              }}
                            >
                              <span>AVAILABLE</span>
                            </span>
                            <button
                              type="button"
                              onClick={() => setEditingPerson(person)}
                              className="btn btn-secondary"
                              style={{
                                padding: "2px 6px",
                                fontSize: "0.625rem",
                                display: "inline-flex",
                                alignItems: "center",
                                gap: "2px",
                                borderRadius: "4px",
                                cursor: "pointer",
                              }}
                              title="Edit Lead"
                            >
                              ✏️ Edit
                            </button>
                          </div>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Pull to CRM Modal */}
      {showPullModal && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.6)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px",
          }}
        >
          <div
            className="card"
            style={{
              width: "100%",
              maxWidth: "460px",
              padding: "24px",
              display: "flex",
              flexDirection: "column",
              gap: "18px",
              boxShadow: "0 20px 40px rgba(0, 0, 0, 0.3)",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <Download style={{ width: "18px", height: "18px", color: "var(--primary)" }} />
                <h3 style={{ fontSize: "1.125rem", fontWeight: 700, color: "var(--text-primary)", margin: 0 }}>
                  Pull Records to CRM Pipeline
                </h3>
              </div>
              <button
                onClick={() => setShowPullModal(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
              >
                <X style={{ width: "18px", height: "18px" }} />
              </button>
            </div>

            <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", margin: 0 }}>
              {pullTargetType === "COMPANIES" ? (
                <>
                  You are about to pull <strong>{selectedCompanyIds.length}</strong> enterprise(s) and their associated contacts into a target organization's CRM pipeline.
                </>
              ) : (
                <>
                  You are about to pull <strong>{selectedPeopleIds.length}</strong> independent people lead(s) into a target organization's CRM pipeline.
                </>
              )}
            </p>

            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <label style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-primary)" }}>
                Conserving to Workspace
              </label>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "8px",
                  padding: "8px 12px",
                  borderRadius: "8px",
                  background: "var(--bg-surface-subtle)",
                  border: "1px solid var(--border-color)",
                  fontSize: "0.8125rem",
                  fontWeight: 600,
                  color: "var(--text-primary)"
                }}
              >
                <ShieldCheck style={{ width: "16px", height: "16px", color: "var(--primary)" }} />
                <span>{orgName} (Your CRM Workspace)</span>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "8px" }}>
              <button
                onClick={() => setShowPullModal(false)}
                className="btn-secondary"
                style={{ fontSize: "0.8125rem" }}
              >
                Cancel
              </button>
              <button
                onClick={handlePullConfirm}
                disabled={pulling}
                className="btn-primary"
                style={{ fontSize: "0.8125rem" }}
              >
                {pulling ? "Pulling..." : `Confirm & Pull ${pullTargetType === "COMPANIES" ? selectedCompanyIds.length : selectedPeopleIds.length} Records`}
              </button>
            </div>
          </div>
        </div>
      )}

      {editingCompany && (
        <EditCompanyModal
          company={editingCompany}
          isOpen={Boolean(editingCompany)}
          onClose={() => setEditingCompany(null)}
          currentUser={currentUser}
          onSaved={(updated, pendingApproval) => {
            if (pendingApproval) {
              setSuccessMsg(`Edits to "${updated.legal_name}" submitted for admin approval.`);
            } else {
              setSuccessMsg(`Enterprise "${updated.legal_name}" updated successfully!`);
            }
            setTimeout(() => setSuccessMsg(null), 4000);
            loadIntelligence();
          }}
        />
      )}

      {editingPerson && (
        <EditPersonModal
          person={editingPerson}
          isOpen={Boolean(editingPerson)}
          onClose={() => setEditingPerson(null)}
          currentUser={currentUser}
          onSaved={(updated, pendingApproval) => {
            if (pendingApproval) {
              setSuccessMsg(`Edits to "${updated.full_name}" submitted for admin approval.`);
            } else {
              setSuccessMsg(`Executive profile for "${updated.full_name}" updated successfully!`);
            }
            setTimeout(() => setSuccessMsg(null), 4000);
            loadIntelligence();
          }}
        />
      )}
    </div>
  );
};
