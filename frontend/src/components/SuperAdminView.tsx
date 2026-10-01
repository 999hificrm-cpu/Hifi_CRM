import React, { useState, useEffect } from "react";
import { api } from "../services/api";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, LineChart, Line, AreaChart, Area, PieChart, Pie, Cell } from 'recharts';
import { 
  Building2, 
  Calendar,
  Plus, 
  ShieldCheck, 
  Check, 
  ActivitySquare, 
  X, 
  Search, 
  Filter, 
  PhoneCall, 
  Mail, 
  MessageCircle, 
  Eye, 
  Layers, 
  Globe, 
  UserCheck,
  LifeBuoy,
  PauseCircle,
  Trash2,
  Key
} from "lucide-react";
import { SupportModeBanner } from "./super_admin/SupportModeBanner";
import { SupportSessionModal } from "./super_admin/SupportSessionModal";
import { SuspendOrgModal } from "./super_admin/SuspendOrgModal";
import { PlatformSecurityView } from "./super_admin/PlatformSecurityView";
import { RecycleBinView } from "./super_admin/RecycleBinView";
import { AuditChainView } from "./super_admin/AuditChainView";

interface SuperAdminViewProps {
  viewMode?: "dashboard" | "organizations" | "users" | "security" | "audit" | "recovery";
}

export const SuperAdminView: React.FC<SuperAdminViewProps> = ({ viewMode = "dashboard" }) => {
  const [organizations, setOrganizations] = useState<any[]>([]);
  const [auditLogs, setAuditLogs] = useState<any[]>([]);
  const [kpis, setKpis] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [showCreateUserModal, setShowCreateUserModal] = useState(false);
  const [loading, setLoading] = useState(true);

  // Search & Filter state
  const [orgSearch, setOrgSearch] = useState("");
  const [auditSearch, setAuditSearch] = useState("");
  const [auditActionFilter, setAuditActionFilter] = useState("ALL");
  const [auditTenantFilter, setAuditTenantFilter] = useState("ALL");

  // Phase 1 Security, Support & Governance State
  const [activeSupportSession, setActiveSupportSession] = useState<any | null>(() => {
    try {
      const saved = localStorage.getItem("jarvis_support_session");
      return saved ? JSON.parse(saved) : null;
    } catch {
      return null;
    }
  });
  const [supportOrgModal, setSupportOrgModal] = useState<any | null>(null);
  const [suspendOrgModal, setSuspendOrgModal] = useState<any | null>(null);

  // Provisioning & User State
  const [name, setName] = useState("");
  const [planCode, setPlanCode] = useState("GROWTH");
  const [creating, setCreating] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const [newUserFullName, setNewUserFullName] = useState("");
  const [newUserEmail, setNewUserEmail] = useState("");
  const [newUserPassword, setNewUserPassword] = useState("");
  const [newUserRole, setNewUserRole] = useState("");
  
  const [editingUserId, setEditingUserId] = useState<string | null>(null);
  const [editingOrgId, setEditingOrgId] = useState<string | null>(null);

  // Detailed Business Fields for ORG Admin
  const [orgIndustry, setOrgIndustry] = useState("");
  const [orgCin, setOrgCin] = useState("");
  const [orgRegistration, setOrgRegistration] = useState("");
  const [orgGst, setOrgGst] = useState("");
  const [orgAddress, setOrgAddress] = useState("");
  const [orgCity, setOrgCity] = useState("");
  const [orgPincode, setOrgPincode] = useState("");
  const [orgState, setOrgState] = useState("");
  const [orgContactNumber, setOrgContactNumber] = useState("");
  const [orgContactEmail, setOrgContactEmail] = useState("");
  const [orgWebsite, setOrgWebsite] = useState("");
  const [orgType, setOrgType] = useState("Private Limited");
  const [orgOwner, setOrgOwner] = useState("");
  const [adminPhone, setAdminPhone] = useState("");

  const resetUserForm = () => {
    setNewUserFullName("");
    setNewUserEmail("");
    setNewUserPassword("");
    setNewUserRole("");
    setName("");
    setEditingUserId(null);
    setEditingOrgId(null);
    setOrgIndustry("");
    setOrgCin("");
    setOrgRegistration("");
    setOrgGst("");
    setOrgAddress("");
    setOrgCity("");
    setOrgPincode("");
    setOrgState("");
    setOrgContactNumber("");
    setOrgContactEmail("");
    setOrgWebsite("");
    setOrgType("Private Limited");
    setOrgOwner("");
    setAdminPhone("");
  };

  const handleEditUser = (user: any) => {
    resetUserForm();
    setEditingUserId(user.id);
    setNewUserFullName(user.full_name);
    setNewUserEmail(user.email);
    setNewUserRole(user.platform_role || user.tenant_role || "DATA_ENTRY");
    
    if (user.tenant_role === "ORG_ADMIN" && user.organization_id) {
        setEditingOrgId(user.organization_id);
        const org = organizations.find(o => o.id === user.organization_id);
        if (org) {
            setName(org.name);
            const settings = org.settings || {};
            setOrgIndustry(settings.industry || "");
            setOrgCin(settings.cin || "");
            setOrgRegistration(settings.registration_number || "");
            setOrgGst(settings.gst_number || "");
            setOrgAddress(settings.address || "");
            setOrgCity(settings.city || "");
            setOrgPincode(settings.pincode || "");
            setOrgState(settings.state || "");
            setOrgContactNumber(settings.contact_number || "");
            setOrgContactEmail(settings.contact_email || "");
            setOrgWebsite(settings.website || "");
            setOrgType(settings.company_type || "Private Limited");
            setOrgOwner(settings.owner_name || "");
            setAdminPhone(user.phone || "");
        }
    }
    setShowCreateUserModal(true);
  };

  useEffect(() => {
    loadPlatformData();
  }, [viewMode]);

  const handleGrantTrial = async (org: any) => {
    const daysStr = window.prompt(`How many days of trial do you want to grant to ${org.name}?`, "3");
    if (!daysStr) return;
    
    const days = parseInt(daysStr, 10);
    if (isNaN(days) || days <= 0) {
      alert("Please enter a valid number of days.");
      return;
    }
    
    try {
      await api.grantTrial(org.id, days);
      setMsg(`Successfully granted a ${days}-day trial to ${org.name}`);
      const orgs = await api.getOrganizations();
      setOrganizations(orgs);
      setTimeout(() => setMsg(""), 3000);
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Failed to grant trial.");
    }
  };
  const handleGrantFullAccess = async (org: any) => {
    const confirmation = window.confirm(`Are you sure you want to grant 10-year enterprise access to ${org.name}?`);
    if (!confirmation) return;
    
    try {
      await api.grantFullAccess(org.id);
      setMsg(`Successfully granted full access to ${org.name}`);
      const orgs = await api.getOrganizations();
      setOrganizations(orgs);
      setTimeout(() => setMsg(""), 3000);
    } catch (e: any) {
      console.error(e);
      alert(e.message || "Failed to grant full access.");
    }
  };

  const handleToggleSuspend = async (org: any) => {
    if (org.status !== "SUSPENDED") {
      const confirmation = window.prompt(`To suspend ${org.name}, please type SUSPEND in caps:`);
      if (confirmation === "SUSPEND") {
        try {
          const reason = "Suspended by Super Admin via toggle";
          const idempotencyKey = `suspend-org-${org.id}-${Date.now()}`;
          await api.suspendOrganization(org.id, reason, idempotencyKey);
          setMsg(`Successfully suspended ${org.name}`);
          setTimeout(() => setMsg(""), 3000);
          loadPlatformData();
        } catch (err: any) {
          alert(err.message || "Failed to suspend organization.");
        }
      } else {
        alert("Confirmation failed. Suspension cancelled.");
      }
    } else {
      alert("Organization is already suspended.");
      // Reactivation can be done via another endpoint if needed, but not requested here.
    }
  };
  const loadPlatformData = async () => {
    setLoading(true);
    try {
      if (viewMode === "dashboard") {
        const [adminKpis, orgs, logs] = await Promise.all([
          api.getAdminKPIs(),
          api.getOrganizations(),
          api.getAuditLogs(),
        ]);
        setKpis(adminKpis);
        setOrganizations(orgs);
        setAuditLogs(logs);
      } else if (viewMode === "organizations") {
        const orgs = await api.getOrganizations();
        setOrganizations(orgs);
      } else if (viewMode === "users" || viewMode === "security") {
        const [adminUsers, orgs] = await Promise.all([
          api.getAdminUsers(),
          api.getOrganizations(),
        ]);
        setUsers(adminUsers);
        setOrganizations(orgs);
      } else if (viewMode === "audit") {
        const orgs = await api.getOrganizations();
        setOrganizations(orgs);
      }
    } catch (e) {
      console.error("Failed loading platform data:", e);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    try {
      if (editingUserId) {
        // Update existing user
        await api.updateAdminUser(editingUserId, {
           full_name: newUserFullName,
           email: newUserEmail,
           password: newUserPassword ? newUserPassword : undefined,
           phone: adminPhone
        });
        if (editingOrgId && newUserRole === "ORG_ADMIN") {
           await api.updateOrganization(editingOrgId, {
               name: name,
               settings: {
                   owner_name: orgOwner,
                   industry: orgIndustry,
                   cin: orgCin,
                   registration_number: orgRegistration,
                   gst_number: orgGst,
                   address: orgAddress,
                   city: orgCity,
                   pincode: orgPincode,
                   state: orgState,
                   contact_number: orgContactNumber,
                   contact_email: orgContactEmail,
                   website: orgWebsite,
                   company_type: orgType,
               }
           });
        }
        setMsg(`User "${newUserFullName}" successfully updated!`);
      } else {
        // Create new user
        if (newUserRole === "ORG_ADMIN") {
          await api.createOrganization({
            name: name,
            admin_name: newUserFullName,
            admin_email: newUserEmail,
            admin_password: newUserPassword || "Password@2026",
            admin_phone: adminPhone,
            plan_code: planCode,
            owner_name: orgOwner,
            industry: orgIndustry,
            cin: orgCin,
            registration_number: orgRegistration,
            gst_number: orgGst,
            address: orgAddress,
            city: orgCity,
            pincode: orgPincode,
            state: orgState,
            contact_number: orgContactNumber,
            contact_email: orgContactEmail,
            website: orgWebsite,
            company_type: orgType,
          });
          setMsg(`Organization "${name}" and Admin "${newUserFullName}" successfully created!`);
        } else {
          await api.createAdminUser({
            full_name: newUserFullName,
            email: newUserEmail,
            password: newUserPassword || "Password@2026",
            platform_role: "DATA_ENTRY",
            tenant_role: null,
            organization_id: null,
          });
          setMsg(`Data Entry Operator "${newUserFullName}" successfully created!`);
        }
      }
      setShowCreateUserModal(false);
      resetUserForm();
      loadPlatformData();
      setTimeout(() => setMsg(null), 4000);
    } catch (err: any) {
      alert(err.message || "Failed to create user/organization");
    } finally {
      setCreating(false);
    }
  };

  const handleToggleUserStatus = async (user: any) => {
    try {
      const newStatus = user.status === "ACTIVE" ? "SUSPENDED" : "ACTIVE";
      if (newStatus === "SUSPENDED") {
        const confirmName = window.prompt(`⚠️ SECURITY GUARDRAIL\n\nAre you sure you want to suspend this user? They will lose all access to the platform immediately.\n\nType "${user.full_name}" to confirm:`);
        if (confirmName !== user.full_name) {
          alert("Confirmation failed. Suspension cancelled.");
          return;
        }
      }
      await api.updateUserStatus(user.id, newStatus);
      loadPlatformData();
    } catch (err: any) {
      alert(err.message || "Failed to update user status");
    }
  };

  // Filtered organizations
  const filteredOrgs = organizations.filter((org) => {
    if (!orgSearch) return true;
    const s = orgSearch.toLowerCase();
    return (
      org.name.toLowerCase().includes(s) ||
      (org.domain && org.domain.toLowerCase().includes(s)) ||
      org.id.toLowerCase().includes(s)
    );
  });

  // Filtered audit events
  const filteredLogs = auditLogs.filter((log) => {
    const matchesAction = auditActionFilter === "ALL" || log.action === auditActionFilter;
    const matchesTenant = auditTenantFilter === "ALL" || log.organization_id === auditTenantFilter;
    const matchesSearch = !auditSearch || (
      log.action.toLowerCase().includes(auditSearch.toLowerCase()) ||
      (log.entity_type && log.entity_type.toLowerCase().includes(auditSearch.toLowerCase())) ||
      (log.actor_user_id && log.actor_user_id.toLowerCase().includes(auditSearch.toLowerCase())) ||
      (log.ip_address && log.ip_address.includes(auditSearch))
    );
    return matchesAction && matchesTenant && matchesSearch;
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
    if (action.includes("VIEW")) {
      return (
        <span className="badge" style={{ background: "#f1f5f9", color: "#334155", border: "1px solid #cbd5e1", display: "inline-flex", alignItems: "center", gap: "4px" }}>
          <Eye style={{ width: "11px", height: "11px" }} />
          {action}
        </span>
      );
    }
    return (
      <span className="badge badge-medium">
        {action}
      </span>
    );
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      {/* Phase 1 Support Session Active Banner */}
      <SupportModeBanner
        session={activeSupportSession}
        orgName={activeSupportSession?.org_name}
        onSessionEnded={() => setActiveSupportSession(null)}
      />

      {/* ========================================================================= */}
      {/* MODULE 1: DASHBOARD VIEW                                                  */}
      {/* ========================================================================= */}
      {viewMode === "dashboard" && kpis && (
        <>
          {/* Header & Date Filters */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px", marginBottom: "8px" }}>
            <div>
              <h2 style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
                Welcome back, Super Admin 👋
              </h2>
              <p style={{ fontSize: "0.875rem", color: "var(--text-secondary)", marginTop: "4px" }}>
                Here's what's happening across your JARVIS platform today.
              </p>
            </div>
            
            <div style={{ display: "flex", alignItems: "center", gap: "10px", background: "var(--bg-surface)", padding: "10px 18px", borderRadius: "12px", border: "1px solid var(--border-subtle)", boxShadow: "var(--shadow-sm)" }}>
              <Calendar style={{ width: "18px", height: "18px", color: "var(--primary)" }} />
              <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>
                {(() => {
                  const date = new Date();
                  const day = date.getDate();
                  const month = date.toLocaleString('default', { month: 'long' });
                  const year = date.getFullYear();
                  let suffix = 'th';
                  if (day % 10 === 1 && day !== 11) suffix = 'st';
                  else if (day % 10 === 2 && day !== 12) suffix = 'nd';
                  else if (day % 10 === 3 && day !== 13) suffix = 'rd';
                  return `${day}${suffix} ${month}, ${year}`;
                })()}
              </span>
            </div>
          </div>

          {/* 4 Top KPI Cards */}
          <div className="dashboard-grid-top" style={{ marginBottom: "8px" }}>
            <div className="card" style={{ padding: "16px", display: "flex", alignItems: "flex-start", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "var(--primary-light)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Building2 style={{ width: "24px", height: "24px", color: "var(--primary)" }} />
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Total Tenants</span>
                <p style={{ fontSize: "1.875rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "2px", lineHeight: 1 }}>
                  {kpis.total_organizations}
                </p>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--emerald)", marginTop: "6px" }}>↑ 12% <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>+2 new this week</span></p>
              </div>
            </div>

            <div className="card" style={{ padding: "16px", display: "flex", alignItems: "flex-start", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "#f3e8ff", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Globe style={{ width: "24px", height: "24px", color: "#9333ea" }} />
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Total Companies</span>
                <p style={{ fontSize: "1.875rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "2px", lineHeight: 1 }}>
                  {kpis.total_global_companies.toLocaleString()}
                </p>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--emerald)", marginTop: "6px" }}>↑ 8% <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>+45 this month</span></p>
              </div>
            </div>

            <div className="card" style={{ padding: "16px", display: "flex", alignItems: "flex-start", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "var(--emerald-light)", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <UserCheck style={{ width: "24px", height: "24px", color: "var(--emerald-dark)" }} />
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Total Users</span>
                <p style={{ fontSize: "1.875rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "2px", lineHeight: 1 }}>
                  {users.length.toLocaleString()}
                </p>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--emerald)", marginTop: "6px" }}>↑ 18% <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>+436 this month</span></p>
              </div>
            </div>
            
            <div className="card" style={{ padding: "16px", display: "flex", alignItems: "flex-start", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "#e0e7ff", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <Layers style={{ width: "24px", height: "24px", color: "#4f46e5" }} />
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Total API Pulls</span>
                <p style={{ fontSize: "1.875rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "2px", lineHeight: 1 }}>
                  {kpis.total_data_pulls.toLocaleString()}
                </p>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--emerald)", marginTop: "6px" }}>↑ 24% <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>+24.3k this week</span></p>
              </div>
            </div>

            <div className="card" style={{ padding: "16px", display: "flex", alignItems: "flex-start", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "#fef3c7", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <PhoneCall style={{ width: "24px", height: "24px", color: "#d97706" }} />
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Telecaller Calls (Today)</span>
                <p style={{ fontSize: "1.875rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "2px", lineHeight: 1 }}>
                  {kpis.total_calls_today?.toLocaleString() || 0}
                </p>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--amber)", marginTop: "6px" }}>
                  <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>{kpis.active_telecaller_sessions || 0} active sessions</span>
                </p>
              </div>
            </div>
            
            <div className="card" style={{ padding: "16px", display: "flex", alignItems: "flex-start", gap: "16px" }}>
              <div style={{ width: "48px", height: "48px", borderRadius: "12px", background: "#dbeafe", display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                <ActivitySquare style={{ width: "24px", height: "24px", color: "#2563eb" }} />
              </div>
              <div style={{ flex: 1 }}>
                <span style={{ fontSize: "0.8125rem", fontWeight: 600, color: "var(--text-secondary)" }}>Total Talk Time</span>
                <p style={{ fontSize: "1.875rem", fontWeight: 900, color: "var(--text-primary)", marginTop: "2px", lineHeight: 1 }}>
                  {kpis.total_talk_time_minutes || 0} <span style={{ fontSize: "1rem" }}>mins</span>
                </p>
                <p style={{ fontSize: "0.75rem", fontWeight: 600, color: "#2563eb", marginTop: "6px" }}>
                  <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>Across platform today</span>
                </p>
              </div>
            </div>
          </div>
          
          {/* Middle Section */}
          <div className="dashboard-grid-middle" style={{ marginBottom: "8px" }}>
            
            {/* Platform Growth Area Chart */}
            <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "16px" }}>
                <div>
                  <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>Platform Growth</h3>
                  <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "4px" }}>Tenants, Users and API usage over time</p>
                </div>
                <select className="select-dropdown" style={{ padding: "6px 12px", width: "auto" }}>
                  <option>Last 30 days</option>
                  <option>Last 6 months</option>
                  <option>This Year</option>
                </select>
              </div>
              
              <div style={{ height: "280px", width: "100%", position: "relative" }}>
                <ResponsiveContainer width="99%" height={280}>
                  <AreaChart data={[
                    { name: 'Aug 15', users: Math.max(0, (users?.length || 0) - 15), companies: Math.max(0, (kpis?.total_global_companies || 0) - 200), tenants: Math.max(0, (kpis?.total_organizations || 0) - 6) },
                    { name: 'Aug 20', users: Math.max(0, (users?.length || 0) - 12), companies: Math.max(0, (kpis?.total_global_companies || 0) - 150), tenants: Math.max(0, (kpis?.total_organizations || 0) - 5) },
                    { name: 'Aug 25', users: Math.max(0, (users?.length || 0) - 8), companies: Math.max(0, (kpis?.total_global_companies || 0) - 100), tenants: Math.max(0, (kpis?.total_organizations || 0) - 4) },
                    { name: 'Aug 30', users: Math.max(0, (users?.length || 0) - 5), companies: Math.max(0, (kpis?.total_global_companies || 0) - 80), tenants: Math.max(0, (kpis?.total_organizations || 0) - 3) },
                    { name: 'Sep 04', users: Math.max(0, (users?.length || 0) - 3), companies: Math.max(0, (kpis?.total_global_companies || 0) - 40), tenants: Math.max(0, (kpis?.total_organizations || 0) - 2) },
                    { name: 'Sep 09', users: Math.max(0, (users?.length || 0) - 1), companies: Math.max(0, (kpis?.total_global_companies || 0) - 10), tenants: Math.max(0, (kpis?.total_organizations || 0) - 1) },
                    { name: 'Sep 13', users: users?.length || 0, companies: kpis?.total_global_companies || 0, tenants: kpis?.total_organizations || 0 },
                  ]}>
                    <defs>
                      <linearGradient id="colorUsers" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#8b5cf6" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#8b5cf6" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorCompanies" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0}/>
                      </linearGradient>
                      <linearGradient id="colorTenants" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.4}/>
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e2e8f0" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: '#64748b' }} dx={-10} tickFormatter={(val) => val >= 1000 ? `${(val/1000).toFixed(0)}K` : val} />
                    <Tooltip contentStyle={{ borderRadius: '8px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgba(15, 23, 42, 0.07)' }} />
                    <Area type="monotone" dataKey="users" name="Users" stroke="#8b5cf6" strokeWidth={3} fillOpacity={1} fill="url(#colorUsers)" />
                    <Area type="monotone" dataKey="companies" name="Companies" stroke="#3b82f6" strokeWidth={3} fillOpacity={1} fill="url(#colorCompanies)" />
                    <Area type="monotone" dataKey="tenants" name="Tenants" stroke="#10b981" strokeWidth={3} fillOpacity={1} fill="url(#colorTenants)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
              <div style={{ display: "flex", justifyContent: "center", gap: "24px", marginTop: "12px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}><div style={{ width: "12px", height: "6px", borderRadius: "3px", background: "#8b5cf6" }}></div><span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Users</span></div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}><div style={{ width: "12px", height: "6px", borderRadius: "3px", background: "#3b82f6" }}></div><span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Companies</span></div>
                <div style={{ display: "flex", alignItems: "center", gap: "6px" }}><div style={{ width: "12px", height: "6px", borderRadius: "3px", background: "#10b981" }}></div><span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>Tenants</span></div>
              </div>
            </div>

            <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
              
              {/* Top Active Companies */}
              <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", flex: 1 }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                  <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>Top Active Companies</h3>
                  <span style={{ fontSize: "0.75rem", color: "var(--primary)", fontWeight: 600, cursor: "pointer" }}>View All</span>
                </div>
                
                <table style={{ width: "100%", borderCollapse: "collapse", fontSize: "0.8125rem" }}>
                  <thead>
                    <tr style={{ color: "var(--text-muted)", borderBottom: "1px solid var(--border-subtle)" }}>
                      <th style={{ textAlign: "left", paddingBottom: "8px", fontWeight: 600 }}>#</th>
                      <th style={{ textAlign: "left", paddingBottom: "8px", fontWeight: 600 }}>Company</th>
                      <th style={{ textAlign: "right", paddingBottom: "8px", fontWeight: 600 }}>Users</th>
                      <th style={{ textAlign: "right", paddingBottom: "8px", fontWeight: 600 }}>API Pulls</th>
                      <th style={{ textAlign: "right", paddingBottom: "8px", fontWeight: 600 }}>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {organizations.slice(0, 5).map((org, idx) => (
                      <tr key={org.id} style={{ borderBottom: "1px solid var(--border-subtle)" }}>
                        <td style={{ padding: "12px 0", color: "var(--text-secondary)" }}>{idx + 1}</td>
                        <td style={{ padding: "12px 0", display: "flex", alignItems: "center", gap: "8px" }}>
                          <div style={{ width: "24px", height: "24px", borderRadius: "6px", background: "var(--primary)", color: "white", display: "flex", alignItems: "center", justifyContent: "center", fontSize: "0.75rem", fontWeight: 700 }}>
                            {org.name.charAt(0)}
                          </div>
                          <span style={{ fontWeight: 600, color: "var(--text-primary)" }}>{org.name}</span>
                        </td>
                        <td style={{ padding: "12px 0", textAlign: "right", color: "var(--text-secondary)" }}>{Math.floor(Math.random() * 300) + 50}</td>
                        <td style={{ padding: "12px 0", textAlign: "right", color: "var(--text-secondary)" }}>{(Math.floor(Math.random() * 20) + 5).toLocaleString()},{(Math.floor(Math.random() * 900) + 100)}</td>
                        <td style={{ padding: "12px 0", textAlign: "right" }}>
                          <span style={{ background: "var(--emerald-light)", color: "var(--emerald-dark)", padding: "2px 8px", borderRadius: "10px", fontSize: "0.6875rem", fontWeight: 700 }}>Active</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              
              {/* Users by Role Pie Chart */}
              <div className="card" style={{ padding: "16px", display: "flex", flexDirection: "column", height: "300px" }}>
                <h3 style={{ fontSize: "1.125rem", fontWeight: 800, color: "var(--text-primary)" }}>Users by Role</h3>
                <div style={{ display: "flex", flex: 1, alignItems: "center" }}>
                  <div style={{ flex: 1, height: "100%" }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={[
                            { name: 'Company Admin', value: users.filter(u => u.tenant_role === 'ORG_ADMIN').length || 1, color: '#8b5cf6' },
                            { name: 'Managers', value: users.filter(u => u.tenant_role === 'SALES_MANAGER').length || 1, color: '#3b82f6' },
                            { name: 'Standard Users', value: users.filter(u => u.tenant_role === 'SALES_REP' || u.tenant_role === 'TELECALLER').length || 1, color: '#10b981' },
                            { name: 'Support Staff', value: users.filter(u => u.platform_role === 'DATA_ENTRY').length || 1, color: '#f59e0b' },
                          ]}
                          innerRadius={60}
                          outerRadius={80}
                          paddingAngle={5}
                          dataKey="value"
                        >
                          {
                            [
                              { name: 'Company Admin', color: '#8b5cf6' },
                              { name: 'Managers', color: '#3b82f6' },
                              { name: 'Standard Users', color: '#10b981' },
                              { name: 'Support Staff', color: '#f59e0b' }
                            ].map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={entry.color} />
                            ))
                          }
                        </Pie>
                        <Tooltip contentStyle={{ borderRadius: '8px', border: 'none', boxShadow: 'var(--shadow-sm)' }} />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: "12px", paddingLeft: "12px" }}>
                    {[
                      { name: 'Company Admin', value: users.filter(u => u.tenant_role === 'ORG_ADMIN').length, color: '#8b5cf6' },
                      { name: 'Managers', value: users.filter(u => u.tenant_role === 'SALES_MANAGER').length, color: '#3b82f6' },
                      { name: 'Standard Users', value: users.filter(u => u.tenant_role === 'SALES_REP' || u.tenant_role === 'TELECALLER').length, color: '#10b981' },
                      { name: 'Support Staff', value: users.filter(u => u.platform_role === 'DATA_ENTRY').length, color: '#f59e0b' },
                    ].map((role) => (
                      <div key={role.name} style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          <div style={{ width: "8px", height: "8px", borderRadius: "50%", background: role.color }}></div>
                          <span style={{ fontSize: "0.75rem", color: "var(--text-secondary)", fontWeight: 600 }}>{role.name}</span>
                        </div>
                        <span style={{ fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)" }}>{role.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>

            </div>
          </div>

          {/* Bottom Section */}
          <div className="dashboard-grid-bottom">
             
             {/* Platform Activity */}
             <div className="card" style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
                   <h3 style={{ fontSize: '1.125rem', fontWeight: 800, color: 'var(--text-primary)' }}>Platform Activity</h3>
                   <span style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 600, cursor: 'pointer' }} onClick={() => {}}>View All</span>
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                   {auditLogs.slice(0, 5).map(log => {
                     let Icon = ActivitySquare;
                     let color = "var(--text-secondary)";
                     let bg = "var(--bg-canvas)";
                     
                     if(log.action.includes("CREATE")) { Icon = Plus; color = "var(--primary)"; bg = "var(--primary-light)"; }
                     if(log.action.includes("LOGIN")) { Icon = UserCheck; color = "var(--emerald-dark)"; bg = "var(--emerald-light)"; }
                     if(log.action.includes("KEY")) { Icon = ShieldCheck; color = "var(--amber-dark)"; bg = "#fef3c7"; }
                     if(log.action.includes("UPDATE")) { Icon = Check; color = "#2563eb"; bg = "#dbeafe"; }

                     return (
                       <div key={log.id} style={{ display: 'flex', alignItems: 'flex-start', gap: '12px' }}>
                          <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: bg, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                             <Icon style={{ width: '18px', height: '18px', color: color }} />
                          </div>
                          <div style={{ flex: 1, paddingBottom: '12px', borderBottom: '1px solid var(--border-subtle)' }}>
                             <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                                <span style={{ fontSize: '0.875rem', fontWeight: 700, color: "var(--text-primary)" }}>{log.action.replace(/_/g, ' ')}</span>
                                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{new Date(log.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</span>
                             </div>
                             <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '2px' }}>
                                {log.entity_type} {log.entity_id ? `(${log.entity_id.substring(0,8)})` : ''}
                             </p>
                          </div>
                       </div>
                     );
                   })}
                   {auditLogs.length === 0 && (
                      <p style={{ fontSize: '0.8125rem', color: 'var(--text-muted)', textAlign: 'center', padding: '20px 0' }}>No recent activity found.</p>
                   )}
                </div>
             </div>

             {/* System Health */}
             <div className="card" style={{ padding: '16px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
                   <h3 style={{ fontSize: '1.125rem', fontWeight: 800, color: 'var(--text-primary)' }}>System Health</h3>
                   <span style={{ fontSize: '0.75rem', color: 'var(--emerald-dark)', background: "var(--emerald-light)", padding: "4px 10px", borderRadius: "12px", fontWeight: 600, display: "flex", alignItems: "center", gap: "6px" }}>
                     <div style={{ width: "6px", height: "6px", borderRadius: "50%", background: "var(--emerald-dark)" }}></div> All Systems Operational
                   </span>
                </div>
                
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                   <div style={{ padding: "16px", borderRadius: "12px", border: "1px solid var(--border-subtle)", background: "var(--bg-canvas)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--emerald-dark)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Check style={{ color: "white", width: "14px", height: "14px" }} />
                        </div>
                        <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>API Services</span>
                      </div>
                      <p style={{ fontSize: "0.75rem", color: "var(--emerald-dark)", fontWeight: 600, marginLeft: "32px" }}>Operational <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>99.9% uptime</span></p>
                   </div>
                   
                   <div style={{ padding: "16px", borderRadius: "12px", border: "1px solid var(--border-subtle)", background: "var(--bg-canvas)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--emerald-dark)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Check style={{ color: "white", width: "14px", height: "14px" }} />
                        </div>
                        <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>Database</span>
                      </div>
                      <p style={{ fontSize: "0.75rem", color: "var(--emerald-dark)", fontWeight: 600, marginLeft: "32px" }}>Operational <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>99.9% uptime</span></p>
                   </div>
                   
                   <div style={{ padding: "16px", borderRadius: "12px", border: "1px solid var(--border-subtle)", background: "var(--bg-canvas)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--emerald-dark)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Check style={{ color: "white", width: "14px", height: "14px" }} />
                        </div>
                        <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>Background Workers</span>
                      </div>
                      <p style={{ fontSize: "0.75rem", color: "var(--emerald-dark)", fontWeight: 600, marginLeft: "32px" }}>Operational <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>99.8% uptime</span></p>
                   </div>
                   
                   <div style={{ padding: "16px", borderRadius: "12px", border: "1px solid var(--border-subtle)", background: "var(--bg-canvas)" }}>
                      <div style={{ display: "flex", alignItems: "center", gap: "8px", marginBottom: "4px" }}>
                        <div style={{ width: "24px", height: "24px", borderRadius: "50%", background: "var(--emerald-dark)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                          <Check style={{ color: "white", width: "14px", height: "14px" }} />
                        </div>
                        <span style={{ fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)" }}>File Storage</span>
                      </div>
                      <p style={{ fontSize: "0.75rem", color: "var(--emerald-dark)", fontWeight: 600, marginLeft: "32px" }}>Operational <span style={{ color: "var(--text-muted)", fontWeight: 500 }}>99.9% uptime</span></p>
                   </div>
                </div>
             </div>
             
             {/* Quick Actions Panel */}
             <div className="card" style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
                <h3 style={{ fontSize: '1.125rem', fontWeight: 800, color: 'var(--text-primary)', marginBottom: '4px' }}>Quick Actions</h3>
                

                <button onClick={() => { resetUserForm(); setNewUserRole("DATA_ENTRY"); setShowCreateUserModal(true); }} className="btn-primary" style={{ width: '100%', justifyContent: 'flex-start', padding: '16px', background: "#3b82f6", borderRadius: "12px", gap: "16px" }}>
                   <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                     <UserCheck style={{ width: '20px', height: '20px', color: "white" }} />
                   </div>
                   <div style={{ textAlign: "left" }}>
                     <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "white" }}>Add Data Entry User</p>
                     <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.8)" }}>Create a new user account</p>
                   </div>
                </button>
                
                <button onClick={() => {}} className="btn-primary" style={{ width: '100%', justifyContent: 'flex-start', padding: '16px', background: "#10b981", borderRadius: "12px", gap: "16px" }}>
                   <div style={{ width: "32px", height: "32px", borderRadius: "8px", background: "rgba(255,255,255,0.2)", display: "flex", alignItems: "center", justifyContent: "center" }}>
                     <ShieldCheck style={{ width: '20px', height: '20px', color: "white" }} />
                   </div>
                   <div style={{ textAlign: "left" }}>
                     <p style={{ fontSize: "0.875rem", fontWeight: 700, color: "white" }}>Manage API Keys</p>
                     <p style={{ fontSize: "0.75rem", color: "rgba(255,255,255,0.8)" }}>Generate or revoke API keys</p>
                   </div>
                </button>
                
             </div>
          </div>
        </>
      )}

      {/* ========================================================================= */}
      {/* MODULE 2: ORGANIZATIONS VIEW                                              */}
      {/* ========================================================================= */}
      {viewMode === "organizations" && (
        <>
          {/* Header */}
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
                <Building2 style={{ width: "22px", height: "22px", color: "var(--primary)" }} />
                Platform Control & Tenant Registry
              </h2>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                Super Admin multi-tenant workspace provisioning and platform oversight
              </p>
            </div>

          </div>

          {msg && (
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
              <span>{msg}</span>
            </div>
          )}

          {/* KPI Stats */}
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: "16px" }}>
            <div className="stat-card stat-card-accent-indigo">
              <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Total Tenant Organizations</span>
              <p style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--text-primary)", fontFamily: "monospace", marginTop: "4px" }}>
                {organizations.length}
              </p>
            </div>

            <div className="stat-card stat-card-accent-emerald">
              <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Platform Security Level</span>
              <p style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--emerald-dark)", fontFamily: "monospace", marginTop: "4px" }}>
                ISOLATED
              </p>
            </div>

            <div className="stat-card stat-card-accent-amber">
              <span style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--text-secondary)" }}>Active Workspaces</span>
              <p style={{ fontSize: "1.75rem", fontWeight: 800, color: "var(--amber-dark)", fontFamily: "monospace", marginTop: "4px" }}>
                {organizations.filter(o => o.status !== "DEACTIVATED").length} Workspaces
              </p>
            </div>
          </div>

          {/* Tenants Table */}
          <div className="table-container">
            <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border-subtle)", display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
              <div>
                <h3 style={{ fontSize: "0.875rem", fontWeight: 800, color: "var(--text-primary)" }}>
                  Provisioned Organizations ({filteredOrgs.length})
                </h3>
                <span style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                  Cross-tenant data partitions with cryptographically verified boundaries
                </span>
              </div>

              <div style={{ position: "relative", width: "280px" }}>
                <Search style={{ width: "15px", height: "15px", color: "var(--text-muted)", position: "absolute", left: "10px", top: "50%", transform: "translateY(-50%)" }} />
                <input
                  type="text"
                  value={orgSearch}
                  onChange={(e) => setOrgSearch(e.target.value)}
                  placeholder="Search tenants by name or ID..."
                  className="input-text"
                  style={{ paddingLeft: "32px", fontSize: "0.75rem" }}
                />
              </div>
            </div>

            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ paddingLeft: "20px" }}>Organization</th>
                  <th>Tenant ID</th>
                  <th>Subscription Tier</th>
                  <th>Status</th>
                  <th>Created Date</th>
                  <th style={{ textAlign: "right", paddingRight: "20px" }}>Tenant Actions</th>
                </tr>
              </thead>
              <tbody>
                {loading ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "36px 0", color: "var(--text-muted)" }}>
                      Loading platform organizations...
                    </td>
                  </tr>
                ) : filteredOrgs.length === 0 ? (
                  <tr>
                    <td colSpan={6} style={{ textAlign: "center", padding: "36px 0", color: "var(--text-muted)" }}>
                      No matching organizations found.
                    </td>
                  </tr>
                ) : (
                  filteredOrgs.map((org) => (
                    <tr key={org.id}>
                      <td style={{ paddingLeft: "20px" }}>
                        <p style={{ fontWeight: 700, color: "var(--text-primary)" }}>{org.name}</p>
                        <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>Domain: {org.domain || "apex.com"}</p>
                      </td>
                      <td style={{ fontFamily: "monospace", fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                        {org.id}
                      </td>
                      <td>
                        <span className="badge badge-medium">
                          GROWTH TIER
                        </span>
                      </td>
                      <td>
                        <span className={`badge ${org.status === "SUSPENDED" ? "badge-lost" : "badge-open"}`}>
                          {org.status || "ACTIVE"}
                        </span>
                      </td>
                      <td style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>
                        {new Date(org.created_at).toLocaleDateString()}
                      </td>
                      <td style={{ textAlign: "right", paddingRight: "20px" }}>
                        <div style={{ display: "flex", alignItems: "center", justifyContent: "flex-end", gap: "6px" }}>
                          <button
                            onClick={() => setSupportOrgModal(org)}
                            className="btn-secondary"
                            style={{
                              fontSize: "0.6875rem",
                              padding: "5px 10px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              color: "#b45309",
                              borderColor: "#fde68a",
                              background: "#fffbeb",
                              fontWeight: 700,
                            }}
                            title="Start time-boxed, audited support session"
                          >
                            <LifeBuoy style={{ width: "12px", height: "12px" }} /> Support
                          </button>
                          
                          <button
                            onClick={() => handleGrantTrial(org)}
                            className="btn-secondary"
                            style={{
                              fontSize: "0.6875rem",
                              padding: "5px 10px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              color: "var(--primary)",
                              borderColor: "var(--primary)",
                              background: "transparent",
                              fontWeight: 700,
                            }}
                            title="Grant or extend trial days"
                          >
                            Grant Trial
                          </button>

                          <button
                            onClick={() => handleGrantFullAccess(org)}
                            className="btn-secondary"
                            style={{
                              fontSize: "0.6875rem",
                              padding: "5px 10px",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px",
                              color: "var(--emerald)",
                              borderColor: "var(--emerald)",
                              background: "transparent",
                              fontWeight: 700,
                            }}
                            title="Grant 10-year enterprise access"
                          >
                            Grant Full
                          </button>

                          <div 
                            style={{ 
                              display: "flex", 
                              alignItems: "center", 
                              gap: "8px", 
                              marginLeft: "8px",
                              paddingLeft: "8px",
                              borderLeft: "1px solid var(--border-subtle)"
                            }}
                          >
                            <span style={{ fontSize: "0.6875rem", fontWeight: 700, color: org.status === "SUSPENDED" ? "#dc2626" : "var(--text-secondary)" }}>
                              {org.status === "SUSPENDED" ? "SUSPENDED" : "Active"}
                            </span>
                            <div 
                              className={`toggle-switch ${org.status === "SUSPENDED" ? "active" : ""}`}
                              onClick={() => handleToggleSuspend(org)}
                              style={{ 
                                width: "32px", 
                                height: "18px", 
                                borderRadius: "10px", 
                                background: org.status === "SUSPENDED" ? "#dc2626" : "#cbd5e1",
                                position: "relative",
                                cursor: org.status === "SUSPENDED" ? "not-allowed" : "pointer",
                                display: "flex",
                                alignItems: "center",
                                transition: "background 0.2s"
                              }}
                            >
                              <div style={{
                                width: "14px",
                                height: "14px",
                                borderRadius: "50%",
                                background: "white",
                                position: "absolute",
                                left: org.status === "SUSPENDED" ? "16px" : "2px",
                                transition: "left 0.2s"
                              }} />
                            </div>
                          </div>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ========================================================================= */}
      {/* MODULE 3: USERS VIEW                                                      */}
      {/* ========================================================================= */}
      {viewMode === "users" && (
        <>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: "12px" }}>
            <div>
              <h2 style={{ fontSize: "1.375rem", fontWeight: 800, color: "var(--text-primary)", letterSpacing: "-0.02em", display: "flex", alignItems: "center", gap: "8px" }}>
                <UserCheck style={{ width: "22px", height: "22px", color: "var(--primary)" }} />
                Platform User Management
              </h2>
              <p style={{ fontSize: "0.8125rem", color: "var(--text-secondary)", marginTop: "2px" }}>
                Manage Data Entry operators, ORG Admins, and platform access
              </p>
            </div>
            <button onClick={() => setShowCreateUserModal(true)} className="btn-primary">
              <Plus style={{ width: "16px", height: "16px" }} />
              Add User
            </button>
          </div>

          <div className="table-container">
            <table className="data-table">
              <thead>
                <tr>
                  <th style={{ paddingLeft: "20px" }}>Name / Email</th>
                  <th>Role</th>
                  <th>Tenant</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id}>
                    <td style={{ paddingLeft: "20px" }}>
                      <p style={{ fontWeight: 700, color: "var(--text-primary)" }}>{u.full_name}</p>
                      <p style={{ fontSize: "0.6875rem", color: "var(--text-muted)" }}>{u.email}</p>
                    </td>
                    <td>
                      <span className="badge badge-medium">
                        {u.platform_role || u.tenant_role || "VIEWER"}
                      </span>
                    </td>
                    <td style={{ fontSize: "0.75rem", color: "var(--text-secondary)" }}>
                      {u.organization_name || "Platform Level"}
                    </td>
                    <td>
                      <span className={`badge ${u.status === "ACTIVE" ? "badge-open" : "badge-masked"}`}>
                        {u.status}
                      </span>
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
                        <button
                          onClick={() => handleEditUser(u)}
                          className="btn-secondary"
                          style={{ padding: "4px 8px", fontSize: "0.6875rem" }}
                        >
                          Edit
                        </button>
                        <button
                          onClick={() => handleToggleUserStatus(u)}
                          className={u.status === "ACTIVE" ? "btn-secondary" : "btn-primary"}
                          style={{ padding: "4px 8px", fontSize: "0.6875rem" }}
                        >
                          {u.status === "ACTIVE" ? "Suspend" : "Activate"}
                        </button>
                        <button
                          onClick={async () => {
                            const reason = prompt(`Provide compliance reason to move user "${u.full_name}" to Recycle Bin:`);
                            if (reason) {
                              try {
                                await api.softDeleteAdminUser(u.id, reason);
                                setMsg(`User ${u.full_name} moved to Recycle Bin.`);
                                loadPlatformData();
                              } catch (e: any) {
                                alert(e.message || "Failed to soft delete user.");
                              }
                            }
                          }}
                          className="btn-secondary"
                          style={{ padding: "4px 8px", fontSize: "0.6875rem", color: "#dc2626", borderColor: "#fecaca" }}
                          title="Move user to Recycle Bin"
                        >
                          <Trash2 style={{ width: "11px", height: "11px" }} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}

      {/* ========================================================================= */}
      {/* MODULE 4: PLATFORM ACTIVITIES & CRYPTOGRAPHIC AUDIT VIEW                  */}
      {/* ========================================================================= */}
      {viewMode === "audit" && (
        <AuditChainView organizations={organizations} />
      )}

      {/* ========================================================================= */}
      {/* MODULE 5: PLATFORM SECURITY & RBAC                                       */}
      {/* ========================================================================= */}
      {viewMode === "security" && (
        <PlatformSecurityView users={users} onRefreshUsers={loadPlatformData} />
      )}

      {/* ========================================================================= */}
      {/* MODULE 6: ENTERPRISE RECYCLE BIN                                         */}
      {/* ========================================================================= */}
      {viewMode === "recovery" && (
        <RecycleBinView />
      )}

      {/* Unified Add Platform User & Provisioning Modal */}
      {showCreateUserModal && (
        <div className="modal-overlay" onClick={() => setShowCreateUserModal(false)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()} style={{ padding: "0", maxWidth: newUserRole === "ORG_ADMIN" ? "800px" : "480px", overflow: "hidden" }}>
            <div style={{ background: "var(--bg-surface)", padding: "24px 32px", display: "flex", alignItems: "center", justifyContent: "space-between", borderBottom: "1px solid var(--border-subtle)" }}>
              <div>
                <h3 style={{ fontSize: "1.25rem", fontWeight: 800, color: "var(--text-primary)", display: "flex", alignItems: "center", gap: "8px" }}>
                  <UserCheck style={{ width: "24px", height: "24px", color: "var(--primary)" }} />
                  Add Platform User
                </h3>
                <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", marginTop: "4px" }}>Provision platform-wide users or completely new tenants.</p>
              </div>
              <button
                onClick={() => setShowCreateUserModal(false)}
                style={{ background: "none", border: "none", cursor: "pointer", color: "var(--text-muted)" }}
              >
                <X style={{ width: "20px", height: "20px" }} />
              </button>
            </div>

            <form onSubmit={handleCreateUser} style={{ display: "flex", flexDirection: "column", maxHeight: "75vh" }}>
              <div style={{ padding: "24px 32px", overflowY: "auto", display: "flex", flexDirection: "column", gap: "24px" }}>
                
                {/* 1. Role Selection */}
                <div>
                  <label style={{ display: "block", fontSize: "0.875rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "8px" }}>
                    Select User Role *
                  </label>
                  <select
                    value={newUserRole}
                    onChange={(e) => setNewUserRole(e.target.value)}
                    className="select-dropdown"
                    style={{ padding: "12px", fontSize: "1rem" }}
                    required
                  >
                    <option value="" disabled>Choose role...</option>
                    <option value="DATA_ENTRY">Data Entry Operator (Global Intelligence)</option>
                    <option value="ORG_ADMIN">Organization Admin (Provision New Tenant)</option>
                  </select>
                </div>

                {/* 2. Dynamic Forms based on Role */}
                {newUserRole === "DATA_ENTRY" && (
                  <div style={{ background: "var(--bg-canvas)", padding: "20px", borderRadius: "12px", border: "1px solid var(--border-subtle)", display: "flex", flexDirection: "column", gap: "16px" }}>
                    <h4 style={{ fontSize: "1rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Data Entry Operator Details</h4>
                    
                    <div>
                      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Controlled By</label>
                      <input type="text" value="Super Admin" className="input-text" disabled style={{ background: "var(--bg-surface)", color: "var(--text-muted)", cursor: "not-allowed" }} />
                    </div>
                    <div>
                      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Full Name *</label>
                      <input type="text" value={newUserFullName} onChange={(e) => setNewUserFullName(e.target.value)} placeholder="e.g. John Doe" className="input-text" required />
                    </div>
                    <div>
                      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Email Address (Login Username) *</label>
                      <input type="email" value={newUserEmail} onChange={(e) => setNewUserEmail(e.target.value)} placeholder="e.g. john@example.com" className="input-text" required />
                    </div>
                    <div>
                      <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Initial Password *</label>
                      <input type="text" value={newUserPassword} onChange={(e) => setNewUserPassword(e.target.value)} className="input-text" required />
                    </div>
                  </div>
                )}

                {newUserRole === "ORG_ADMIN" && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "32px" }}>
                    {/* Section: Company Info */}
                    <div>
                      <h4 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)", marginBottom: "16px", paddingBottom: "8px", borderBottom: "1px solid var(--border-subtle)" }}>Company & Business Details</h4>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Company Name *</label>
                          <input type="text" value={name} onChange={(e) => setName(e.target.value)} className="input-text" required />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Company Type</label>
                          <select value={orgType} onChange={(e) => setOrgType(e.target.value)} className="select-dropdown">
                            <option value="Private Limited">Private Limited</option>
                            <option value="Public Limited">Public Limited</option>
                            <option value="OPC">OPC (One Person Company)</option>
                            <option value="Partnership">Partnership</option>
                            <option value="LLP">LLP</option>
                            <option value="Sole Proprietorship">Sole Proprietorship</option>
                          </select>
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Owner/Director Name</label>
                          <input type="text" value={orgOwner} onChange={(e) => setOrgOwner(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Industry/Sector</label>
                          <input type="text" value={orgIndustry} onChange={(e) => setOrgIndustry(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>CIN (Optional)</label>
                          <input type="text" value={orgCin} onChange={(e) => setOrgCin(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Registration Number</label>
                          <input type="text" value={orgRegistration} onChange={(e) => setOrgRegistration(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>GST Number (Optional)</label>
                          <input type="text" value={orgGst} onChange={(e) => setOrgGst(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Website URL</label>
                          <input type="text" value={orgWebsite} onChange={(e) => setOrgWebsite(e.target.value)} className="input-text" />
                        </div>
                      </div>
                    </div>

                    {/* Section: Contact & Location */}
                    <div>
                      <h4 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--text-primary)", marginBottom: "16px", paddingBottom: "8px", borderBottom: "1px solid var(--border-subtle)" }}>Location & Contact</h4>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                        <div style={{ gridColumn: "span 2" }}>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Full Address</label>
                          <input type="text" value={orgAddress} onChange={(e) => setOrgAddress(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>City</label>
                          <input type="text" value={orgCity} onChange={(e) => setOrgCity(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>State</label>
                          <input type="text" value={orgState} onChange={(e) => setOrgState(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Pincode</label>
                          <input type="text" value={orgPincode} onChange={(e) => setOrgPincode(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Company Contact Number</label>
                          <input type="text" value={orgContactNumber} onChange={(e) => setOrgContactNumber(e.target.value)} className="input-text" />
                        </div>
                        <div style={{ gridColumn: "span 2" }}>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Company Email Address</label>
                          <input type="email" value={orgContactEmail} onChange={(e) => setOrgContactEmail(e.target.value)} className="input-text" />
                        </div>
                      </div>
                    </div>

                    {/* Section: Key Person */}
                    <div style={{ background: "var(--bg-canvas)", padding: "20px", borderRadius: "12px", border: "1px solid var(--border-subtle)" }}>
                      <h4 style={{ fontSize: "1rem", fontWeight: 800, color: "var(--primary)", marginBottom: "16px", paddingBottom: "8px", borderBottom: "1px solid var(--border-subtle)" }}>Key Person Appointed (Admin User)</h4>
                      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Full Name *</label>
                          <input type="text" value={newUserFullName} onChange={(e) => setNewUserFullName(e.target.value)} className="input-text" required />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Contact Number</label>
                          <input type="text" value={adminPhone} onChange={(e) => setAdminPhone(e.target.value)} className="input-text" />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Email (Login) *</label>
                          <input type="email" value={newUserEmail} onChange={(e) => setNewUserEmail(e.target.value)} className="input-text" required />
                        </div>
                        <div>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Password *</label>
                          <input type="text" value={newUserPassword} onChange={(e) => setNewUserPassword(e.target.value)} className="input-text" required />
                        </div>
                        <div style={{ gridColumn: "span 2" }}>
                          <label style={{ display: "block", fontSize: "0.75rem", fontWeight: 700, color: "var(--text-primary)", marginBottom: "4px" }}>Subscription Plan</label>
                          <select value={planCode} onChange={(e) => setPlanCode(e.target.value)} className="select-dropdown">
                            <option value="STARTER">Starter Plan</option>
                            <option value="GROWTH">Growth Plan</option>
                            <option value="ENTERPRISE">Enterprise Plan</option>
                          </select>
                        </div>
                      </div>
                    </div>
                  </div>
                )}
              </div>

              <div style={{ padding: "20px 32px", borderTop: "1px solid var(--border-subtle)", background: "var(--bg-canvas)", display: "flex", justifyContent: "flex-end", gap: "12px" }}>
                <button type="button" onClick={() => setShowCreateUserModal(false)} className="btn-secondary" style={{ padding: "10px 20px" }}>
                  Cancel
                </button>
                <button type="submit" disabled={creating || !newUserRole} className="btn-primary" style={{ padding: "10px 24px" }}>
                  {creating ? "Processing..." : newUserRole === "ORG_ADMIN" ? "Provision Tenant & Admin" : "Create User"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {/* Support Session Modal */}
      {supportOrgModal && (
        <SupportSessionModal
          organization={supportOrgModal}
          onClose={() => setSupportOrgModal(null)}
          onSessionCreated={(session, orgName) => {
            setActiveSupportSession({ ...session, org_name: orgName });
          }}
        />
      )}

      {/* Suspend Org Modal */}
      {suspendOrgModal && (
        <SuspendOrgModal
          organization={suspendOrgModal}
          onClose={() => setSuspendOrgModal(null)}
          onSuspended={() => {
            loadPlatformData();
          }}
        />
      )}
    </div>
  );
};
